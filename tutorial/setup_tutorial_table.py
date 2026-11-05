"""Create (or drop) the small table that step4_app.py uses.

    python -m tutorial.setup_tutorial_table          # create + seed
    python -m tutorial.setup_tutorial_table --drop   # remove it again
"""

import sys

from sqlalchemy import text

from server import get_engine

engine = get_engine()  # the same engine the starter app uses

# engine.begin() opens a connection AND a transaction; it commits on success.
with engine.begin() as conn:
    if "--drop" in sys.argv:
        conn.execute(text("DROP TABLE IF EXISTS tutorial_students"))
        print("Dropped tutorial_students")
    else:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tutorial_students (
                uni   text PRIMARY KEY,
                name  text NOT NULL,
                major text
            )
        """))
        conn.execute(text("""
            INSERT INTO tutorial_students VALUES
                ('ab1234', 'Ada Byron',    'Mathematics'),
                ('gh5678', 'Grace Hopper', 'Computer Science'),
                ('at9012', 'Alan Turing',  'Computer Science')
            ON CONFLICT (uni) DO NOTHING
        """))
        print("Created tutorial_students")
