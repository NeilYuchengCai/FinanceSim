"""
Seed historical events into the `events` table for the Timeline view.

Idempotent: deletes all existing events before inserting a fresh set.
Safe to re-run.

Usage:
    python scripts/seed_events.py
"""
import json
import os
import random
import sqlite3
import uuid
from datetime import datetime, timedelta

# ----------------------------------------------------------------------------
# Paths / constants
# ----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "financesim.db")

WORLD_ID = 1
TOTAL_EVENTS = 80
DAYS_BACK = 90

random.seed(20240101)

# Distribution of event types (must sum to TOTAL_EVENTS).
# The five types surfaced by the Timeline filter bar each get >= 8 entries.
TYPE_PLAN = [
    ("earnings",          12),
    ("geopolitical",      10),
    ("central_bank",      10),
    ("liquidity_crisis",   9),
    ("black_swan",         8),
    ("product_launch",     5),
    ("inflation_shock",    5),
    ("management_change",  4),
    ("regulatory",         4),
    ("ma",                 4),
    ("employment_shock",   3),
    ("guidance",           3),
    ("banking_crisis",     3),
]

# English copy templates: type -> (titles, bodies) with {a} = joined tickers
CONTENT = {
    "earnings": (
        [
            "{a0} Beats Q{quarter} Earnings Estimates",
            "{a0} Misses Q{quarter} Revenue Consensus",
            "{a0} Reports Record Quarterly Profit",
            "{a0} Quarterly Results Top Street Forecasts",
        ],
        [
            "{a0} posted quarterly results that came in ahead of analyst expectations, "
            "with margins expanding on tighter cost control and stronger-than-expected demand.",
            "{a0} reported a quarterly shortfall against consensus, citing softer demand "
            "and unfavourable currency effects. Management trimmed full-year guidance.",
            "{a0} delivered record quarterly profit driven by operating leverage and "
            "improving product mix. Free cash flow conversion remained above target.",
        ],
    ),
    "product_launch": (
        [
            "{a0} Unveils Next-Generation Product Line",
            "{a0} Launches New Platform for Enterprise Clients",
        ],
        [
            "{a0} introduced a new product family aimed at enterprise customers, "
            "with availability scheduled for the coming quarter.",
            "{a0} announced a new platform release expanding its addressable market "
            "and deepening integration across its existing portfolio.",
        ],
    ),
    "management_change": (
        [
            "{a0} Names New Chief Executive Officer",
            "{a0} Announces Leadership Transition",
        ],
        [
            "{a0} announced a change at the top as the board appointed a new chief "
            "executive officer, effective immediately. The transition follows a "
            "review of long-term strategy.",
        ],
    ),
    "regulatory": (
        [
            "Regulator Opens Formal Inquiry Into Sector Practices",
            "New Compliance Requirements Issued for Large Institutions",
        ],
        [
            "Authorities opened a formal inquiry affecting {a}, focusing on disclosure "
            "practices. Affected firms face potential remediation costs and tighter oversight.",
        ],
    ),
    "ma": (
        [
            "Major M&A Activity Reshapes the Sector",
            "Strategic Acquisition Announced Involving {a0}",
        ],
        [
            "A significant transaction involving {a} was announced, with the combined "
            "entity expected to hold a materially larger share of the market. "
            "Closing remains subject to regulatory clearance.",
        ],
    ),
    "guidance": (
        [
            "{a0} Raises Full-Year Outlook",
            "{a0} Cuts Forward Guidance on Demand Concerns",
        ],
        [
            "{a0} updated its forward guidance, pointing to a changed demand backdrop "
            "and revising its full-year revenue and margin assumptions accordingly.",
        ],
    ),
    "geopolitical": (
        [
            "Geopolitical Tensions Escalate Across Key Trade Routes",
            "Export Controls Tightened on Strategic Technology",
            "Trade Negotiations Stall, Raising Tariff Risk",
        ],
        [
            "Escalating geopolitical tensions raised risk premiums across {a}, with "
            "supply chains and cross-border trade flows under renewed pressure.",
            "New export control measures targeting strategic technology weighed on {a}, "
            "prompting investors to reprice exposure to the affected region.",
        ],
    ),
    "central_bank": (
        [
            "Central Bank Holds Policy Rate Steady",
            "Central Bank Delivers Surprise Rate Cut",
            "Central Bank Signals Extended Tightening Cycle",
        ],
        [
            "The central bank left its policy rate unchanged while signalling that "
            "future decisions remain data dependent, moving risk assets including {a}.",
            "A surprise policy decision by the central bank shifted rate expectations "
            "materially, with {a} reacting to the repricing of the front end.",
        ],
    ),
    "inflation_shock": (
        [
            "Inflation Print Comes In Well Above Consensus",
            "Core Inflation Surprise Resets Rate Expectations",
        ],
        [
            "An upside inflation surprise forced markets to reprice the policy path, "
            "pressuring duration-sensitive names across {a}.",
        ],
    ),
    "employment_shock": (
        [
            "Payrolls Data Surprises to the Downside",
            "Labour Market Tightens Unexpectedly",
        ],
        [
            "Labour market data diverged sharply from expectations, shifting the "
            "macro outlook and feeding through to {a}.",
        ],
    ),
    "liquidity_crisis": (
        [
            "Liquidity Stress Emerges in Short-Term Funding Markets",
            "Market-Making Capacity Withdraws Amid Funding Squeeze",
        ],
        [
            "Signs of liquidity stress appeared across funding markets, with spreads "
            "widening and depth thinning in {a}. Dealers cut risk appetite.",
        ],
    ),
    "banking_crisis": (
        [
            "Banking Sector Stress Re-Emerges on Credit Concerns",
            "Deposit Outflows Pressure Regional Lenders",
        ],
        [
            "Renewed stress in the banking sector weighed on {a} as concerns over "
            "asset quality and deposit stability resurfaced.",
        ],
    ),
    "black_swan": (
        [
            "Unprecedented Global Shock Hits Financial Markets",
            "Systemic Dislocation Triggers Broad Risk-Off Move",
        ],
        [
            "An unprecedented shock triggered a violent repricing across {a}, with "
            "correlations converging and volatility spiking across asset classes.",
            "A systemic dislocation forced a broad risk-off move, hitting {a} and "
            "straining liquidity across normally uncorrelated markets.",
        ],
    ),
}

