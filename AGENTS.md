# Repository Guidelines

## Project Structure & Module Organization
- Root directory contains standalone Python scripts for sensor and relay experiments (e.g., `sensors_test.py`, `moisture_log.py`, `lcd_test.py`).
- `sera_panel/` holds the main control panel app (`app.py`), hardware test scripts (`*.sh`), and runtime configuration (`config.json`).
- `sera_projesi/` contains an alternate or earlier application entry point (`app.py`).
- `sera-venv/` is a local Python virtual environment; keep project dependencies installed there.

## Build, Test, and Development Commands
- `python3 sera_panel/app.py` runs the primary panel application.
- `python3 sera_projesi/app.py` runs the alternate application entry point.
- `python3 sensors_test.py` or `python3 dht_test.py` runs individual hardware test scripts.
- `bash sera_panel/relay_click_test.sh` runs relay click tests; check `.log` files in `sera_panel/` for output.

## Coding Style & Naming Conventions
- Use 4-space indentation and PEP 8-style Python formatting.
- Prefer `snake_case` for functions/variables and `UPPER_SNAKE_CASE` for constants.
- Keep module filenames descriptive and in `snake_case` (e.g., `moisture_raw.py`).
- Store runtime settings in `sera_panel/config.json` rather than hard-coding values.

## Testing Guidelines
- Tests are hardware-driven scripts named `*_test.py` and `*_test.sh`.
- Run tests manually with the target hardware connected; there is no automated test runner configured.
- Add new tests following the existing naming pattern and keep logs in `sera_panel/` when appropriate.

## Update Log Guidelines
- When pushing to GitHub, also add a user-friendly entry to `config/updates.json`.
- Each entry should explain what changed and why it matters for the user (not technical details).

## Commit & Pull Request Guidelines
- No Git history is present in this workspace; use clear, imperative commit messages (e.g., "Add relay polarity check").
- PRs should include a short description, how you validated (commands run), and any hardware assumptions.

## Security & Configuration Tips
- Avoid committing secrets or network credentials; keep sensitive values out of `config.json`.
- Be explicit about GPIO/I2C pin usage in code comments when altering hardware behavior.
