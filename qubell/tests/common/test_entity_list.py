from qubell import deprecated
import unittest2

from qubell.api.private.common import EntityList, IdName
from qubell.api.private import exceptions


class EntityListTests(unittest2.TestCase):
    class DummyEntity:
        def __init__(self, id, name):
            self.id = id
            self.name = name

        @property
        def dummy(self):
            'dummy property'
            return self.id + "--==--" + self.name

        @deprecated
        def plain_old(self): pass

        @deprecated(msg="yo")
        def plain_old_with_message(self): pass

    class DummyEntityList(EntityList):
        def __init__(self, raw_json):
            self.raw_json = raw_json
            EntityList.__init__(self)

        def _id_name_list(self):
            self._list = [IdName(item["id"], item["name"]) for item in self.raw_json]
        def _get_item(self, id_name):
            return EntityListTests.DummyEntity(id_name.id, id_name.name)

    raw_objects = [
        {"id": "1", "name": "name1"},
        {"id": "2", "name": "name2"},
        {"id": "3", "name": "name3dup"},
        {"id": "4", "name": "name3dup"},
        {"id": "1234567890abcd1234567890", "name": "with_bson_id"}
    ]

    def setUp(self):
        self.entity_list = EntityListTests.DummyEntityList(self.raw_objects)

    def test_get_item_by_name(self):
        assert self.entity_list["name2"].id == "2"

    def test_get_item_by_id(self):
        assert self.entity_list["1234567890abcd1234567890"].name == "with_bson_id"

    def test_get_last_item_when_duplicate_by_name(self):
        assert "4" == self.entity_list["name3dup"].id

    def test_get_item_by_index(self):
        assert "2" == self.entity_list[1].id
        assert "4" == self.entity_list[-2].id

    def test_get_item_by_slice(self):
        assert ["2", "4"] == [i.id for i in self.entity_list[1:4:2]]

    def test_not_existing_item(self):
        with self.assertRaises(exceptions.NotFoundError) as context:
            assert self.entity_list["hren"]
        assert str(context.exception) == "None of 'hren' in DummyEntityList"

    def test__len(self):
        assert len(self.raw_objects) == len(self.entity_list)

    def test__in_by_item(self):
        dummy = EntityListTests.DummyEntity("1", "name1")
        assert dummy in self.entity_list

    def test__in_by_id(self):
        assert "1234567890abcd1234567890" in self.entity_list

    def test__in_by_uid(self):
        assert u"1234567890abcd1234567890" in self.entity_list

    def test__in_by_name(self):
        assert "name2" in self.entity_list
        assert "name3dup" in self.entity_list

    def test__iter(self):
        entity_ids = [e.id for e in self.entity_list]
        raw_ids = [e["id"] for e in self.raw_objects]
        self.assertEqual(entity_ids, raw_ids)
        for e in self.entity_list:
            assert isinstance(e, EntityListTests.DummyEntity)

    def test_deprecation_visually(self):
        self.entity_list[0].plain_old()
        self.entity_list["name2"].plain_old_with_message()

    def test__repr(self):
        assert repr(self.entity_list) == "DummyEntityList([IdName(id='1', name='name1'), IdName(id='2', name='name2'), IdName(id='3', name='name3dup'), IdName(id='4', name='name3dup'), IdName(id='1234567890abcd1234567890', name='with_bson_id')])"
