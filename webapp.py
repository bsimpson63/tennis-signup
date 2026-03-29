#!/usr/bin/env python3
"""
Web UI for managing tennis class signup configuration.
Run with: python3 webapp.py
Access at: http://<host>:5000
"""

import json
import pathlib
import subprocess
from flask import Flask, request, redirect, url_for, render_template_string

app = Flask(__name__)

SETTINGS_PATH = pathlib.Path(__file__).parent / "settings.json"
LOG_PATH = pathlib.Path(__file__).parent / "signup.log"


def git_hash():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=pathlib.Path(__file__).parent,
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        return "unknown"


def load_settings():
    if SETTINGS_PATH.exists():
        try:
            return json.loads(SETTINGS_PATH.read_text())
        except Exception:
            pass
    return {"class_names": [], "dry_run": False}


def save_settings(settings):
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2))


def read_log(n=80):
    if not LOG_PATH.exists():
        return "(no log yet)"
    lines = LOG_PATH.read_text().splitlines()
    return "\n".join(lines[-n:])


TEMPLATE = """<!doctype html>
<html lang="en" data-theme="light">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Tennis Signup</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.classless.min.css">
  <style>
    pre { font-size: 0.75rem; max-height: 400px; overflow-y: auto; white-space: pre-wrap; }
    .remove-form { margin: 0; }
    .remove-btn { padding: 0.2rem 0.6rem; font-size: 0.8rem; }
    td { vertical-align: middle; }
  </style>
</head>
<body>
  <main>
    <h1>Tennis Signup</h1>
    <p><a href="https://wac.clubautomation.com/calendar/classes?tab=by-date" target="_blank">View class calendar</a></p>

    <section>
      <h2>Classes</h2>
      <p>Each night the script registers for the first open class whose name contains one of the strings below (case-insensitive).</p>
      {% if class_names %}
      <figure>
        <table>
          <thead><tr><th>Class name</th><th></th></tr></thead>
          <tbody>
            {% for i, name in enumerate(class_names) %}
            <tr>
              <td>{{ name }}</td>
              <td>
                <form class="remove-form" method="post" action="/class/delete/{{ i }}">
                  <button class="remove-btn secondary outline" type="submit">Remove</button>
                </form>
              </td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </figure>
      {% else %}
      <p><em>No classes configured yet.</em></p>
      {% endif %}

      <details>
        <summary role="button" class="outline">Add class</summary>
        <form method="post" action="/class/add" style="margin-top:1rem">
          <label>Class name
            <input type="text" name="class_name" placeholder="e.g. Pro On Duty Advanced Monday AM" required>
          </label>
          <small>Enter the name as it appears on the <a href="https://wac.clubautomation.com/calendar/classes?tab=by-date" target="_blank">website</a>. Partial, case-insensitive match is used.</small>
          <br>
          <button type="submit" style="margin-top:0.75rem">Add</button>
        </form>
      </details>
    </section>

    <section>
      <h2>Settings</h2>
      <form method="post" action="/settings">
        <fieldset>
          <label>
            <input type="checkbox" name="dry_run" role="switch" {% if dry_run %}checked{% endif %}>
            Dry run &mdash; find classes but do not register
          </label>
        </fieldset>
        <button type="submit">Save</button>
      </form>
    </section>

    <section>
      <h2>Recent log</h2>
      <pre>{{ log }}</pre>
    </section>
  </main>
  <footer style="text-align:center; padding: 1rem; font-size: 0.75rem; color: var(--pico-muted-color);">
    version {{ git_hash }}
  </footer>
</body>
</html>"""


@app.route("/")
def index():
    settings = load_settings()
    return render_template_string(
        TEMPLATE,
        class_names=settings.get("class_names", []),
        dry_run=settings.get("dry_run", False),
        log=read_log(),
        enumerate=enumerate,
        git_hash=git_hash(),
    )


@app.route("/class/add", methods=["POST"])
def class_add():
    settings = load_settings()
    class_name = request.form.get("class_name", "").strip()
    if class_name:
        settings.setdefault("class_names", []).append(class_name)
        save_settings(settings)
    return redirect(url_for("index"))


@app.route("/class/delete/<int:idx>", methods=["POST"])
def class_delete(idx):
    settings = load_settings()
    class_names = settings.get("class_names", [])
    if 0 <= idx < len(class_names):
        class_names.pop(idx)
        settings["class_names"] = class_names
        save_settings(settings)
    return redirect(url_for("index"))


@app.route("/settings", methods=["POST"])
def settings_update():
    settings = load_settings()
    settings["dry_run"] = "dry_run" in request.form
    save_settings(settings)
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
