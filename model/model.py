"""Foreguild revenue model: the source of every number in the operating plan.

Run:
    python3 model/model.py            # print the three scenarios
    python3 model/model.py --check    # fail if any figure published in the plan drifts from the model
    python3 model/model.py --csv      # write model/output.csv (month-by-month, all scenarios)

No dependencies beyond the Python standard library.
All volumes and prices are PLANNING ASSUMPTIONS, not observed results.
"""
import csv
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Assumptions (base case). Conservative = 0.6x volumes, optimistic = 1.5x.
#    Prices and costs are the same in every scenario; only volumes change.
# ---------------------------------------------------------------------------
VOLUMES = {  # per month, months 1..12
    "open_tasks":      [50, 100, 180, 280, 400, 520, 650, 800, 950, 1100, 1300, 1500],
    "packages":        [0, 5, 12, 22, 35, 50, 70, 90, 115, 140, 170, 200],
    "standing_orders": [0, 0, 2, 5, 9, 14, 20, 26, 32, 38, 44, 50],
    "agent_seats":     [0, 0, 0, 1, 1, 2, 3, 4, 5, 6, 7, 8],
    "api_calls":       [0, 0, 0, 500, 1500, 3000, 5000, 7500, 10000, 13000, 16000, 20000],
    "pro_subs":        [0, 0, 3, 6, 10, 14, 18, 22, 26, 30, 35, 40],
    "private_boards":  [0, 0, 0, 0, 0, 1, 1, 2, 3, 3, 4, 5],
}

PRICE = {  # buyer price per unit and the share Foreguild keeps (policy-register starting values)
    "open_task":      (40.0, 0.08),     # 8% fee on a $40 average task
    "package":        (250.0, 0.25),    # managed outcome, keeps 25%
    "standing_order": (600.0, 0.30),    # monthly, keeps 30%
    "agent_seat":     (1500.0, 0.35),   # monthly, keeps 35%
    "api_call":       (1.0, 0.08),      # agent-to-agent, 8%
}
PRO_PLAN = 29.0              # $ a month
PRIVATE_BOARD = 500.0        # $ a month
PRIORITY_BOOST = 1.0         # $ per boosted task
PRIORITY_SHARE = 0.10        # share of open tasks that buy a boost, from month 3
FEE_FREE_SHARE_M1_2 = 0.5    # half of open tasks are fee-free in months 1-2

DIRECT_COST = {  # cost of serving one unit (checking, payments, human review, account time)
    "open_task": 0.70, "package": 22.50, "standing_order": 25.0,
    "agent_seat": 100.0, "api_call": 0.02, "private_board": 50.0,
}
FIXED_COST = [6000] * 3 + [11000] * 9   # $ a month: lean months 1-3, full team from month 4

SCENARIOS = {"Conservative": 0.6, "Base": 1.0, "Optimistic": 1.5}


# ---------------------------------------------------------------------------
# 2. Model
# ---------------------------------------------------------------------------
def run(scale):
    """Return month rows plus summary for one volume scale."""
    rows, cum, low_point, break_even = [], 0.0, 0.0, None
    for i in range(12):
        v = {k: round(series[i] * scale) for k, series in VOLUMES.items()}

        # Revenue by lane
        paid_open = v["open_tasks"] * (FEE_FREE_SHARE_M1_2 if i < 2 else 1.0)
        r_open = paid_open * PRICE["open_task"][0] * PRICE["open_task"][1]
        if i >= 2:
            r_open += v["open_tasks"] * PRIORITY_SHARE * PRIORITY_BOOST
        r_pkg = v["packages"] * PRICE["package"][0] * PRICE["package"][1]
        r_so = v["standing_orders"] * PRICE["standing_order"][0] * PRICE["standing_order"][1]
        r_seat = v["agent_seats"] * PRICE["agent_seat"][0] * PRICE["agent_seat"][1]
        r_api = v["api_calls"] * PRICE["api_call"][0] * PRICE["api_call"][1]
        r_sw = v["pro_subs"] * PRO_PLAN + v["private_boards"] * PRIVATE_BOARD
        revenue = r_open + r_pkg + r_so + r_seat + r_api + r_sw

        # Buyer spend (GMV) and direct costs
        gmv = (v["open_tasks"] * PRICE["open_task"][0] + v["packages"] * PRICE["package"][0]
               + v["standing_orders"] * PRICE["standing_order"][0]
               + v["agent_seats"] * PRICE["agent_seat"][0] + v["api_calls"] * PRICE["api_call"][0])
        lane_cost = (v["open_tasks"] * DIRECT_COST["open_task"] + v["packages"] * DIRECT_COST["package"]
                     + v["standing_orders"] * DIRECT_COST["standing_order"]
                     + v["agent_seats"] * DIRECT_COST["agent_seat"]
                     + v["api_calls"] * DIRECT_COST["api_call"]
                     + v["private_boards"] * DIRECT_COST["private_board"])

        contribution = revenue - lane_cost
        result = contribution - FIXED_COST[i]
        cum += result
        low_point = min(low_point, cum)
        if break_even is None and result > 0:
            break_even = i + 1

        rows.append(dict(month=i + 1, **v, gmv=round(gmv),
                         rev_open=round(r_open), rev_packages=round(r_pkg), rev_standing=round(r_so),
                         rev_seats=round(r_seat), rev_api=round(r_api), rev_software=round(r_sw),
                         revenue=round(revenue), lane_cost=round(lane_cost),
                         contribution=round(contribution), fixed_cost=FIXED_COST[i], result=round(result)))
    summary = dict(break_even_month=break_even, funding_needed=round(-low_point),
                   year_revenue=sum(r["revenue"] for r in rows),
                   year_result=sum(r["result"] for r in rows),
                   year_gmv=sum(r["gmv"] for r in rows))
    return rows, summary


