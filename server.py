"""COMS W4111 example webserver, adapted for Cloud Run and direct SQL.

Run locally with Python 3.14: python3 server.py
Cloud Run uses the Gunicorn command in Procfile instead of Flask's dev server.
"""

import os
from functools import lru_cache

from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from sqlalchemy import URL, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from tutorial.step1_routing import bp as step1_bp
from tutorial.step4_app import bp as step4_bp

load_dotenv()  # read DB_USER / DB_PASSWORD from .env, even when server is imported

app = Flask(__name__)

# Tutorial demo pages at /step1/ and /step4/ (see tutorial/README.md).
app.register_blueprint(step1_bp)
app.register_blueprint(step4_bp)


@lru_cache(maxsize=1)
def get_engine():
    """Configure the connection pool without opening a connection at import."""
    database_url = URL.create(
        "postgresql+psycopg2",  # dialect+driver: PostgreSQL, via the psycopg2 package
        username=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        port=int(os.environ.get("DB_PORT", "5454")),
        database=os.environ.get("DB_NAME", "proj1part2"),
    )
    return create_engine(
        database_url,
        pool_size=1,
        max_overflow=0,
        pool_pre_ping=True,
        pool_timeout=5,
        connect_args={
            "connect_timeout": 5,
            "options": "-c statement_timeout=5000",
        },
    )


@app.before_request
def before_request():
    """Make a connection available as g.conn for database-backed routes."""
    g.conn = None
    g.database_error = None
    g.database_configured = bool(
        os.environ.get("DB_USER") and os.environ.get("DB_PASSWORD")
    )
    if (
        request.endpoint not in {"index", "add", "initialize", "database_check"}
        and request.blueprint != "step4"
    ):
        return
    if not g.database_configured:
        g.database_error = "Database credentials are not configured yet. Follow the Cloud Run setup guide."
        return
    try:
        g.conn = get_engine().connect()
        schema = os.environ.get("DB_SCHEMA")
        if schema:
            # Bind the schema value and quote it as one identifier, not raw SQL.
            g.conn.execute(
                text(
                    "SELECT set_config('search_path', quote_ident(:schema), false)"
                ),
                {"schema": schema},
            )
            g.conn.commit()
    except (SQLAlchemyError, ValueError, KeyError) as exc:
        # Driver exception messages can contain credentials or connection details.
        app.logger.warning(
            "Database connection failed (%s)", type(exc).__name__
        )
        if g.conn is not None:
            g.conn.close()
            g.conn = None
        g.database_error = "The database is unavailable. Check the proxy, secrets, and application logs."


@app.teardown_request
def teardown_request(exception):
    """Return the connection to the pool, rolling back unfinished work."""
    conn = g.pop("conn", None)
    if conn is not None:
        conn.close()


def render_index(data=None, table_exists=False, error=None, status=200):
    return render_template(
        "index.html",
        data=data or [],
        table_exists=table_exists,
        database_ready=g.get("conn") is not None,
        error=error,
    ), status


def require_connection():
    if g.get("conn") is None:
        abort(503)
    return g.conn


@app.errorhandler(SQLAlchemyError)
def database_error(error):
    conn = g.get("conn")
    if conn is not None:
        conn.rollback()
    app.logger.warning("Database operation failed (%s)", type(error).__name__)
    if request.endpoint == "database_check":
        return jsonify(database="unavailable"), 503
    return render_index(
        error="The database operation could not be completed. Check the application logs.",
        status=503,
    )


@app.errorhandler(503)
def unavailable(error):
    if request.endpoint == "database_check":
        return jsonify(database="unavailable"), 503
    return render_index(
        error=g.get("database_error") or "The database is unavailable.",
        status=503,
    )


@app.route("/")
def index():
    """Run a SQL query and pass its results to a Jinja HTML template."""
    if g.conn is None:
        # The first GitHub deployment can be previewed before secrets are added.
        status = 503 if g.database_configured else 200
        return render_index(error=g.database_error, status=status)

    table_exists = g.conn.execute(
        text("SELECT to_regclass('test') IS NOT NULL")
    ).scalar_one()
    if not table_exists:
        return render_index()

    cursor = g.conn.execute(text("SELECT name FROM test ORDER BY id"))
    names = [row[0] for row in cursor]
    cursor.close()
    return render_index(data=names, table_exists=True)


@app.route("/another")
def another():
    return render_template("another.html")


@app.route("/initialize", methods=["POST"])
def initialize():
    """Explicitly create the original example table; never create a schema."""
    conn = require_connection()
    conn.execute(
        text(
            "CREATE TABLE IF NOT EXISTS test (id serial PRIMARY KEY, name text NOT NULL)"
        )
    )
    conn.execute(
        text("""
        INSERT INTO test(name)
        SELECT seed.name
        FROM (VALUES ('grace hopper'), ('alan turing'), ('ada lovelace')) AS seed(name)
        WHERE NOT EXISTS (SELECT 1 FROM test)
    """)
    )
    conn.commit()
    return redirect(url_for("index"))


@app.route("/add", methods=["POST"])
def add():
    """Use bound parameters for user input; commit writes explicitly."""
    name = request.form.get("name", "").strip()
    if not name or len(name) > 100:
        abort(400, description="Enter a name between 1 and 100 characters.")
    conn = require_connection()
    conn.execute(text("INSERT INTO test(name) VALUES (:name)"), {"name": name})
    conn.commit()
    return redirect(url_for("index"))


@app.route("/login")
def login():
    # As in the original skeleton, this illustrates an error, not a login system.
    abort(401)


@app.route("/db-check")
def database_check():
    conn = require_connection()
    value = conn.execute(text("SELECT :value"), {"value": 1}).scalar_one()
    schema_accessible = conn.execute(
        text("""
        SELECT current_schema() IS NOT NULL
            AND has_schema_privilege(current_schema(), 'USAGE')
    """)
    ).scalar_one()
    table_exists = conn.execute(
        text("SELECT to_regclass('test') IS NOT NULL")
    ).scalar_one()
    return jsonify(
        database="ok",
        select_1=value,
        current_schema_accessible=bool(schema_accessible),
        demo_table_exists=bool(table_exists),
        revision=os.environ.get("K_REVISION", "local"),
    )


if __name__ == "__main__":
    # This is only for local development; Cloud Run runs Gunicorn via Procfile.
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "8111")))
