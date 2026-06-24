import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ruleset import generate
from verify_release import EXPECTED, PRIORITY, audit


def _sample_rule(name: str) -> str:
    samples = {
        'Reject': 'DOMAIN-SUFFIX,reject.example,REJECT',
        'LAN': 'IP-CIDR,192.168.0.0/16,DIRECT,no-resolve',
        'Direct': 'DOMAIN-SUFFIX,direct.example,DIRECT',
        'AI': 'DOMAIN-SUFFIX,ai.example,Proxy',
        'Telegram': 'DOMAIN-SUFFIX,telegram.example,Proxy',
        'Global': 'DOMAIN-SUFFIX,global.example,Proxy',
        'GlobalMedia': 'DOMAIN-SUFFIX,globalmedia.example,Proxy',
        'Mainland': 'DOMAIN-SUFFIX,mainland.example,DIRECT',
        'MainlandMedia': 'DOMAIN-SUFFIX,mainlandmedia.example,DIRECT',
        'Game': 'DOMAIN-SUFFIX,game.example,Proxy',
        'GitHub': 'DOMAIN-SUFFIX,github.example,Proxy',
        'Apple': 'DOMAIN-SUFFIX,apple.example,DIRECT',
        'Microsoft': 'DOMAIN-SUFFIX,microsoft.example,DIRECT',
        'Google': 'DOMAIN-SUFFIX,google.example,Proxy',
    }
    return samples[name]


class VerifyReleaseTests(unittest.TestCase):
    def test_audit_accepts_official_provider_set(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in EXPECTED:
                content = _sample_rule(name) + '\n'
                (root / f'{name}.list').write_text(content, encoding='utf-8')
                (root / f'{name}.yaml').write_text(
                    generate([f'file://{root / f"{name}.list"}'], is_clash=True),
                    encoding='utf-8',
                )

            with patch('verify_release.MINIMUM_RULES', {}):
                manifest = audit(root)

        self.assertEqual(
            manifest['recommended_order'],
            {'providers': PRIORITY},
        )
        self.assertEqual(set(manifest['providers']), EXPECTED)


if __name__ == '__main__':
    unittest.main()
