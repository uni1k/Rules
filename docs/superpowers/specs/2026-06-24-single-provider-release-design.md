# Single Provider Release Design

## Goal

Remove published `*Domain.list` and `*IP.list` tiered providers while keeping one Surge `.list` and one Clash `.yaml` per provider.

## Scope

This change only affects release artifacts, release verification, and documentation.

- Keep `ruleset.py` source parsing and Clash YAML generation behavior unchanged.
- Stop generating split provider files in the GitHub Actions release workflow.
- Stop requiring split provider files in release verification.
- Update repository documentation to describe single-provider release artifacts.
- Remove obsolete split-provider tests and release-path usage.

## Design

### Release artifacts

Each logical provider publishes exactly two files:

- `Name.list`
- `Name.yaml`

`Name.yaml` continues to be generated from `Name.list` via `python ruleset.py -c -s "file://..."`.

### Verification

`verify_release.py` should treat `*.list` files as the canonical provider set.

It should continue to verify:

- expected provider names
- minimum rule counts
- `.list` and `.yaml` consistency
- duplicate and coverage statistics

It should no longer:

- infer `NameDomain` / `NameIP`
- require split provider files
- emit split-only recommended order fields

`recommended_order` should become a single ordered provider list.

### Workflow

The release workflow should:

- generate base `.list` files
- convert each base `.list` into a `.yaml`
- verify outputs
- publish only those `.list` / `.yaml` artifacts

### Documentation

README should describe the single-provider model and remove tiered-provider guidance.

## Risks

- Existing consumers depending on `*Domain.list` / `*IP.list` will lose those files.
- Manifest readers expecting the old `recommended_order.domain_and_application` / `recommended_order.ip` shape will need updating.

## Success Criteria

- CI no longer calls `split_providers.py`.
- Release verification passes with only base provider `.list` files present.
- Test suite passes after removing obsolete split-provider assumptions.
