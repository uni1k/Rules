import unittest
from unittest.mock import patch

from ruleset import (MAX_RULESET_DEPTH, REQUEST_TIMEOUT, RuleError, RuleSet,
                     generate)


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


if __name__ == '__main__':
    unittest.main()
