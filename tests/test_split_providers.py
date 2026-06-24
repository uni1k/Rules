import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from split_providers import split_directory


class SplitProviderTests(unittest.TestCase):
    def test_split_preserves_order_and_types(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Example.list').write_text(
                'DOMAIN,b.example\nIP-CIDR,203.0.113.0/24\n'
                'DOMAIN-SUFFIX,example\nIP-CIDR6,2001:db8::/32\n',
                encoding='utf-8')
            summary = split_directory(root)
            self.assertEqual(summary, {'Example': {'domain': 2, 'ip': 2}})
            self.assertEqual((root / 'ExampleDomain.list').read_text(),
                             'DOMAIN,b.example\nDOMAIN-SUFFIX,example\n')
            self.assertEqual((root / 'ExampleIP.list').read_text(),
                             'IP-CIDR,203.0.113.0/24\nIP-CIDR6,2001:db8::/32\n')

    def test_unsupported_types_warn_and_skip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Mixed.list').write_text(
                'DOMAIN,ok.example\nDST-PORT,443\nSRC-PORT,12345\n'
                'IP-CIDR,1.1.1.0/24\n',
                encoding='utf-8')
            stderr = StringIO()
            with patch('split_providers.sys.stderr', stderr):
                summary = split_directory(root)
            self.assertEqual(summary, {'Mixed': {'domain': 1, 'ip': 1}})
            self.assertIn('DST-PORT', stderr.getvalue())
            self.assertIn('SRC-PORT', stderr.getvalue())


if __name__ == '__main__':
    unittest.main()
