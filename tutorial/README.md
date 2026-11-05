# Flask + PostgreSQL tutorial demos

Small, runnable examples for each part of the tutorial. They reuse the
starter app: `server.py` registers the step 1 and step 4 routes on its `app`
(so they run locally and on Cloud Run), and every script uses `get_engine()`
from `server.py`, so there is one app and one engine configuration.

Run them from the repository root with your virtual environment active, the
Cloud SQL Auth Proxy running on `127.0.0.1:5454`, and `DB_USER` /
`DB_PASSWORD` in `.env`.

| File | Concept |
| --- | --- |
| `step1_routing.py` | Routes, URL variables, `request.args`, templates, GET vs POST (at `/step1/`) |
| `step2_queries.py` | `conn.execute(text(...))`, reading rows, one-pass cursors, `commit()` |
| `step3_parameters.py` | SQL injection with f-strings vs. `:named` parameters |
| `step4_app.py` | Query results in a Jinja table, GET search form, POST insert form (at `/step4/`) |
| `setup_tutorial_table.py` | Creates / drops the `tutorial_students` table used by step 4 |

```bash
python -m tutorial.step2_queries          # prints to the terminal (TEMP table)
python -m tutorial.step3_parameters       # prints to the terminal (TEMP table)

python -m tutorial.setup_tutorial_table
python server.py                          # http://127.0.0.1:8111/step1/ and /step4/
python -m tutorial.setup_tutorial_table --drop
```
