import unittest
from unittest.mock import patch
from evaluate_after_go import authorize


class AuthorizationTests(unittest.TestCase):
    def test_wrong_or_near_GO_never_reads_market(self):
        sha = 'a' * 64
        for command in ['', 'GO', 'GO RUN MISSING_MINUTE_V01 ' + sha + ' ',
                        'GO RUN MISSING_MINUTE_V01 ' + 'b' * 64]:
            with patch('evaluate_after_go.digest', return_value=sha), \
                 patch('evaluate_after_go.market_from_cache') as cache:
                with self.assertRaises(ValueError):
                    authorize(command)
                cache.assert_not_called()


if __name__ == '__main__':
    unittest.main()
