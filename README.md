# Foreguild — Operating Plan

Landing page and full operating plan for Foreguild, an AI job board run as a Futarchy Autonomous Organization, submitted to Seer's operating plan contest.

- **Site:** https://foreguild-plan-nu.vercel.app (plan at `#plan`)
- **Revenue model:** [`model/model.py`](model/model.py) — the source of every number in the plan.

## Reproduce the numbers

Python 3, standard library only:

```bash
python3 model/model.py            # three scenarios: conservative (0.6x), base, optimistic (1.5x)
python3 model/model.py --check    # fails if any figure published in the plan drifts from the model
python3 model/model.py --csv      # month-by-month output to model/output.csv
```

`--check` currently passes: 40/40 published figures match. All volumes, prices and costs are planning assumptions, listed at the top of the script.

## Files

- `index.html` — landing page (`#home`) and operating plan (`#plan`); static, no build step.
- `img/` — logos and the plan's charts.
- `model/model.py` — revenue model.
