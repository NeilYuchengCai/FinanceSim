"""
重建 commodities 表为英文种子数据。

背景：库里原有的商品名是中文（"原油 (WTI)"、"黄金"…），且只有 13 个。
项目要求全英文 + 全球覆盖，本脚本按 app/data/seed/commodities.json 全量替换。

用法：
    python scripts/load_commodities.py            # 写入
    python scripts/load_commodities.py --dry-run  # 只校验不写入
"""
import json
import os
import re
import sqlite3
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED_PATH = os.path.join(BASE_DIR, "app", "data", "seed", "commodities.json")
DB_PATH = os.path.join(BASE_DIR, "financesim.db")

WORLD_ID = 1
VALID_CATEGORIES = {"ENERGY", "METAL", "AGRICULTURE", "PRECIOUS_METAL"}
CJK = re.compile(r"[\u4e00-\u9fff]")


def load_seed():
    with open(SEED_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def validate(rows):
    errors = []
    seen = set()
    for i, r in enumerate(rows):
        label = f"#{i} {r.get('ticker', '<no ticker>')}"
        for field in ("ticker", "name", "category", "subcategory", "baseline_price"):
            if not r.get(field):
                errors.append(f"{label}: 缺字段 {field}")
        if r.get("category") and r["category"].upper() not in VALID_CATEGORIES:
            errors.append(f"{label}: category 非法 {r['category']}")
        for field in ("name", "subcategory"):
            if CJK.search(str(r.get(field) or "")):
                errors.append(f"{label}: {field} 含中文 -> {r[field]}")
        t = r.get("ticker")
        if t in seen:
            errors.append(f"{label}: ticker 重复 {t}")
        seen.add(t)
        if float(r.get("baseline_price") or 0) <= 0:
            errors.append(f"{label}: baseline_price 必须 > 0")
    return errors


def main():
    dry_run = "--dry-run" in sys.argv
    rows = load_seed()
    print(f"种子条目: {len(rows)}")

    errors = validate(rows)
    if errors:
        print("校验失败:")
        for e in errors[:30]:
            print("  -", e)
        return 1
    print("校验通过：全英文、无重复 ticker、category 合法")

    if dry_run:
        print("--dry-run：未写入数据库")
        return 0

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM commodities WHERE world_id = ?", (WORLD_ID,))

    now = datetime.now().isoformat()
    for r in rows:
        cur.execute(
            """
            INSERT INTO commodities (
                world_id, ticker, name, category, subcategory, currency, exchange,
                contract_size, tick_size, volatility, seasonality_factor,
                supply_demand, inventory, inventory_change,
                baseline_price, current_price, data_source, source_ts, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                WORLD_ID,
                r["ticker"],
                r["name"],
                r["category"].upper(),
                r["subcategory"],
                r.get("currency") or "USD",
                r.get("exchange"),
                float(r.get("contract_size") or 1000.0),
                float(r.get("tick_size") or 0.01),
                float(r.get("volatility") or 0.02),
                float(r.get("seasonality_factor") or 1.0),
                json.dumps({"supply": r.get("supply"), "demand": r.get("demand")}),
                float(r.get("inventory") or 0),
                0.0,
                float(r["baseline_price"]),
                float(r["baseline_price"]),
                "SIMULATED",
                now,
                now,
            ),
        )

    conn.commit()
    total = cur.execute(
        "SELECT COUNT(*) FROM commodities WHERE world_id = ?", (WORLD_ID,)
    ).fetchone()[0]
    cjk = cur.execute(
        "SELECT COUNT(*) FROM commodities WHERE name LIKE '%' "
        "AND (name GLOB '*[一-龥]*' OR subcategory GLOB '*[一-龥]*')"
    ).fetchone()[0]
    by_cat = cur.execute(
        "SELECT category, COUNT(*) FROM commodities WHERE world_id=? GROUP BY category",
        (WORLD_ID,),
    ).fetchall()
    conn.close()

    print(f"写入完成: {total} 条商品（中文残留 {cjk}）")
    for cat, n in sorted(by_cat):
        print(f"  {cat}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
