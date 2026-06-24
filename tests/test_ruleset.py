import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests
from ruamel.yaml import YAML

from ruleset import (MAX_RULESET_DEPTH, REQUEST_RETRIES, REQUEST_TIMEOUT,
                     RuleError, RuleSet, generate)


class RuleSetTests(unittest.TestCase):
    def test_generate_deduplicates_excludes_and_ends_with_newline(self):
        result = generate(
            ['DOMAIN,example.com,Proxy', 'IP-CIDR,1.1.1.0/24,Proxy',
             'DOMAIN,example.com,DIRECT'],
            ['DOMAIN,example.com,DIRECT'],
            force_no_resolve=True,
        )
        self.assertEqual(result, 'IP-CIDR,1.1.1.0/24,no-resolve\n')

    def test_url_regex_hash_is_not_treated_as_comment(self):
        self.assertEqual(
            generate(['URL-REGEX,^https://example.com/page#fragment,Proxy']),
            'URL-REGEX,^https://example.com/page#fragment\n',
        )

    def test_domains_and_cidrs_are_canonicalized(self):
        self.assertEqual(
            generate(['DOMAIN-SUFFIX,Example.COM,Proxy',
                      'DOMAIN-SUFFIX,example.com,DIRECT']),
            'DOMAIN-SUFFIX,example.com\n',
        )
        self.assertEqual(
            generate(['IP-CIDR,203.0.113.1/24,Proxy']),
            'IP-CIDR,203.0.113.0/24\n',
        )

    def test_domainset_entries_convert_to_domain_rules(self):
        rules = RuleSet()
        self.assertEqual(
            rules._process('.example.com', domainset=True),
            ('DOMAIN-SUFFIX', 'example.com'),
        )
        self.assertEqual(
            rules._process('api.example.com', domainset=True),
            ('DOMAIN', 'api.example.com'),
        )
        self.assertEqual(
            rules._process('7h1s_rul35et_i5_mad3_by_5ukk4w-ruleset.skk.moe',
                           domainset=True),
            (),
        )

    def test_invalid_ruleset_reference_is_reported(self):
        with self.assertRaisesRegex(RuleError, 'invalid ruleset reference'):
            generate(['RULE-SET'])

    def test_strict_mode_rejects_unsupported_rules(self):
        with self.assertRaisesRegex(RuleError, 'unsupported rule type: MATCH'):
            generate(['MATCH,Proxy'], strict=True)

    def test_cycle_is_detected(self):
        sources = {
            'https://example.test/a': ['RULE-SET,https://example.test/b'],
            'https://example.test/b': ['RULE-SET,https://example.test/a'],
        }

        with patch.object(RuleSet, 'fetch_lines', side_effect=lambda url: sources[url]):
            with self.assertRaisesRegex(RuleError, 'cyclic ruleset reference'):
                generate(['https://example.test/a'])

    def test_nesting_depth_is_limited(self):
        urls = [f'https://example.test/{index}'
                for index in range(MAX_RULESET_DEPTH + 1)]
        sources = {
            url: [f'RULE-SET,{urls[index + 1]}']
            for index, url in enumerate(urls[:-1])
        }
        sources[urls[-1]] = ['DOMAIN,example.com,Proxy']

        with patch.object(RuleSet, 'fetch_lines', side_effect=lambda url: sources[url]):
            with self.assertRaisesRegex(RuleError, 'ruleset nesting exceeds'):
                generate([urls[0]])

    def test_http_fetch_uses_timeout_and_utf8_fallback(self):
        class Response:
            encoding = None

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def raise_for_status(self):
                pass

            def iter_lines(self, decode_unicode):
                self.decode_unicode = decode_unicode
                return iter(['DOMAIN,example.com,Proxy'])

        response = Response()
        with patch('ruleset.requests.get', return_value=response) as request:
            self.assertEqual(list(RuleSet.fetch_lines('https://example.test/rules')),
                             ['DOMAIN,example.com,Proxy'])

        request.assert_called_once_with('https://example.test/rules', stream=True,
                                        allow_redirects=True, timeout=REQUEST_TIMEOUT)
        self.assertEqual(response.encoding, 'utf-8')
        self.assertTrue(response.decode_unicode)

    def test_http_fetch_retries_on_failure(self):
        fail_response = MagicMock()
        fail_response.__enter__ = MagicMock(return_value=fail_response)
        fail_response.__exit__ = MagicMock(return_value=False)
        fail_response.raise_for_status.side_effect = requests.RequestException(
            'connection reset')

        ok_response = MagicMock()
        ok_response.__enter__ = MagicMock(return_value=ok_response)
        ok_response.__exit__ = MagicMock(return_value=False)
        ok_response.raise_for_status.return_value = None
        ok_response.encoding = 'utf-8'
        ok_response.iter_lines.return_value = iter(['DOMAIN,ok.com,Proxy'])

        with patch('ruleset.requests.get',
                   side_effect=[fail_response, ok_response]):
            with patch('ruleset.time.sleep'):
                result = list(RuleSet.fetch_lines('https://example.test/rules'))
        self.assertEqual(result, ['DOMAIN,ok.com,Proxy'])

    def test_clash_yaml_includes_type_and_behavior(self):
        output = generate(['DOMAIN,example.com,Proxy',
                           'DOMAIN-SUFFIX,example.org,Proxy'],
                          is_clash=True)
        yaml = YAML(typ='safe')
        doc = yaml.load(output)
        self.assertEqual(doc['type'], 'file')
        self.assertEqual(doc['behavior'], 'domain')
        self.assertIn('DOMAIN,example.com', doc['payload'])

    def test_clash_yaml_behavior_ipcidr(self):
        output = generate(['IP-CIDR,1.1.1.0/24,Proxy',
                           'IP-CIDR6,2001:db8::/32,Proxy'],
                          is_clash=True)
        yaml = YAML(typ='safe')
        doc = yaml.load(output)
        self.assertEqual(doc['behavior'], 'ipcidr')

    def test_exclude_file_removes_rules(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.list',
                                         delete=False) as f:
            f.write('DOMAIN,remove.me,Proxy\nDOMAIN-SUFFIX,drop.this,Proxy\n')
            exclude_path = f.name
        result = generate(
            ['DOMAIN,keep.me,Proxy', 'DOMAIN,remove.me,Proxy',
             'DOMAIN-SUFFIX,drop.this,Proxy'],
            exclusions=[f'file://{exclude_path}'],
        )
        self.assertEqual(result, 'DOMAIN,keep.me\n')


if __name__ == '__main__':
    unittest.main()
