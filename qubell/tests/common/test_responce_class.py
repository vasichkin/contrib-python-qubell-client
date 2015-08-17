import unittest
from qubell.api.private.common import Response
from qubell.api.private.common import EntityList, QubellEntityList

class Stubs(object):
    count = 0
    full_data = \
        {'aa': 'aa', 'bb': [
            {'aaaa':'aaaa', 'bbbb':'bbbb'},
            {'cccc':'cccc', 'dddd':'dddd'}]
        }

    raw_objects = [
        {"id": "1", "name": "name1"},
        {"id": "2", "name": "name2", },
    ]

    def respond_with_given_data_first(self, partial_data):
        # Reply with given 'partial_data' for 3 times, then reply with 'full_data'
        self.count += 1
        if self.count <= 3:
            return partial_data
        else:
            return self.full_data

    def respond_ok(self):
        return self.full_data

    def respond_as_api(self, ):
        return self.raw_objects

    def respond_custom(self, data):
        return data

    def __init__(self, id=None):
        self.id = id

    @property
    def submodules(self):
        return self.raw_objects

class test_Response(unittest.TestCase):
    instance_json = Stubs.full_data

    def setUp(self):
        self.stubs = Stubs()

    def test_happy_pass(self):
        # Check Response class returns all without retries
        resp = Response(data_fn=lambda: self.stubs.respond_ok())
        assert resp['aa'] == 'aa'
        assert isinstance(resp['bb'],list)
        assert resp['bb'][0]['aaaa']=='aaaa'
        assert resp.tries_count == 0

    def test_retry_root(self):
        # Check Response class retries if there missing key in root
        resp = Response(data_fn=lambda: self.stubs.respond_with_given_data_first({}))
        assert resp['bb']
        assert resp.tries_count == 3

    def test_retry_submodule(self):
        # Check Response class retries if there missing key in child
        resp = Response(data_fn=lambda: self.stubs.respond_with_given_data_first({}))
        assert resp['bb'][0]['aaaa']
        assert resp.tries_count == 3

    def test_retry_false(self):
        resp = Response(data_fn=lambda: self.stubs.respond_with_given_data_first({}), retry_query=False)
        self.assertRaises(KeyError, resp.__getitem__, 'bb')
        assert resp.tries_count == 0

    def test_retry_true(self):
        resp = Response(data_fn=lambda: self.stubs.respond_with_given_data_first({}), retry_query=True)
        assert resp['bb']
        assert resp.tries_count == 3

    def test_responce_list(self):
        resp = Response(data_fn=lambda: self.stubs.respond_custom([7, 8.43, '9']))
        assert resp[0] == 7
        assert resp[1] == 8.43
        assert resp[2] == '9'

    def test_entity_list(self):
        resp = Response(data_fn=lambda: self.stubs.respond_as_api())
        ent_list = QubellEntityList(list_json_method=resp.get_data)
        ent_list.base_clz = Stubs
        assert ent_list
        assert ent_list['name1']
        sub = ent_list['name2']
        assert sub
        assert sub.submodules
        assert sub.submodules[0]

