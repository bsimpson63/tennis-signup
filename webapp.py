#!/usr/bin/env python3
"""
Web UI for managing tennis class signup configuration.
Run with: python3 webapp.py
Access at: http://<host>:5000
"""

import json
import pathlib
from flask import Flask, request, redirect, url_for, render_template_string

app = Flask(__name__)

SETTINGS_PATH = pathlib.Path(__file__).parent / "settings.json"
LOG_PATH = pathlib.Path(__file__).parent / "signup.log"

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def load_settings():
    if SETTINGS_PATH.exists():
        try:
            return json.loads(SETTINGS_PATH.read_text())
        except Exception:
            pass
    return {"schedules": [], "dry_run": False}


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
      <h2>Schedule</h2>
      <p>On each scheduled day the script will find and register for the first open class whose name contains the configured string (case-insensitive).</p>
      {% if schedules %}
      <figure>
        <table>
          <thead><tr><th>Day</th><th>Class name</th><th></th></tr></thead>
          <tbody>
            {% for i, s in enumerate(schedules) %}
            <tr>
              <td>{{ s.day.capitalize() }}</td>
              <td>{{ s.class_name }}</td>
              <td>
                <form class="remove-form" method="post" action="/schedule/delete/{{ i }}">
                  <button class="remove-btn secondary outline" type="submit">Remove</button>
                </form>
              </td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </figure>
      {% else %}
      <p><em>No classes scheduled yet.</em></p>
      {% endif %}

      <details>
        <summary role="button" class="outline">Add class</summary>
        <form method="post" action="/schedule/add" style="margin-top:1rem">
          <div class="grid">
            <label>Day
              <select name="day" required>
                {% for day in days %}
                <option value="{{ day }}">{{ day.capitalize() }}</option>
                {% endfor %}
              </select>
            </label>
            <label>Class name
              <input type="text" name="class_name" placeholder="e.g. Pro On Duty Advanced Monday AM" required>
            </label>
          </div>
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
</body>
</html>"""


@app.route("/")
def index():
    settings = load_settings()
    return render_template_string(
        TEMPLATE,
        schedules=settings.get("schedules", []),
        dry_run=settings.get("dry_run", False),
        log=read_log(),
        days=DAYS,
        enumerate=enumerate,
    )


@app.route("/schedule/add", methods=["POST"])
def schedule_add():
    settings = load_settings()
    class_name = request.form.get("class_name", "").strip()
    day = request.form.get("day", "").strip().lower()
    if class_name and day in DAYS:
        settings.setdefault("schedules", []).append({"class_name": class_name, "day": day})
        save_settings(settings)
    return redirect(url_for("index"))


@app.route("/schedule/delete/<int:idx>", methods=["POST"])
def schedule_delete(idx):
    settings = load_settings()
    schedules = settings.get("schedules", [])
    if 0 <= idx < len(schedules):
        schedules.pop(idx)
        settings["schedules"] = schedules
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