# ---------------------------------------------------------------------------
# 3. Figures published in the plan (Sections 1, 6, 7, 8 and 11). --check
#    recomputes each one and fails if the plan and the model disagree.
# ---------------------------------------------------------------------------
def published_checks(results):
    base_rows, base = results["Base"]
    m12 = base_rows[-1]
    yield "Base month-12 revenue", m12["revenue"], 35910
    yield "Base month-12 lane costs", m12["lane_cost"], 8250
    yield "Base month-12 contribution", m12["contribution"], 27660
    yield "Base month-12 operating result", m12["result"], 16660
    yield "Base month-12 open-board revenue", m12["rev_open"], 4950
    yield "Base month-12 packages revenue", m12["rev_packages"], 12500
    yield "Base month-12 standing-order revenue", m12["rev_standing"], 9000
    yield "Base month-12 seat revenue", m12["rev_seats"], 4200
    yield "Base month-12 API revenue", m12["rev_api"], 1600
    yield "Base month-12 software revenue", m12["rev_software"], 3660
    yield "Base month-12 GMV", m12["gmv"], 172000
    yield "Base break-even month", base["break_even_month"], 8
    yield "Base funding needed", base["funding_needed"], 35123
    yield "Base year-one revenue", base["year_revenue"], 166557
    yield "Base year-one result", base["year_result"], 11444
    yield "Base 90-day contribution, months 10-12", sum(r["contribution"] for r in base_rows[9:12]), 71310
    for name, rev, res, be, fund, yrev, yres in [
        ("Conservative", 21651, 5681, 10, 49312, 100468, -39477),
        ("Optimistic", 54115, 30715, 6, 25436, 250469, 76210),
    ]:
        rows, s = results[name]
        yield f"{name} month-12 revenue", rows[-1]["revenue"], rev
        yield f"{name} month-12 result", rows[-1]["result"], res
        yield f"{name} break-even month", s["break_even_month"], be
        yield f"{name} funding needed", s["funding_needed"], fund
        yield f"{name} year-one revenue", s["year_revenue"], yrev
        yield f"{name} year-one result", s["year_result"], yres
    # Section 7 monthly targets table (base)
    for month, rev, res in [(1, 80, -5955), (2, 472, -5710), (3, 1791, -4655),
                            (6, 9557, -3592), (9, 21762, 5859), (12, 35910, 16660)]:
        r = base_rows[month - 1]
        yield f"Base month-{month} revenue", r["revenue"], rev
        yield f"Base month-{month} result", r["result"], res


def main():
    results = {name: run(scale) for name, scale in SCENARIOS.items()}

    if "--check" in sys.argv:
        failures = [(label, got, want) for label, got, want in published_checks(results) if got != want]
        total = sum(1 for _ in published_checks(results))
        for label, got, want in failures:
            print(f"MISMATCH  {label}: model {got}, plan {want}")
        print(f"{total - len(failures)}/{total} published figures match the model.")
        sys.exit(1 if failures else 0)

    if "--csv" in sys.argv:
        out = Path(__file__).with_name("output.csv")
        with out.open("w", newline="") as f:
            w = None
            for name, (rows, _) in results.items():
                for r in rows:
                    if w is None:
                        w = csv.DictWriter(f, fieldnames=["scenario", *r.keys()])
                        w.writeheader()
                    w.writerow({"scenario": name, **r})
        print(f"Wrote {out}")
        return

    for name, (rows, s) in results.items():
        m12 = rows[-1]
        print(f"{name:<12} month-12 revenue ${m12['revenue']:,}  result ${m12['result']:,}  "
              f"break-even month {s['break_even_month']}  funding ${s['funding_needed']:,}  "
              f"year-one revenue ${s['year_revenue']:,}  result ${s['year_result']:,}")


if __name__ == "__main__":
    main()
