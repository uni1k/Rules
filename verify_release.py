import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from ruamel.yaml import YAML
from ruleset import RuleSet

EXPECTED = {
    'LAN', 'AI', 'Telegram',
    'Global', 'GlobalMedia', 'Mainland', 'MainlandMedia',
    'Game', 'Apple', 'Microsoft', 'Google', 'Reject',
}

# Earlier entries have higher matching priority when consumers combine providers.
PRIORITY = [
    'Reject', 'LAN', 'MainlandMedia', 'GlobalMedia',
    'Apple', 'Microsoft', 'AI', 'Telegram',
    'Mainland', 'Google', 'Game', 'Global',
]
CLASH_TYPES = {
    'DOMAIN', 'DOMAIN-SUFFIX', 'DOMAIN-KEYWORD', 'IP-CIDR', 'IP-CIDR6',
    'SRC-IP-CIDR', 'DST-PORT', 'SRC-PORT',
}
MINIMUM_RULES = {'Reject': 50_000, 'China': 1_000, 'Global': 1_000}


def read_lines(path: Path) -> list[str]:
    lines = path.read_text(encoding='utf-8').splitlines()
    if not lines:
        raise ValueError(f'empty provider: {path.name}')
    return lines


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(directory: Path) -> dict:
    all_lists = {path.stem: path for path in directory.glob('*.list')}
    missing = EXPECTED - all_lists.keys()
    unexpected = all_lists.keys() - EXPECTED
    if missing or unexpected:
        raise ValueError(f'provider set mismatch: missing={sorted(missing)} '
                         f'unexpected={sorted(unexpected)}')

    base_lines = {name: read_lines(path) for name, path in all_lists.items()}

    yaml = YAML(typ='safe')
    providers, ownership = {}, defaultdict(list)
    for name, path in sorted(all_lists.items()):
        lines = read_lines(path)
        if len(lines) < MINIMUM_RULES.get(name, 1):
            raise ValueError(f'provider too small: {name} has {len(lines)} rules')
        target = directory / f'{name}.yaml'
        if not target.exists():
            raise ValueError(f'missing Clash provider: {target.name}')
        with target.open(encoding='utf-8') as stream:
            document = yaml.load(stream)
        payload = document.get('payload') if isinstance(document, dict) else None
        if not isinstance(payload, list) or not payload:
            raise ValueError(f'invalid Clash provider: {target.name}')
        normalized = RuleSet()
        for line in lines:
            normalized.add(line)
        expected = [line for line in normalized
                    if line.split(',', 1)[0] in CLASH_TYPES]
        if payload != expected:
            raise ValueError(f'unapproved Surge/Clash difference: {name}')
        types = Counter(line.split(',', 1)[0] for line in lines)
        providers[name] = {'rules': len(lines), 'clash_rules': len(payload),
                           'types': dict(sorted(types.items())),
                           'sha256': checksum(path)}
    for name, lines in base_lines.items():
        for line in lines:
            ownership[line].append(name)

    duplicates = {rule: names for rule, names in ownership.items() if len(names) > 1}
    suffix_owners = defaultdict(list)
    domain_owners = []
    for rule, names in ownership.items():
        kind, value, *_ = rule.split(',')
        if kind == 'DOMAIN-SUFFIX':
            suffix_owners[value].extend(names)
        elif kind == 'DOMAIN':
            domain_owners.append((value, names))
    coverages = []
    coverage_count = 0
    for domain, names in domain_owners:
        labels = domain.split('.')
        for index in range(1, len(labels)):
            suffix = '.'.join(labels[index:])
            owners = set(suffix_owners.get(suffix, ())) - set(names)
            if owners:
                coverage_count += 1
                if len(coverages) < 100:
                    coverages.append({'domain': domain, 'suffix': suffix,
                                      'providers': sorted(set(names) | owners,
                                                          key=PRIORITY.index)})
                break
    return {
        'provider_priority': PRIORITY,
        'recommended_order': {
            'providers': [name for name in PRIORITY if name in all_lists],
        },
        'providers': providers,
        'cross_provider_exact_duplicates': len(duplicates),
        'duplicate_examples': [
            {'rule': rule, 'providers': sorted(names, key=PRIORITY.index)}
            for rule, names in list(sorted(duplicates.items()))[:100]
        ],
        'cross_provider_domain_coverages': coverage_count,
        'domain_coverage_examples': coverages,
    }


def main():
    parser = argparse.ArgumentParser(description='Verify generated rule providers')
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--workflow', type=Path)
    args = parser.parse_args()
    manifest = audit(args.directory)
    if args.workflow:
        workflow = args.workflow.read_text(encoding='utf-8')
        manifest['workflow_sha256'] = checksum(args.workflow)
        manifest['configured_sources'] = sorted(set(re.findall(
            r'--source\s+["\']?([^\s"\'\\]+)', workflow)))
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n',
                             encoding='utf-8')
    print(f"verified {len(manifest['providers'])} providers; "
          f"cross-provider exact duplicates: {manifest['cross_provider_exact_duplicates']}")


if __name__ == '__main__':
    main()
