import argparse
from pathlib import Path

DOMAIN_TYPES = {'DOMAIN', 'DOMAIN-SUFFIX', 'DOMAIN-KEYWORD', 'URL-REGEX',
                'PROCESS-NAME', 'USER-AGENT'}
IP_TYPES = {'IP-CIDR', 'IP-CIDR6', 'SRC-IP-CIDR'}


def split_provider(path: Path) -> tuple[list[str], list[str]]:
    domain, ip, unsupported = [], [], []
    for line in path.read_text(encoding='utf-8').splitlines():
        rule_type = line.split(',', 1)[0]
        if rule_type in DOMAIN_TYPES:
            domain.append(line)
        elif rule_type in IP_TYPES:
            ip.append(line)
        else:
            unsupported.append(rule_type)
    if unsupported:
        raise ValueError(f'{path.name}: unclassified rule types: '
                         f'{", ".join(sorted(set(unsupported)))}')
    return domain, ip


def split_directory(directory: Path) -> dict[str, dict[str, int]]:
    result = {}
    for path in sorted(directory.glob('*.list')):
        if path.stem.endswith(('Domain', 'IP')):
            continue
        domain, ip = split_provider(path)
        stats = {}
        if domain:
            target = path.with_name(f'{path.stem}Domain.list')
            target.write_text('\n'.join(domain) + '\n', encoding='utf-8')
            stats['domain'] = len(domain)
        if ip:
            target = path.with_name(f'{path.stem}IP.list')
            target.write_text('\n'.join(ip) + '\n', encoding='utf-8')
            stats['ip'] = len(ip)
        result[path.stem] = stats
    return result


def main():
    parser = argparse.ArgumentParser(description='Split mixed rule providers')
    parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    summary = split_directory(args.directory)
    print(f'split {len(summary)} providers into '
          f'{sum(len(kinds) for kinds in summary.values())} tiered providers')


if __name__ == '__main__':
    main()
