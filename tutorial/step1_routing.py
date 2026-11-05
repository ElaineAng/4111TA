"""Step 1: basic Flask routing.

Run:  python server.py   then open http://127.0.0.1:8111/step1/

The routes live on a Blueprint, a group of routes that server.py
registers on its app under the /step1 prefix.
"""

from flask import Blueprint, redirect, render_template, render_template_string, request, url_for

bp = Blueprint("step1", __name__, url_prefix="/step1")


# A route maps a URL path to a Python function. Whatever it returns is the response.
@bp.route("/")
def index():
    return "Hello, W4111! Try /step1/hello/ada, /step1/square/7, or /step1/search?q=sql"


# <name> captures part of the URL and passes it as an argument.
# A template escapes it for us, so /step1/hello/<b>hi</b> shows the tags as text.
@bp.route("/hello/<name>")
def hello(name):
    return render_template_string("Hello, {{ name }}!", name=name)


# A converter (<int:...>) checks and converts the value; /step1/square/abc gives a 404.
@bp.route("/square/<int:n>")
def square(n):
    return f"{n} squared is {n * n}"


# Query-string values (?q=...) come from request.args.
@bp.route("/search")
def search():
    q = request.args.get("q", "")
    return render_template_string("You searched for: {{ q }}", q=q)


# render_template looks in templates/ and fills in the {{ variables }}.
@bp.route("/page")
def page():
    return render_template("step1_page.html", title="My first template", items=["SELECT", "FROM", "WHERE"])


# GET shows the form, POST receives it. url_for builds URLs from "blueprint.function" names.
@bp.route("/echo", methods=["GET", "POST"])
def echo():
    if request.method == "POST":
        message = request.form["message"]
        return redirect(url_for("step1.hello", name=message))
    return render_template("step1_form.html")
