# COMS W4111 Project 1 Flask Starter

This is the course's example Flask webserver, adapted for **Python 3.14.6**
and **Google Cloud Run**. It uses SQLAlchemy connections and explicit,
parameterized SQL, not an ORM.

## Getting started

Follow the Project 1 Part 3 webpage to create your team's private
GitHub repository. Then open [`docs/cloud-run-setup.html`](docs/cloud-run-setup.html)
for the Console-only setup instructions. These continue from the Google Cloud
project, proxy key, and PostgreSQL account you already used for Part 2.

## Local development

1. Follow the assignment instructions to create a virtual environment.
2. Install dependencies from `requirements.txt` with `pip`.
3. Create a private `.env` file. Flask loads `.env` when you run `python server.py`.
4. Run the Cloud SQL Auth Proxy on the same computer as the local app.

> [!WARNING]
> Never commit `.env` or include it in your submission.

## What to commit

Commit and push the contents of this directory at the **root** of your team's
repository, including `.python-version`, `.gitignore`, and `.gcloudignore`.

Do **not** commit:

- the ZIP itself
- an enclosing directory
- `proxy-key.json`
- database passwords
- `.env` files
- local virtual environments

## Files

| Path                       | Description                            |
| -------------------------- | -------------------------------------- |
| `server.py`                | Flask routes and direct SQL examples   |
| `requirements.txt`         | Python dependencies                    |
| `Procfile`                 | Gunicorn startup command for Cloud Run |
| `.python-version`          | Python runtime selection               |
| `templates/`               | Example HTML templates                 |
| `static/`                  | Example stylesheet                     |
| `docs/cloud-run-setup.html`| Setup instructions                     |
| `tests/test_server.py`     | Tests with mocked database connections |

## Example table

The starter does not create tables when imported. If the example test table
is missing, click **Initialize example table** on the homepage. The button
disappears once the table exists. No extra setting or deployment is needed.

Replace the example routes and templates with your own Part 3 application.
Do not initialize over meaningful existing data.

## Note

This is a public teaching example, not an authenticated application.
Use invented demonstration data and never commit credentials.
