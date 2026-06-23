import tempfile
import unittest
from pathlib import Path

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


if __name__ == '__main__':
    unittest.main()
