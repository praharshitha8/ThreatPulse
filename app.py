
from flask import Flask, request, redirect, url_for, render_template_string
from threading import RLock
from datetime import datetime, timedelta
from urllib.parse import urlencode

app = Flask(__name__)
lock = RLock()

MAX_FAILURES = 5
WINDOW_MINUTES = 5
BLOCK_MINUTES = 2

DEMO_USERNAME = "student"
DEMO_PASSWORD = "Demo123!"

failed_attempts = {}
blocked_until = {}
events = []

totals = {
    "checks": 0,
    "failed": 0,
    "blocked": 0,
    "success": 0
}


def log_event(kind, message):
    events.insert(0, {
        "time": datetime.now().strftime("%H:%M:%S"),
        "kind": kind,
        "message": message
    })
    del events[12:]


def check_login(username, password):
    now = datetime.now()

    with lock:
        totals["checks"] += 1

        until = blocked_until.get(username)

        if until and until > now:
            log_event("blocked", f"Login blocked for {username}")
            return (
                "Account temporarily blocked. Try again later.",
                "error"
            )

        if until and until <= now:
            blocked_until.pop(username, None)
            failed_attempts.pop(username, None)

        attempts = [
            t for t in failed_attempts.get(username, [])
            if now - t < timedelta(minutes=WINDOW_MINUTES)
        ]
        failed_attempts[username] = attempts

        if username == DEMO_USERNAME and password == DEMO_PASSWORD:
            failed_attempts.pop(username, None)
            totals["success"] += 1
            log_event("success", f"Successful login: {username}")

            return "Login successful!", "success"

        attempts.append(now)
        failed_attempts[username] = attempts
        totals["failed"] += 1

        if len(attempts) >= MAX_FAILURES:
            blocked_until[username] = (
                now + timedelta(minutes=BLOCK_MINUTES)
            )
            totals["blocked"] += 1

            log_event(
                "blocked",
                f"Repeated failures detected for {username}"
            )

            return "Too many failed attempts. Account temporarily blocked.", "error"

        log_event("failed", f"Failed login attempt: {username or 'unknown'}")

        return (
            f"Login failed. Attempts: {len(attempts)}/{MAX_FAILURES}.",
            "error"
        )


