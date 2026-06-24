import re
import unittest
from pathlib import Path


class ReleaseWorkflowTests(unittest.TestCase):
    def test_ai_rule_sources_include_aggregated_providers(self):
        workflow = Path('.github/workflows/release.yml').read_text(
            encoding='utf-8'
        )
        match = re.search(
            r'- name: Generate AI Rule\n        run: \|\n(?P<body>(?: {10}.*\n)+)',
            workflow,
        )
        self.assertIsNotNone(match)
        body = match.group('body')
        self.assertIn('https://ruleset.skk.moe/List/non_ip/ai.conf', body)
        self.assertIn(
            'https://raw.githubusercontent.com/Coldvvater/Mononoke/refs/heads/master/Surge/Rules/AI.list',
            body,
        )

    def test_lan_and_direct_rule_sources_are_split(self):
        workflow = Path('.github/workflows/release.yml').read_text(
            encoding='utf-8'
        )
        lan_match = re.search(
            r'- name: Generate LAN Rule\n        run: \|\n(?P<body>(?: {10}.*\n)+)',
            workflow,
        )
        self.assertIsNotNone(lan_match)
        lan_body = lan_match.group('body')
        self.assertIn('https://ruleset.skk.moe/List/non_ip/lan.conf', lan_body)
        self.assertIn('https://ruleset.skk.moe/List/ip/lan.conf', lan_body)
        self.assertNotIn('https://ruleset.skk.moe/List/non_ip/direct.conf', lan_body)

        direct_match = re.search(
            r'- name: Generate Direct Rule\n        run: \|\n(?P<body>(?: {10}.*\n)+)',
            workflow,
        )
        self.assertIsNotNone(direct_match)
        direct_body = direct_match.group('body')
        self.assertIn('https://ruleset.skk.moe/List/non_ip/direct.conf', direct_body)
        self.assertIn(
            'https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/refs/heads/master/rule/Surge/Direct/Direct.list',
            direct_body,
        )

    def test_github_rule_is_generated(self):
        workflow = Path('.github/workflows/release.yml').read_text(
            encoding='utf-8'
        )
        match = re.search(
            r'- name: Generate GitHub Rule\n        run: \|\n(?P<body>(?: {10}.*\n)+)',
            workflow,
        )
        self.assertIsNotNone(match)
        body = match.group('body')
        self.assertIn(
            'https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/refs/heads/master/rule/Surge/GitHub/GitHub.list',
            body,
        )


if __name__ == '__main__':
    unittest.main()
