# -*- coding: utf-8 -*-

import argparse
import ipaddress
import re
import sys
from io import StringIO
from typing import Iterable
from urllib.parse import urlparse

import requests
from ordered_set import OrderedSet
from ruamel.yaml import YAML

ClashRuleTypes = (
    'DOMAIN', 'DOMAIN-SUFFIX', 'DOMAIN-KEYWORD',
    'IP-CIDR', 'IP-CIDR6',
    'SRC-IP-CIDR', 'DST-PORT', 'SRC-PORT',
)

SurgeRuleTypes = (
    'DOMAIN', 'DOMAIN-SUFFIX', 'DOMAIN-KEYWORD',
    'IP-CIDR', 'IP-CIDR6',
    'USER-AGENT', 'URL-REGEX', 'PROCESS-NAME',
    'DEST-PORT', 'SRC-IP', 'IN-PORT', 'PROTOCOL',
)

LogicalRuleTypes = ('AND', 'OR', 'NOT')
URL_SCHEMES = ('http', 'https', 'file')
REQUEST_TIMEOUT = (5, 30)
MAX_RULESET_DEPTH = 16


class RuleError(Exception):
    """Raised when an input rule cannot be safely converted."""


class RuleSet(OrderedSet):

    def __init__(self,
                 is_clash: bool = False,
                 force_no_resolve: bool = False,
                 include_comments: bool = False,
                 strict: bool = False):
        super().__init__()
        self.is_clash = is_clash
        self.force_no_resolve = force_no_resolve
        self.include_comments = include_comments
        self.strict = strict
        self.types = ClashRuleTypes if is_clash else SurgeRuleTypes
        self._active_sources = []

    @staticmethod
    def _is_url(value: str) -> bool:
        parsed = urlparse(value)
        return parsed.scheme in URL_SCHEMES and (
            bool(parsed.path) and (
                parsed.scheme == 'file' or bool(parsed.netloc)
            )
        )

    @staticmethod
    def fetch_lines(*urls):
        for url in urls:
            parsed = urlparse(url)
            if parsed.scheme == 'file':
                if parsed.netloc not in ('', 'localhost') or not parsed.path:
                    raise RuleError(f'unsupported ruleset URL: {url}')
                with open(parsed.path, encoding='utf-8') as source:
                    yield from source
                continue

            if parsed.scheme not in ('http', 'https') or not parsed.netloc:
                raise RuleError(f'unsupported ruleset URL: {url}')

            try:
                with requests.get(url, stream=True, allow_redirects=True,
                                  timeout=REQUEST_TIMEOUT) as response:
                    response.raise_for_status()
                    response.encoding = response.encoding or 'utf-8'
                    yield from response.iter_lines(decode_unicode=True)
            except requests.RequestException as error:
                raise RuleError(f'failed to fetch ruleset {url}: {error}') from error

    @staticmethod
    def _is_domainset_url(url: str) -> bool:
        return urlparse(url).path.startswith('/List/domainset/')

    def _process(self, text: str, domainset: bool = False) -> tuple[str, ...]:
        text = text.strip()
        if not text:
            return ()

        if text.startswith('#'):
            return () if self.is_clash or not self.include_comments else (text,)

        # A hash is part of a valid URL or regular expression unless preceded by
        # whitespace, which is the comment form used by common rule providers.
        text = re.split(r'\s+#', text, maxsplit=1)[0].strip()
        if domainset and ',' not in text:
            if text.startswith('7h1s_rul35et_i5_mad3_by_5ukk4w-'):
                return ()
            if text.startswith('.'):
                return ('DOMAIN-SUFFIX', text[1:].lower())
            return ('DOMAIN', text.lower())

        rule = [item.strip() for item in text.split(',')]
        if not rule or any(not item for item in rule):
            raise RuleError(f'invalid rule: {text}')
        if rule[0] in LogicalRuleTypes:
            return ()
        if len(rule) > 4:
            raise RuleError(f'invalid rule: {text}')
        if len(rule) == 4:
            if rule[-1] != 'no-resolve':
                raise RuleError(f'invalid option: {text}')
            rule.pop(2)
        elif len(rule) == 3 and rule[-1] != 'no-resolve':
            rule.pop()

        if rule[0] in ('DOMAIN', 'DOMAIN-SUFFIX', 'DOMAIN-KEYWORD'):
            rule[1] = rule[1].lower()
        elif rule[0] in ('IP-CIDR', 'IP-CIDR6', 'SRC-IP-CIDR'):
            try:
                rule[1] = str(ipaddress.ip_network(rule[1], strict=False))
            except ValueError as error:
                raise RuleError(f'invalid IP network: {text}') from error

        if rule[0] == 'RULE-SET':
            if len(rule) not in (2, 3) or not self._is_url(rule[1]):
                raise RuleError(f'invalid ruleset reference: {text}')
        elif self._is_url(rule[0]):
            if len(rule) != 1:
                raise RuleError(f'invalid ruleset reference: {text}')
            rule.insert(0, 'RULE-SET')
        elif rule[0] not in self.types:
            if self.strict:
                raise RuleError(f'unsupported rule type: {rule[0]}')
            return ()
        elif len(rule) < 2:
            raise RuleError(f'invalid rule: {text}')

        if (self.force_no_resolve and rule[0] in ('IP-CIDR', 'IP-CIDR6')
                and rule[-1] != 'no-resolve'):
            rule.append('no-resolve')

        return tuple(rule)

    def _operate(self, text: str, operation: str, domainset: bool = False):
        rule = self._process(text, domainset)
        if not rule:
            return
        if rule[0] == 'RULE-SET':
            url = rule[1]
            if url in self._active_sources:
                chain = ' -> '.join((*self._active_sources, url))
                raise RuleError(f'cyclic ruleset reference: {chain}')
            if len(self._active_sources) >= MAX_RULESET_DEPTH:
                raise RuleError(
                    f'ruleset nesting exceeds {MAX_RULESET_DEPTH}: {url}'
                )
            self._active_sources.append(url)
            try:
                for line in self.fetch_lines(url):
                    self._operate(line, operation, self._is_domainset_url(url))
            finally:
                self._active_sources.pop()
            return

        getattr(super(), operation)(','.join(rule))

    def add(self, text: str):
        self._operate(text, 'add')

    def discard(self, text: str):
        self._operate(text, 'discard')