PAGE = r'''
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ThreatPulse</title>

<style>
:root {
    color-scheme: dark;
    --bg: #0a1020;
    --panel: #111b30;
    --line: #26344d;
    --muted: #91a0b8;
    --text: #eef4ff;
    --blue: #70adff;
    --green: #51d6a0;
    --red: #ff7485;
}

* { box-sizing: border-box; }

body {
    margin: 0;
    background: radial-gradient(ellipse at top left, #172c4b, transparent 42%), var(--bg);
    color: var(--text);
    font: 15px/1.5 system-ui, sans-serif;
}

.wrap {
    max-width: 1120px;
    margin: auto;
    padding: 30px 22px;
}

header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 15px;
    margin-bottom: 30px;
}

.brand {
    display: flex;
    align-items: center;
    gap: 12px;
}

.logo {
    width: 43px;
    height: 43px;
    display: grid;
    place-items: center;
    border-radius: 13px;
    background: linear-gradient(135deg, #65b2ff, #7774f5);
    color: #071226;
    font-size: 25px;
    font-weight: 900;
}

h1, h2, h3, p { margin-top: 0; }

h1 { margin-bottom: 0; font-size: 22px; }
h2 { font-size: 27px; margin-bottom: 5px; }
h3 { font-size: 16px; margin-bottom: 5px; }

.subtitle, .muted { color: var(--muted); }
.subtitle { margin-bottom: 0; font-size: 12px; }
.muted { font-size: 13px; margin-bottom: 20px; }

.status {
    color: #8be5c2;
    background: #102c2b;
    border: 1px solid #285b50;
    border-radius: 30px;
    padding: 7px 12px;
    font-size: 12px;
    white-space: nowrap;
}

.intro { margin-bottom: 23px; }
.intro p { color: var(--muted); margin-bottom: 0; }

.stats {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 13px;
    margin-bottom: 18px;
}

.stat, .panel {
    background: linear-gradient(145deg, #141f35, #0e1729);
    border: 1px solid var(--line);
    border-radius: 16px;
}

.stat { padding: 17px; }
.label { color: var(--muted); font-size: 12px; }
.value { font-size: 29px; font-weight: 700; margin-top: 5px; }
.sub { font-size: 11px; color: #8292ab; margin-top: 2px; }

.main {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 17px;
}

.panel { padding: 22px; }

.field { margin-bottom: 14px; }

label {
    display: block;
    font-size: 13px;
    margin-bottom: 7px;
    color: #c5d0e2;
}

input {
    width: 100%;
    background: #0b1425;
    border: 1px solid #31415d;
    border-radius: 10px;
    padding: 12px;
    color: var(--text);
    font: inherit;
    outline: none;
}

input:focus { border-color: var(--blue); }

button {
    width: 100%;
    border: 0;
    border-radius: 10px;
    padding: 12px;
    background: linear-gradient(100deg, #67b1ff, #7c8cff);
    color: #081225;
    font-weight: 750;
    font-size: 14px;
    cursor: pointer;
}

button:disabled { opacity: .7; cursor: wait; }

.hint {
    color: var(--muted);
    font-size: 12px;
    margin: 12px 0 0;
}

code {
    color: #c6d9ff;
    background: #1b2940;
    padding: 2px 5px;
    border-radius: 5px;
}

.result {
    padding: 11px 12px;
    border-radius: 10px;
    margin-bottom: 15px;
    font-size: 13px;
}

.success {
    background: #102f2b;
    border: 1px solid #286453;
    color: #9aefd0;
}

.error {
    background: #351d2b;
    border: 1px solid #704052;
    color: #ffb1bd;
}

.activity-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 15px;
}

.count {
    color: #a8b7ce;
    background: #1d2b43;
    padding: 4px 8px;
    border-radius: 7px;
    font-size: 11px;
}

.events { list-style: none; margin: 0; padding: 0; }

.event {
    display: flex;
    gap: 12px;
    padding: 13px 0;
    border-bottom: 1px solid #233149;
}

.event:last-child { border-bottom: 0; }

.dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-top: 7px;
    flex-shrink: 0;
    background: var(--blue);
}

.dot.failed, .dot.blocked { background: var(--red); }
.dot.success { background: var(--green); }

.event-main { min-width: 0; flex: 1; }
.event-msg { font-size: 13px; overflow-wrap: anywhere; }
.event-time { color: #8191aa; font-size: 11px; margin-top: 3px; }
.empty { color: var(--muted); font-size: 13px; padding: 12px 0; }

.footer {
    font-size: 11px;
    color: #71819b;
    text-align: center;
    margin-top: 22px;
}

@media (max-width: 760px) {
    .stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .main { grid-template-columns: 1fr; }
    .wrap { padding: 22px 14px; }
    h2 { font-size: 24px; }
    .panel { padding: 18px; }
}

@media (max-width: 400px) {
    .status { font-size: 10px; }
    h1 { font-size: 19px; }
}
</style>
</head>

<body>
<div class="wrap">

<header>
    <div class="brand">
        <div class="logo">ϟ</div>
        <div>
            <h1>ThreatPulse</h1>
            <p class="subtitle">Login security monitor</p>
        </div>
    </div>
    <div class="status">● Demo system online</div>
</header>

<section class="intro">
    <h2>Security overview</h2>
</section>

<section class="stats">
    <div class="stat">
        <div class="label">Threat alerts</div>
        <div class="value">{{ totals.blocked }}</div>
        <div class="sub">Accounts blocked</div>
    </div>

    <div class="stat">
        <div class="label">Failed attempts</div>
        <div class="value">{{ totals.failed }}</div>
        <div class="sub">This session</div>
    </div>

    <div class="stat">
        <div class="label">Login checks</div>
        <div class="value">{{ totals.checks }}</div>
        <div class="sub">Total submissions</div>
    </div>

    <div class="stat">
        <div class="label">Successful logins</div>
        <div class="value">{{ totals.success }}</div>
        <div class="sub">Accepted logins</div>
    </div>
</section>

<section class="main">

<div class="panel">
    <h3>Test a login</h3>

    {% if result %}
        <div class="result {{ result_type }}" role="status">
            {{ result }}
        </div>
    {% endif %}

    <form action="{{ url_for('simulate') }}" method="post" id="login-form">
        <div class="field">
            <label for="username">Username</label>
            <input id="username" name="username"
                   autocomplete="off" required maxlength="80"
                   placeholder="Enter username">
        </div>

        <div class="field">
            <label for="password">Password</label>
            <input id="password" name="password" type="password"
                   autocomplete="off" required maxlength="200"
                   placeholder="Enter password">
        </div>

        <button id="submit-btn" type="submit">Run login test</button>
    </form>

    <p class="hint">Demo: <code>student</code> / <code>Demo123!</code></p>
</div>

<div class="panel">
    <div class="activity-head">
        <h3>Recent activity</h3>
        <span class="count">{{ events|length }} events</span>
    </div>

    {% if events %}
        <ul class="events">
        {% for event in events %}
            <li class="event">
                <span class="dot {{ event.kind }}"></span>
                <div class="event-main">
                    <div class="event-msg">{{ event.message }}</div>
                    <div class="event-time">{{ event.time }}</div>
                </div>
            </li>
        {% endfor %}
        </ul>
    {% else %}
        <div class="empty">No activity yet. Run a login test.</div>
    {% endif %}
</div>

</section>

<div class="footer">
    ThreatPulse · Educational demo · No real accounts monitored
</div>

</div>

<script>
document.getElementById("login-form").addEventListener("submit", function () {
    const button = document.getElementById("submit-btn");
    button.disabled = true;
    button.textContent = "Checking...";
});
</script>
</body>
</html>
'''


@app.get("/")
def index():
    with lock:
        return render_template_string(
            PAGE,
            totals=totals.copy(),
            events=list(events),
            result=request.args.get("result"),
            result_type=request.args.get("type", "")
        )


@app.post("/simulate")
def simulate():
    username = request.form.get("username", "").strip()[:80]
    password = request.form.get("password", "")[:200]

    result, result_type = check_login(username, password)

    query = urlencode({
        "result": result,
        "type": result_type
    })

    return redirect(url_for("index") + "?" + query)


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        threaded=True
    )
