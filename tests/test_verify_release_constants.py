import unittest

from verify_release import EXPECTED, PRIORITY


class VerifyReleaseConstantsTests(unittest.TestCase):
    def test_expected_contains_direct_and_github(self):
        self.assertIn('Direct', EXPECTED)
        self.assertIn('GitHub', EXPECTED)

    def test_priority_contains_direct_and_github(self):
        self.assertIn('Direct', PRIORITY)
        self.assertIn('GitHub', PRIORITY)

    def test_priority_orders_direct_after_lan(self):
        self.assertGreater(PRIORITY.index('Direct'), PRIORITY.index('LAN'))

    def test_priority_orders_github_between_google_and_game(self):
        self.assertGreater(PRIORITY.index('GitHub'), PRIORITY.index('Google'))
        self.assertLess(PRIORITY.index('GitHub'), PRIORITY.index('Game'))


if __name__ == '__main__':
    unittest.main()