def generate(sources: Iterable[str],
             exclusions: Iterable[str] = (),
             is_clash: bool = False,
             force_no_resolve: bool = False,
             include_comments: bool = False,
             strict: bool = False) -> str:
    rules = RuleSet(is_clash, force_no_resolve, include_comments, strict)

    for source in sources:
        rules.add(source)
    for exclusion in exclusions:
        rules.discard(exclusion)

    if is_clash:
        with StringIO() as stream:
            yaml = YAML(typ='safe', pure=True)
            yaml.default_flow_style = False
            yaml.indent(mapping=2, sequence=4, offset=2)
            yaml.dump({'payload': list(rules)}, stream)
            return stream.getvalue()

    return '\n'.join(rules) + ('\n' if rules else '')


def main():
    parser = argparse.ArgumentParser(description='Ruleset Generator')
    parser.add_argument('-s', '--source', action='append', required=True,
                        help='rule or URL to include; repeat for multiple sources')
    parser.add_argument('-e', '--exclude', action='append', default=[],
                        help='rule or URL to exclude; repeat for multiple exclusions')
    parser.add_argument('-c', '--is-clash', action='store_true',
                        help='output Clash YAML instead of Surge rules')
    parser.add_argument('--force-no-resolve', action='store_true',
                        help='append no-resolve to IP-CIDR and IP-CIDR6 rules')
    parser.add_argument('--include-comments', action='store_true',
                        help='preserve full-line comments in Surge output')
    parser.add_argument('--strict', action='store_true',
                        help='fail instead of ignoring unsupported rule types')
    args = parser.parse_args()

    sys.stdout.write(generate(args.source, args.exclude, args.is_clash,
                              args.force_no_resolve, args.include_comments,
                              args.strict))


if __name__ == '__main__':
    main()
