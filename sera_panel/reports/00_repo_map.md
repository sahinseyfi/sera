# Report 00 - Repo Map

## Finding 00-01: Launcher entrypoint defers to parent app
Problem / risk:
- The local entrypoint in this folder is a thin launcher that imports a parent-level module, which makes the effective runtime code live outside this folder. This can create drift between what is audited here and what runs in production.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 4, Risk 2, Effort M
Recommendation:
- Decide whether this folder should be self-contained (run app_legacy.py) or keep the launcher but document the dependency on the parent app explicitly.
DoD (acceptance criteria):
- Clear run target documented; no ambiguity on which app is used in production.
Related files:
- `app.py`: `import app as merged_app`
- `app.py`: `app.run(host="0.0.0.0", port=5000, debug=merged_app.SIMULATION_MODE)`
Notes / assumptions:
- This report only inspects `/home/sahin/sera_panel` per scope.

## Finding 00-02: Legacy app holds most runtime logic
Problem / risk:
- The actual Flask routes, sensor loop, and relay safety logic are implemented in `app_legacy.py`, which suggests two parallel code paths (launcher vs legacy). This can confuse maintenance and testing.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 4, Risk 2, Effort M
Recommendation:
- Consolidate to a single runtime app or explicitly mark `app_legacy.py` as the canonical implementation.
DoD (acceptance criteria):
- One clear entrypoint with documented ownership; duplicate logic removed or archived.
Related files:
- `app_legacy.py`: `app = Flask(__name__)`
- `app_legacy.py`: `@app.route("/api/status")`
Notes / assumptions:
- Current routes and safety logic are only present in `app_legacy.py` within this folder.

## Finding 00-03: Config sources are duplicated
Problem / risk:
- `config.json` includes both `channels` and `relays`, while a separate `config/channels.json` exists. This invites drift and unclear source of truth.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 3, Risk 2, Effort M
Recommendation:
- Choose a single mapping source (relays or channels), and document or remove the duplicate path.
DoD (acceptance criteria):
- One canonical mapping file; code references only that file.
Related files:
- `config.json`: `"channels": {` and `"relays": {`
- `config/channels.json`: `"channels": {`
Notes / assumptions:
- `config.json` is the file loaded by `app_legacy.py`.

## Finding 00-04: UI assets define a test panel only
Problem / risk:
- The UI in this folder is a single test panel page, which may not match the broader dashboard and settings mentioned in docs.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 2, Risk 2, Effort M
Recommendation:
- Clarify the intended UX scope for this folder (test-only vs full panel), and update UI assets accordingly.
DoD (acceptance criteria):
- UI scope documented and aligned with available routes and APIs.
Related files:
- `templates/index.html`: `<div id="relayList" class="relay-list"></div>`
- `static/app.js`: `const API_PREFIX = "/test/api";`
Notes / assumptions:
- The UI uses the `/test/api` prefix which is not present in `app_legacy.py`.

## Finding 00-05: Hardware test tooling exists outside the Flask UI
Problem / risk:
- Hardware test workflows are split between shell scripts and a Python CLI tool, without a single, consolidated entrypoint or shared configuration.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 2, Risk 2, Effort M
Recommendation:
- Document the intended usage order and align the tools with the same active_low / pin config source.
DoD (acceptance criteria):
- One documented test flow; tools reference the same pin map.
Related files:
- `relay_click_test.sh`: `PINS=(18 23 24 25 20 21)`
- `tools/sera_hw_panel.py`: `RELAYS = [
    ("relay1_heater_fan", 18),`
Notes / assumptions:
- Pin lists are hardcoded in multiple locations.

## Finding 00-06: Roadmap docs mention features not present here
Problem / risk:
- Project docs reference endpoints and features (history, events, automation) that are not implemented in this folder, which may confuse contributors.
Impact (1-5), Risk (1-5), Effort (S/M/L):
- Impact 3, Risk 2, Effort M
Recommendation:
- Sync the roadmap and actual implementation scope for this folder, or link to the correct app codebase.
DoD (acceptance criteria):
- Roadmap notes either match the implemented routes or point to the correct repo/module.
Related files:
- `yol_haritasi.md`: `"/api/status"`
- `yol_haritasi.md`: `"/api/history"`
Notes / assumptions:
- The listed endpoints do not appear in `app_legacy.py` route list.