# Crisis types skew toward higher severity
CRISIS_TYPES = {"liquidity_crisis", "banking_crisis", "black_swan"}
MACRO_TYPES = {"geopolitical", "central_bank", "inflation_shock", "employment_shock"}


def pick_severity(etype: str) -> float:
    if etype in CRISIS_TYPES:
        return round(random.uniform(0.62, 0.98), 3)
    if etype in MACRO_TYPES:
        return round(random.uniform(0.35, 0.85), 3)
    return round(random.uniform(0.10, 0.70), 3)


def pick_duration(etype: str) -> int:
    if etype == "black_swan":
        return random.randint(20, 30)
    if etype in ("liquidity_crisis", "banking_crisis"):
        return random.randint(10, 30)
    if etype in MACRO_TYPES:
        return random.randint(5, 20)
    if etype in ("earnings", "product_launch", "guidance"):
        return random.randint(1, 3)
    return random.randint(3, 10)


def pick_sentiment(etype: str, severity: float) -> float:
    if etype in ("earnings", "product_launch", "ma", "guidance"):
        return round(random.uniform(0.2, 0.8) * severity, 3)
    if etype in CRISIS_TYPES or etype == "regulatory":
        return round(random.uniform(-0.8, -0.2) * severity, 3)
    return round(random.uniform(-1.0, 1.0) * severity, 3)


def pick_macro_effect(etype: str, severity: float) -> dict:
    if etype in ("inflation_shock", "employment_shock"):
        return {
            "inflation_impact": round(severity * random.uniform(0.005, 0.02), 5),
            "gdp_impact": round(-severity * random.uniform(0.002, 0.01), 5),
        }
    if etype in ("central_bank", "geopolitical"):
        return {
            "rate_impact": round(severity * random.uniform(0.001, 0.005), 5),
            "risk_premium": round(severity * random.uniform(0.002, 0.01), 5),
        }
    if etype in ("liquidity_crisis", "banking_crisis"):
        return {
            "credit_spread": round(severity * random.uniform(0.01, 0.05), 5),
            "liquidity_premium": round(severity * random.uniform(0.005, 0.02), 5),
        }
    if etype == "black_swan":
        return {
            "volatility_spike": round(severity * random.uniform(0.1, 0.3), 5),
            "risk_premium": round(severity * random.uniform(0.02, 0.05), 5),
        }
    return {}


def build_pool(tickers):
    """Number of assets an event of a given type touches."""
    return {
        "earnings": (1, 1),
        "product_launch": (1, 1),
        "management_change": (1, 1),
        "guidance": (1, 2),
        "regulatory": (2, 4),
        "ma": (1, 3),
        "geopolitical": (6, 14),
        "central_bank": (8, 18),
        "inflation_shock": (8, 18),
        "employment_shock": (6, 14),
        "liquidity_crisis": (10, 20),
        "banking_crisis": (6, 14),
        "black_swan": (15, 24),
    }


