import unittest
from qubell.api.private.testing import norm


class NormNamesTests(unittest.TestCase):

    def test_same_when_no_special_symbols(self):
        assert norm('default') == 'default'

    def test_preserve_upper_case(self):
        assert norm('privateHA') == 'privateHA'

    def test_underscore_is_accepted(self):
        assert norm('some_name') == 'some_name'

    def test_specials_replaced_by_underscore(self):
        assert norm('a-b c%d=e') == 'a_b_c_d_e'
