"""Step 2: running SQL with SQLAlchemy Core -- no ORM.

Run:  python -m tutorial.step2_queries

Uses a TEMP table, so nothing is left behind in your database.
"""

from sqlalchemy import text

from server import get_engine

engine = get_engine()  # the same engine the starter app uses

# engine.connect() borrows a connection from the pool.
# The `with` block gives it back (and rolls back anything uncommitted) at the end.
with engine.connect() as conn:

    # --- Write SQL as text, run it with conn.execute ---------------------------
    conn.execute(text("""
        CREATE TEMP TABLE students (
            uni   text PRIMARY KEY,
            name  text NOT NULL,
            major text
        )
    """))
    conn.execute(text("""
        INSERT INTO students VALUES
            ('ab1234', 'Ada Byron',     'Mathematics'),
            ('gh5678', 'Grace Hopper',  'Computer Science'),
            ('at9012', 'Alan Turing',   'Computer Science')
    """))
    conn.commit()  # writes are not saved until you commit

    # --- One value: scalar_one() ----------------------------------------------
    count = conn.execute(text("SELECT count(*) FROM students")).scalar_one()
    print("count:", count)

    # --- Many rows: execute() returns a Result (a cursor) ----------------------
    cursor = conn.execute(text("SELECT uni, name, major FROM students ORDER BY name"))
    for row in cursor:
        # A Row works like a tuple AND has named attributes.
        print(row[0], "|", row.name, "|", row.major)
    cursor.close()

    # --- A cursor is a one-pass iterator ---------------------------------------
    cursor = conn.execute(text("SELECT name FROM students"))
    first_pass = [row.name for row in cursor]
    second_pass = [row.name for row in cursor]  # already used up!
    print("first pass: ", first_pass)
    print("second pass:", second_pass)

    # So: turn it into a list if you need the rows more than once
    # (e.g. to pass them to a template).
    rows = conn.execute(text("SELECT uni, name FROM students")).fetchall()
    print("fetchall:", rows)

    # --- Other handy ways to read a result ------------------------------------
    one = conn.execute(text("SELECT name FROM students WHERE uni = 'gh5678'")).fetchone()
    print("fetchone:", one)

    names = conn.execute(text("SELECT name FROM students")).scalars().all()
    print("scalars().all():", names)

    dicts = conn.execute(text("SELECT uni, name FROM students")).mappings().all()
    print("mappings().all():", dicts)
    print("first dict:", dict(dicts[0]))