def ensure_duration_column(conn: sqlite3.Connection):
    cols = [r[1] for r in conn.execute("PRAGMA table_info(events)").fetchall()]
    if "duration_days" not in cols:
        conn.execute("ALTER TABLE events ADD COLUMN duration_days INTEGER DEFAULT 0")
        conn.commit()
        print("[schema] added column events.duration_days")


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # --- guard: world must exist -------------------------------------------
    cur.execute("SELECT id FROM worlds WHERE id = ?", (WORLD_ID,))
    if cur.fetchone() is None:
        raise SystemExit(f"world_id={WORLD_ID} does not exist; run init_db first")

    ensure_duration_column(conn)

    # --- real tickers / sectors --------------------------------------------
    rows = cur.execute(
        "SELECT ticker, sector FROM assets WHERE type = 'EQUITY' AND ticker IS NOT NULL"
    ).fetchall()
    if not rows:
        raise SystemExit("no EQUITY assets found; load asset seed data first")

    tickers = [r[0] for r in rows]
    print(f"[assets] {len(tickers)} equity tickers available")

    sector_of = {r[0]: (r[1] or "Unknown") for r in rows}

    # --- wipe ---------------------------------------------------------------
    cur.execute("DELETE FROM events")
    conn.commit()
    print("[reset] DELETE FROM events")

    # --- generate -----------------------------------------------------------
    pool_cfg = build_pool(tickers)
    plan = []
    for etype, count in TYPE_PLAN:
        plan.extend([etype] * count)
    if len(plan) != TOTAL_EVENTS:
        raise SystemExit(f"TYPE_PLAN sums to {len(plan)}, expected {TOTAL_EVENTS}")
    random.shuffle(plan)

    now = datetime.now()
    inserted = []
    for i, etype in enumerate(plan):
        lo, hi = pool_cfg[etype]
        hi = min(hi, len(tickers))
        n = random.randint(min(lo, hi), hi)
        affected = random.sample(tickers, n)
        sectors = sorted({sector_of[t] for t in affected})[:6]

        titles, bodies = CONTENT[etype]
        title_tpl = random.choice(titles)
        body_tpl = random.choice(bodies)
        fmt = {
            "a0": affected[0],
            "a": ", ".join(affected[:3]),
            "quarter": random.randint(1, 4),
        }
        title = title_tpl.format(**fmt)[:500]
        body = body_tpl.format(**fmt)

        severity = pick_severity(etype)
        duration = pick_duration(etype)
        sentiment = pick_sentiment(etype, severity)
        macro = pick_macro_effect(etype, severity)

        # spread evenly across the last DAYS_BACK days
        day_offset = (i * (DAYS_BACK - 1)) / max(len(plan) - 1, 1)
        created = now - timedelta(
            days=day_offset,
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59),
        )

        inserted.append(
            (
                str(uuid.uuid4()),
                WORLD_ID,
                etype,
                severity,
                title,
                body,
                json.dumps(affected),
                json.dumps(sectors),
                json.dumps(macro),
                sentiment,
                random.randint(1, 3),
                duration,
                created.strftime("%Y-%m-%d %H:%M:%S"),
            )
        )

    cur.executemany(
        """
        INSERT INTO events (
            id, world_id, type, severity, title, body,
            affected_assets, affected_sectors, macro_effect,
            sentiment_effect, propagation_depth, duration_days, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        inserted,
    )
    conn.commit()

    # --- report -------------------------------------------------------------
    print(f"\n[done] inserted {len(inserted)} events into {DB_PATH}\n")
    print(f"{'type':<20}{'count':>7}")
    print("-" * 27)
    for etype, _ in TYPE_PLAN:
        c = cur.execute(
            "SELECT COUNT(*) FROM events WHERE world_id = ? AND type = ?",
            (WORLD_ID, etype),
        ).fetchone()[0]
        print(f"{etype:<20}{c:>7}")
    total = cur.execute(
        "SELECT COUNT(*) FROM events WHERE world_id = ?", (WORLD_ID,)
    ).fetchone()[0]
    print("-" * 27)
    print(f"{'TOTAL':<20}{total:>7}")
    oldest = cur.execute(
        "SELECT MIN(created_at), MAX(created_at) FROM events WHERE world_id = ?",
        (WORLD_ID,),
    ).fetchone()
    print(f"\ndate range: {oldest[0]}  ->  {oldest[1]}")
    conn.close()


if __name__ == "__main__":
    main()
