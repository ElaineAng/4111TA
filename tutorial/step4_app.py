"""Step 4: query results -> Jinja templates, plus forms.

Run:  python -m tutorial.setup_tutorial_table
      python server.py      then open http://127.0.0.1:8111/step4/

server.py registers this Blueprint and opens g.conn for its routes,
just like it does for the starter's own pages.
"""

from flask import Blueprint, abort, g, redirect, render_template, request, url_for
from sqlalchemy import text

bp = Blueprint("step4", __name__, url_prefix="/step4")


@bp.before_request
def require_connection():
    if g.conn is None:
        abort(503)  # server.py shows "The database is unavailable."


@bp.route("/")
def students():
    # GET form: the search box puts ?q=... in the URL.
    q = request.args.get("q", "").strip()
    cursor = g.conn.execute(
        text("""
            SELECT uni, name, major
            FROM tutorial_students
            WHERE name ILIKE :pattern
            ORDER BY name
        """),
        {"pattern": f"%{q}%"},
    )
    rows = cursor.mappings().all()  # a list of dict-like rows, safe to loop over in the template
    cursor.close()
    return render_template("step4_students.html", rows=rows, q=q)


@bp.route("/students/<uni>")
def student_detail(uni):
    row = g.conn.execute(
        text("SELECT uni, name, major FROM tutorial_students WHERE uni = :uni"),
        {"uni": uni},
    ).mappings().first()  # the row, or None if no student has this UNI
    # The template shows a friendly message when student is None.
    return render_template("step4_detail.html", student=row, uni=uni)


@bp.route("/add", methods=["POST"])
def add_student():
    # POST form: values arrive in request.form.
    uni = request.form.get("uni", "").strip()
    name = request.form.get("name", "").strip()
    major = request.form.get("major", "").strip() or None  # empty -> NULL
    if not uni or not name:
        abort(400, description="UNI and name are required.")

    g.conn.execute(
        text("INSERT INTO tutorial_students (uni, name, major) VALUES (:uni, :name, :major)"),
        {"uni": uni, "name": name, "major": major},
    )
    g.conn.commit()
    # Redirect after POST so refreshing the page doesn't submit twice.
    return redirect(url_for("step4.students"))
