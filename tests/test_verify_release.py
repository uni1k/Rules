import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ruleset import generate
from verify_release import audit


class VerifyReleaseTests(unittest.TestCase):
    def test_audit_accepts_base_providers_without_tiered_variants(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            providers = {
                'Reject': [
                    'DOMAIN-SUFFIX,ads.example,REJECT',
                    'IP-CIDR,198.51.100.0/24,REJECT,no-resolve',
                ],
                'LAN': [
                    'DOMAIN,router.local,DIRECT',
                    'IP-CIDR,192.168.0.0/16,DIRECT,no-resolve',
                ],
            }
            for name, rules in providers.items():
                content = '\n'.join(rules) + '\n'
                (root / f'{name}.list').write_text(content, encoding='utf-8')
                (root / f'{name}.yaml').write_text(
                    generate([f'file://{root / f"{name}.list"}'], is_clash=True),
                    encoding='utf-8',
                )

            with patch('verify_release.EXPECTED', set(providers)):
                with patch('verify_release.PRIORITY', ['Reject', 'LAN']):
                    with patch('verify_release.MINIMUM_RULES', {}):
                        manifest = audit(root)

        self.assertEqual(
            manifest['recommended_order'],
            {'providers': ['Reject', 'LAN']},
        )
        self.assertEqual(set(manifest['providers']), {'Reject', 'LAN'})


if __name__ == '__main__':
    unittest.main()
