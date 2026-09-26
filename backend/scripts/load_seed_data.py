"""
FinanceSim — 资产种子数据加载脚本

读取 backend/app/data/seed/*.json，校验后全量替换 assets 表的数据。

背景：旧数据存在大量问题（中文名、exchange/currency 张冠李戴、
fundamentals 存储非法 JSON 导致 SQLAlchemy 反序列化直接 500），
因此这里采用全量替换而非增量合并。

用法:
    python load_seed_data.py            # 加载
    python load_seed_data.py --dry-run  # 只校验不写库
"""
import json
import os
import re
import sys
import sqlite3
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
# HERE = backend/scripts，种子文件实际在 backend/app/data/seed
SEED_DIR = os.path.normpath(os.path.join(HERE, "..", "app", "data", "seed"))
DB_PATH = os.path.normpath(os.path.join(HERE, "..", "financesim.db"))

REQUIRED_FIELDS = [
    "ticker", "name", "type", "exchange", "sector",
    "industry", "currency",
]

CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")

# 期望每个文件的条目数
EXPECTED = {
    "us_stocks.json": 150,
    "europe_stocks.json": 95,
    "apac_stocks.json": 150,
    "china_stocks.json": 60,
    "fx_pairs.json": 52,
    "bonds.json": 48,
    "etf_index.json": 65,
}


def load_seed_files():
    """读取并校验所有种子文件"""
    records = []
    errors = []

    for fname in EXPECTED:
        path = os.path.join(SEED_DIR, fname)
        if not os.path.exists(path):
            errors.append(f"[缺失] {fname} 不存在")
            continue

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            errors.append(f"[损坏] {fname} 不是合法 JSON: {e}")
            continue

        if not isinstance(data, list):
            errors.append(f"[格式] {fname} 顶层应为数组")
            continue

        expected = EXPECTED[fname]
        if len(data) != expected:
            errors.append(f"[数量] {fname}: 期望 {expected} 条，实际 {len(data)} 条")

        for i, item in enumerate(data):
            # 必填字段
            missing = [k for k in REQUIRED_FIELDS if not item.get(k)]
            if missing:
                errors.append(f"[缺字段] {fname}[{i}]: {missing}")
                continue

            # 硬约束：不允许任何中文字符
            text = json.dumps(item, ensure_ascii=False)
            zh = CHINESE_RE.findall(text)
            if zh:
                errors.append(
                    f"[中文] {fname}[{i}] {item.get('ticker')}: 包含中文 {''.join(zh[:5])}"
                )
                continue

            item["_source"] = fname
            records.append(item)

    return records, errors


def dedupe(records):
    """按 ticker 去重，保留首次出现"""
    seen = {}
    dupes = []
    out = []
    for r in records:
        tk = r["ticker"]
        if tk in seen:
            dupes.append(tk)
            continue
        seen[tk] = True
        out.append(r)
    return out, dupes


def main():
    dry_run = "--dry-run" in sys.argv

    records, errors = load_seed_files()
    records, dupes = dedupe(records)

    if not os.path.exists(DB_PATH):
        errors.append(f"[数据库] 找不到 {DB_PATH}")
    print("=" * 66)
    print("FinanceSim 种子数据加载")
    print("=" * 66)

    print(f"\n读取目录: {SEED_DIR}")
    print(f"总记录数: {len(records)}")
    if dupes:
        print(f"重复 ticker（已跳过）: {len(dupes)} -> {dupes[:10]}")

    # 分类统计
    by_type = {}
    for r in records:
        by_type[r["type"]] = by_type.get(r["type"], 0) + 1
    print("\n按类型分布:")
    for t, n in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {t:8s} {n:4d}")

    if errors:
        print(f"\n发现 {len(errors)} 个问题:")
        for e in errors[:40]:
            print(f"  {e}")
        if len(errors) > 40:
            print(f"  ... 另有 {len(errors) - 40} 条")
        print("\n校验未通过，中止写入。")
        return 1

    print("\n校验全部通过。")

    if dry_run:
        print("\n[dry-run] 未写入数据库。")
        return 0

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    before = cur.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
    print(f"\n当前 assets 表记录数: {before}")
    print("警告: 即将清空 assets 表并全量替换（price_history 会级联删除）")

    cur.execute("DELETE FROM assets")
    conn.commit()

    now = datetime.utcnow().isoformat()
    inserted = 0
    for r in records:
        try:
            cur.execute(
                """INSERT INTO assets
                   (world_id, ticker, type, name, exchange, sector, industry,
                    currency, market_cap, beta, volatility, fundamentals,
                    current_price, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    1,
                    r["ticker"],
                    r["type"],
                    r["name"],
                    r["exchange"],
                    r.get("sector"),
                    r.get("industry"),
                    r["currency"],
                    r.get("market_cap"),
                    r.get("beta", 1.0),
                    r.get("volatility", 0.25),
                    json.dumps(r.get("fundamentals") or {}),
                    r.get("current_price"),
                    now,
                    now,
                ),
            )
            inserted += 1
        except Exception as e:
            print(f"  [写入失败] {r.get('ticker')}: {e}")

    conn.commit()

    after = cur.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
    print(f"\n写入完成: {inserted} 条 -> 当前 total={after}")

    # 验证 JSON 合法性（这是之前 500 的根因，必须复查）
    bad = 0
    rows = cur.execute("SELECT ticker, fundamentals FROM assets").fetchall()
    for tk, f in rows:
        if f is None:
            continue
        try:
            json.loads(f)
        except Exception:
            bad += 1
            print(f"  [非法JSON] {tk}")
    print(f"非法 fundamentals 数量: {bad}")

    print("\n各类型最终数量:")
    for t, n in cur.execute(
        "SELECT type, COUNT(*) FROM assets GROUP BY type ORDER BY COUNT(*) DESC"
    ).fetchall():
        print(f"  {t:8s} {n:4d}")

    conn.close()

    if bad:
        print("\n仍存在非法 JSON，请修复！")
        return 1

    print("\n数据库重建成功。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
