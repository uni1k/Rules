# Single Provider Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove tiered release providers and publish one `.list` plus one `.yaml` per logical provider.

**Architecture:** Keep rule generation unchanged and simplify the release pipeline around base provider files only. Verification remains the source of truth for release integrity, but it now validates a single provider set and emits a single recommended order list.

**Tech Stack:** Python, unittest, GitHub Actions YAML

## Global Constraints

- Do not change `ruleset.py` core parsing or YAML generation behavior.
- Release artifacts must remain one `.list` and one `.yaml` per expected provider.
- Tests must be written first for verification behavior changes.
- Remove split-provider release-path usage rather than leaving dead workflow references.

---

### Task 1: Update verification to the single-provider model

**Files:**
- Create: `tests/test_verify_release.py`
- Modify: `verify_release.py`

**Interfaces:**
- Consumes: `verify_release.audit(directory: Path) -> dict`
- Produces: manifest shape with `recommended_order["providers"]`

- [ ] **Step 1: Write the failing test**

```python
def test_audit_accepts_base_providers_without_tiered_variants():
    manifest = audit(root)
    assert manifest['recommended_order']['providers'] == ['Reject', ...]
    assert 'LAN' in manifest['providers']
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_verify_release -v`
Expected: FAIL because `audit()` still requires `*Domain` / `*IP` files and emits the old manifest shape.

- [ ] **Step 3: Write minimal implementation**

```python
all_lists = {path.stem: path for path in directory.glob('*.list')}
missing = EXPECTED - all_lists.keys()
unexpected = all_lists.keys() - EXPECTED
...
'recommended_order': {'providers': [name for name in PRIORITY if name in all_lists]}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_verify_release -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_verify_release.py verify_release.py
git commit -m "refactor: verify single-provider releases"
```

### Task 2: Remove split-provider release workflow usage

**Files:**
- Modify: `.github/workflows/release.yml`

**Interfaces:**
- Consumes: base `*.list` files produced earlier in workflow
- Produces: `*.yaml` files generated directly from base providers

- [ ] **Step 1: Write the failing test**

No dedicated automated test. Use repository verification by keeping Task 1 tests green and inspecting workflow diff.

- [ ] **Step 2: Apply minimal workflow change**

```yaml
      - name: Convert Clash Rules
        run: |
          for rule in *.list
          do
            python ruleset.py -c -s "file://$PWD/$rule" > "${rule%.*}.yaml"
          done
```

- [ ] **Step 3: Run tests**

Run: `python -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "build: stop generating tiered providers"
```

### Task 3: Remove obsolete split-provider docs and tests

**Files:**
- Modify: `README.md`
- Delete: `tests/test_split_providers.py`
- Optional Delete: `split_providers.py`

**Interfaces:**
- Consumes: current tiered-provider documentation
- Produces: docs and tests aligned with single-provider releases

- [ ] **Step 1: Remove obsolete references**

Delete tiered-provider README guidance and split-provider test coverage that no longer reflects supported behavior.

- [ ] **Step 2: Run full tests**

Run: `python -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add README.md tests/test_split_providers.py split_providers.py
git commit -m "docs: remove tiered provider release guidance"
```
