# Report 05 - UX and Product

## Finding 05-01: Frontend calls a different API base
Problem / risk:
- The UI uses `/test/api/*`, but the backend routes are `/api/*`, so the page will not load data without additional routing.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 5, Risk 2, Effort S
Recommendation:
- Align the API prefix in JS or add a backend prefix that matches the UI.
DoD (acceptance criteria):
- The test panel loads status and relays with no console errors.
Related files:
- `static/app.js`: `const API_PREFIX = "/test/api";`
- `app_legacy.py`: `@app.route("/api/status")`
Notes / assumptions:
- No blueprint or reverse proxy is defined in this folder.

## Finding 05-02: Static assets reference a missing blueprint
Problem / risk:
- The template uses `url_for('test_panel.static')` but `app_legacy.py` does not define a `test_panel` blueprint, causing 404 for CSS/JS.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 4, Risk 2, Effort S
Recommendation:
- Use `url_for('static', ...)` or add a blueprint with the correct name.
DoD (acceptance criteria):
- CSS and JS load without 404 errors.
Related files:
- `templates/index.html`: `url_for('test_panel.static', filename='style.css')`
- `app_legacy.py`: `app = Flask(__name__)`
Notes / assumptions:
- The default Flask static folder is used by `app = Flask(__name__)`.

## Finding 05-03: UI expects safe_mode but backend returns safety.test_mode
Problem / risk:
- The UI reads `st.safe_mode`, which is not present in `/api/status`. This causes incorrect display of safety state.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 4, Risk 2, Effort S
Recommendation:
- Align naming (either add `safe_mode` to API or update UI to use `safety.test_mode`).
DoD (acceptance criteria):
- The safety indicator correctly reflects backend state.
Related files:
- `static/app.js`: `setText("safeModeVal", st.safe_mode ? "ON" : "OFF");`
- `app_legacy.py`: `"safety": { "test_mode": ... }`
Notes / assumptions:
- The mismatch is visible on initial page load.

## Finding 05-04: Link to /dashboard may be dead in this app
Problem / risk:
- The UI provides a link to `/dashboard` but there is no matching route in `app_legacy.py`.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 2, Risk 1, Effort S
Recommendation:
- Remove or update the link to a valid route for this app.
DoD (acceptance criteria):
- Navigation links only target defined routes.
Related files:
- `templates/index.html`: `<a class="btn" href="/dashboard">Ana Panel</a>`
- `app_legacy.py`: `@app.route("/")`
Notes / assumptions:
- This app only defines `"/"` for the UI.

## Finding 05-05: Relay controls lack confirm or safety context
Problem / risk:
- Relay buttons allow immediate ON/OFF/pulse without confirmation, which is risky for heater or pump actions.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 3, Risk 3, Effort S
Recommendation:
- Add confirmations or a safety banner for pump/heater actions.
DoD (acceptance criteria):
- Unsafe actions require explicit confirmation or are gated by a visible safety toggle.
Related files:
- `static/app.js`: `onclick="relayOn('${key}')"`
- `static/app.js`: `onclick="relayPulse('${key}',10)"`
Notes / assumptions:
- The backend enforces test_mode but the UI does not explain it clearly.

## Finding 05-06: Config form lacks guidance for reserved pins
Problem / risk:
- The UI allows any GPIO number but does not show reserved pins or conflicts, increasing misconfiguration risk.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 3, Risk 2, Effort S
Recommendation:
- Add inline hints for reserved pins (2/3 for I2C) and show validation errors prominently.
DoD (acceptance criteria):
- Users see clear guidance and errors before saving config.
Related files:
- `static/app.js`: `<input type="number" min="0" max="27" data-relaykey="${key}">`
- `app_legacy.py`: `reserved = {2, 3}`
Notes / assumptions:
- Validation exists server-side but the UI does not explain it.
