"""Step 3: parameterized queries vs. SQL injection.

Run:  python -m tutorial.step3_parameters

Uses a TEMP table, so nothing is left behind in your database.
"""

from sqlalchemy import text

from server import get_engine

engine = get_engine()  # the same engine the starter app uses

with engine.connect() as conn:
    conn.execute(text("CREATE TEMP TABLE accounts (username text, secret text)"))
    conn.execute(text("""
        INSERT INTO accounts VALUES
            ('alice', 'alice-secret'),
            ('bob',   'bob-secret')
    """))

    # Pretend this came from a form: request.form["username"]
    user_input = "nobody' OR '1'='1"

    # --- WRONG: building SQL with an f-string ---------------------------------
    unsafe_sql = f"SELECT * FROM accounts WHERE username = '{user_input}'"
    print("The query the database actually sees:")
    print("   ", unsafe_sql)
    print("Rows returned (should be none!):")
    for row in conn.execute(text(unsafe_sql)):
        print("   ", row)

    # --- RIGHT: a named parameter, value passed separately --------------------
    safe_sql = text("SELECT * FROM accounts WHERE username = :username")
    rows = conn.execute(safe_sql, {"username": user_input}).fetchall()
    print("\nWith a parameter, rows returned:", rows)

    # --- WORSE: input that ends the query and starts a new one ----------------
    # A harmless throwaway table plays the victim.
    conn.execute(text("CREATE TEMP TABLE victim (id int)"))
    exists = text("SELECT to_regclass('victim') IS NOT NULL")
    print("\nvictim table exists?", conn.execute(exists).scalar_one())

    evil_input = "x'; DROP TABLE victim; --"

    # Safe first: the whole input is just a string to compare against.
    conn.execute(text("SELECT * FROM accounts WHERE username = :username"), {"username": evil_input})
    print("after the parameterized query, victim exists?", conn.execute(exists).scalar_one())

    # Unsafe: the quote closes the string, ';' ends the SELECT, '--' comments out the rest.
    unsafe_sql = f"SELECT * FROM accounts WHERE username = '{evil_input}'"
    print("The query the database actually sees:")
    print("   ", unsafe_sql)
    conn.execute(text(unsafe_sql))
    print("after the f-string query, victim exists?", conn.execute(exists).scalar_one())

    # --- Parameters for every value: INSERT, several params, LIKE --------------
    conn.execute(
        text("INSERT INTO accounts (username, secret) VALUES (:u, :s)"),
        {"u": "O'Brien", "s": "quotes are fine"},  # no escaping needed
    )
    search = "b"
    rows = conn.execute(
        text("SELECT username FROM accounts WHERE username ILIKE :pattern"),
        {"pattern": f"%{search}%"},  # wildcards go in the VALUE, not the SQL
    ).fetchall()
    print("LIKE search:", rows)

    # --- Parameters are for VALUES only, not table or column names ------------
    # text("SELECT * FROM accounts ORDER BY :col") sends ORDER BY 'username' -- a string, so Postgres errors
    # Instead, check the name against a fixed list you control:
    sort_by = "secret"  # e.g. from request.args
    if sort_by not in {"username", "secret"}:
        sort_by = "username"
    rows = conn.execute(text(f"SELECT username FROM accounts ORDER BY {sort_by}")).fetchall()
    print("sorted by", sort_by, ":", rows)
