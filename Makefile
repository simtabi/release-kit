.DEFAULT_GOAL := help
SHELL := /bin/bash

# Python tooling. `uv` is preferred but vanilla pip works.
PIP ?= pip
PYTHON ?= python3

.PHONY: help install lint test cov build dry-run publish bootstrap-repo rotate-tokens docs clean

help:
	@echo "make targets:"
	@echo "  install         Install editable + dev + all platform extras"
	@echo "  lint            ruff check + mypy"
	@echo "  test            pytest with coverage gate"
	@echo "  cov             open htmlcov in browser"
	@echo "  build           build sdist + wheel"
	@echo "  dry-run         release-kit publish (no --apply)"
	@echo "  publish         release-kit publish --apply  (prompts confirmation)"
	@echo "  bootstrap-repo  release-kit bootstrap-repo --apply (prompts)"
	@echo "  rotate-tokens   release-kit rotate-tokens (interactive)"
	@echo "  docs            verify docs ToC + cross-links"
	@echo "  clean           remove build + cache artefacts"

install:
	$(PIP) install -e '.[dev,all]'
	@command -v pre-commit >/dev/null && pre-commit install || echo "pre-commit not on PATH (optional)"

lint:
	$(PYTHON) -m ruff check src tests
	$(PYTHON) -m mypy src/release_kit

test:
	$(PYTHON) -m pytest

cov: test
	@if [ -d htmlcov ]; then \
		case "$$(uname -s)" in \
			Darwin*) open htmlcov/index.html ;; \
			Linux*)  xdg-open htmlcov/index.html ;; \
			*)       echo "Open htmlcov/index.html manually" ;; \
		esac; \
	else \
		echo "Run 'make test' first"; \
	fi

build:
	$(PYTHON) -m build

dry-run:
	release-kit publish

publish:
	@read -p "About to publish for real. Continue? [y/N] " ans; \
	  test "$$ans" = "y" || { echo "Aborted."; exit 1; }
	release-kit publish --apply

bootstrap-repo:
	@read -p "About to apply topics + branch protection. Continue? [y/N] " ans; \
	  test "$$ans" = "y" || { echo "Aborted."; exit 1; }
	release-kit bootstrap-repo --apply

rotate-tokens:
	release-kit rotate-tokens

docs:
	@echo "Validating docs ToC + cross-links..."
	@$(PYTHON) - <<'PY'
import pathlib, re, sys
playbook = pathlib.Path("docs/playbook")
toc = (playbook / "README.md").read_text()
disk = sorted(p.relative_to(playbook).as_posix() for p in playbook.rglob("*.md") if p.name != "README.md")
linked = sorted(set(re.findall(r"\]\(([^)#]+\.md)\)", toc)))
missing = [p for p in disk if p not in linked]
extra   = [p for p in linked if p not in disk]
if missing:
    print(f"ToC missing entries for: {missing}", file=sys.stderr)
if extra:
    print(f"ToC references files not on disk: {extra}", file=sys.stderr)
sys.exit(0 if not (missing or extra) else 1)
PY

clean:
	rm -rf build/ dist/ src/*.egg-info
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage coverage.xml
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
