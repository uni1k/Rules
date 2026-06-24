# Direct Provider Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract non-LAN direct rules from `LAN` into a dedicated `Direct` provider and publish `Direct.list` / `Direct.yaml`.

**Architecture:** Keep rule generation logic unchanged and modify only release configuration, release verification, and tests. `LAN` keeps only LAN rules; `Direct` aggregates generic direct routes from Sukka plus the BlackMatrix7 Direct provider.

**Tech Stack:** Python, unittest, GitHub Actions YAML

## Global Constraints

- Do not change `ruleset.py` parsing behavior.
- `LAN` must no longer include `https://ruleset.skk.moe/List/non_ip/direct.conf`.
- `Direct` must include Sukka direct plus BlackMatrix7 Direct list.
- Tests must fail before implementation changes.

---

### Task 1: Add tests for `Direct` provider workflow and verification

**Files:**
- Modify: `tests/test_release_workflow.py`
- Modify: `tests/test_verify_release.py`

**Interfaces:**
- Consumes: workflow `Generate LAN Rule` / `Generate Direct Rule`, `verify_release.audit(directory: Path) -> dict`
- Produces: failing expectations for `Direct`

- [ ] Write failing tests
- [ ] Run focused tests and confirm failure
- [ ] Implement minimal production changes
- [ ] Re-run focused tests to green

### Task 2: Update workflow and release verification

**Files:**
- Modify: `.github/workflows/release.yml`
- Modify: `verify_release.py`

**Interfaces:**
- Consumes: base release provider names
- Produces: `Direct` in generated provider set and manifest order

- [ ] Split LAN and Direct generation in workflow
- [ ] Add `Direct` to `EXPECTED` and `PRIORITY`
- [ ] Re-run targeted tests

### Task 3: Update documentation and run full verification

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: release artifact documentation
- Produces: docs aligned with `Direct`

- [ ] Update provider list/docs
- [ ] Run `python -m unittest discover -s tests -v`
- [ ] Commit
