# Rules

Generate deduplicated Surge rule providers and Clash rule-provider YAML from
inline rules, local files, or remote HTTP(S) rule lists. The scheduled GitHub
Actions workflow publishes generated files to the `release` branch.

## Usage

```bash
python -m pip install -r requirements.txt

# Surge provider rules
python ruleset.py \
  --source 'DOMAIN-SUFFIX,example.com,Proxy' \
  --source 'https://example.com/rules.list' > rules.list

# Clash rule-provider YAML
python ruleset.py --is-clash --source 'file:///absolute/path/rules.list' > rules.yaml
```

Use `--exclude` to remove rules after merging, `--force-no-resolve` for IP CIDR
rules, and `--include-comments` to retain full-line comments in Surge output.
`--strict` turns unsupported rule types into errors; without it they are ignored
for compatibility with mixed upstream rule lists.

Only `http`, `https`, and `file` rule-set URLs are supported. Remote downloads
have a 5-second connect timeout and a 30-second read timeout. Cyclic nested
`RULE-SET` references fail with a descriptive error instead of recursing
indefinitely.

Sukka `List/domainset` sources are also accepted: `.example.com` entries are
converted to `DOMAIN-SUFFIX,example.com`, while exact host entries become
`DOMAIN` rules.

## Release artifacts

Each release publishes one Surge provider and one Clash provider per ruleset:

- `Surge/<Name>.list`
- `Clash/<Name>.yaml`

`Surge/manifest.json` records the recommended provider order plus the duplicate
and overlap audit for the published base providers.

## Development

```bash
python -m unittest discover -s tests -v
```

The release workflow installs exact versions from `requirements.lock`. It still
deliberately consumes third-party rule lists, so pin each upstream URL to a
reviewed commit SHA before using this repository where reproducible rule output
is required.
