.PHONY: help venv install run run-sim test doctor

PY ?= python3
VENV ?= venv

PYRUN := $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/python,$(PY))
PIPRUN := $(if $(wildcard $(VENV)/bin/pip),$(VENV)/bin/pip,pip3)

help:
	@echo "Targets:"
	@echo "  make venv      - Create venv ($(VENV))"
	@echo "  make install   - Install requirements into venv"
	@echo "  make run       - Run panel (real hardware defaults)"
	@echo "  make run-sim   - Run panel in SIMULATION_MODE"
	@echo "  make test      - Run pytest in SIMULATION_MODE"
	@echo "  make doctor    - Validate config + schemas"

venv:
	$(PY) -m venv $(VENV)

install: venv
	$(PIPRUN) install -r requirements.txt

run:
	$(PYRUN) app.py

run-sim:
	SIMULATION_MODE=1 $(PYRUN) app.py

test:
	SIMULATION_MODE=1 DISABLE_BACKGROUND_LOOPS=1 $(PYRUN) -m pytest -q tests

doctor:
	$(PYRUN) scripts/doctor.py
