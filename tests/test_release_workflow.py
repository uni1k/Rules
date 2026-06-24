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
        self.assertIn(
            'blackmatrix7/ios_rule_script/master/rule/Surge/Copilot/Copilot.list',
            body,
        )
        self.assertIn('https://ruleset.skk.moe/List/non_ip/ai.conf', body)
        self.assertIn(
            'https://raw.githubusercontent.com/xjasonlyu/Rules/release/Surge/AI.list',
            body,
        )


if __name__ == '__main__':
    unittest.main()
