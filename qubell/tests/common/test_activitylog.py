import unittest

from qubell.api.private import exceptions
from qubell.api.private.instance import ActivityLog


class test_activityLog(unittest.TestCase):
    actlog = [{"time": 1407341616257, "self": "true", "description": "Destroyed", "severity": "INFO",
               "eventTypeText": "status updated"},
              {"time": 1407341615501, "self": "true", "description": "destroy with status 'Succeeded'",
               "severity": "INFO", "source": "wfapp", "eventTypeText": "workflow finished"},
              {"time": 1407341615480, "self": "true", "description": "destroy", "severity": "DEBUG", "source": "wfapp",
               "eventTypeText": "step finished"},
              {"time": 1407341615429, "self": "true", "description": "destroy", "severity": "DEBUG", "source": "wfapp",
               "eventTypeText": "step started"},
              {"time": 1407341615000, "self": "true", "description": "'destroy'", "severity": "INFO",
               "eventTypeText": "command finished"},
              {"time": 1407341614922, "self": "true", "description": "destroy", "severity": "INFO", "source": "wfapp",
               "eventTypeText": "workflow started"},
              {"time": 1407341614000, "self": "true",
               "description": "'destroy' (53e2542ee4b0098a7cc0ac63) by "
                              "LAUNCHER Tester",
               "severity": "INFO", "eventTypeText": "command started"},
              {"time": 1407341600208, "self": "true", "description": "Action WF launched", "severity": "DEBUG",
               "source": "out.app_output", "eventTypeText": "signals updated"},
              {"time": 1407341599550, "self": "true", "description": "wf with status 'Succeeded'", "severity": "INFO",
               "source": "wfapp", "eventTypeText": "workflow finished"},
              {"time": 1407341599477, "self": "true", "description": "out: Action WF launched", "severity": "DEBUG",
               "source": "wfapp", "eventTypeText": "dynamic links updated"},
              {"time": 1407341599409, "self": "true", "description": "wf", "severity": "INFO", "source": "wfapp",
               "eventTypeText": "workflow started"},
              {"time": 1407341599000, "self": "true",
               "description": "'action.default' (53e2541fe4b0cc5147c57557) by "
                              "LAUNCHER Tester",
               "severity": "INFO", "eventTypeText": "command started"},
              {"time": 1407341599000, "self": "true", "description": "'action.default' (53e2541fe4b0cc5147c57557)",
               "severity": "INFO", "eventTypeText": "command finished"},
              {"time": 1407341594969, "self": "true", "description": "Active", "severity": "INFO",
               "eventTypeText": "status updated"},
              {"time": 1407341594513, "self": "true", "description": "This is default manifest", "severity": "DEBUG",
               "source": "out.app_output", "eventTypeText": "signals updated"},
              {"time": 1407341594000, "self": "true", "description": "'launch'", "severity": "INFO",
               "eventTypeText": "command finished"},
              {"time": 1407341593478, "self": "true", "description": "launch with status 'Succeeded'",
               "severity": "INFO", "source": "wfapp", "eventTypeText": "workflow finished"},
              {"time": 1407341593437, "self": "true",
               "description": "in: This is default manifest\nout: This is default manifest", "severity": "DEBUG",
               "source": "wfapp", "eventTypeText": "dynamic links updated"},
              {"time": 1407341593408, "self": "true", "description": "launch", "severity": "INFO", "source": "wfapp",
               "eventTypeText": "workflow started"},
              {"time": 1407341531694, "self": "true", "description": "Executing", "severity": "DEBUG",
               "eventTypeText": "status updated"},
              {"time": 1407341530000, "self": "true",
               "description": "'launch' (53e253dae4b0098a7cc0ac62) by LAUNCHER "
                              "Tester",
               "severity": "INFO", "eventTypeText": "command started"}]

    actlog_single = [{
        "time": 1407341530000,
        "self": "true",
        "description": '''in: This is default manifest
    out: This is default manifest''',
        "severity": "INFO", "eventTypeText": "command started"
    }]

    def test_sugar(self):
        all_logs = ActivityLog(self.actlog)
        info_logs = ActivityLog(self.actlog, severity='INFO')

        self.assertEqual(len(all_logs), 21)
        self.assertEqual(len(info_logs), 14)

        for log in info_logs:
            assert log['severity'] == 'INFO'

        assert 'status updated: Active' in info_logs
        self.assertEqual(all_logs["command started: 'launch' \(.*\) by LAUNCHER Tester"], 1407341530000)
        self.assertEqual(all_logs[1407341530000],
                         "command started: 'launch' (53e253dae4b0098a7cc0ac62) by LAUNCHER Tester")
        self.assertEqual(all_logs[0], "command started: 'launch' (53e253dae4b0098a7cc0ac62) by LAUNCHER Tester")
        self.assertEqual(all_logs[-1], 'status updated: Destroyed')

    def test_interval_start(self):
        logs = ActivityLog(self.actlog, severity='INFO', start=1407341614922)
        self.assertEqual(len(logs), 4)
        self.assertEqual(logs[0], "workflow started: destroy")
        self.assertEqual(logs[-1], "status updated: Destroyed")

    def test_interval_end(self):
        logs = ActivityLog(self.actlog, severity='INFO', end=1407341594969)
        self.assertEqual(len(logs), 5)
        self.assertEqual(logs[0], "command started: 'launch' (53e253dae4b0098a7cc0ac62) by LAUNCHER Tester")
        self.assertEqual(logs[-1], "status updated: Active")

    def test_get_interval(self):
        logs = ActivityLog(self.actlog, severity='INFO').get_interval(
            "command started: 'action.default' \(.*\) by LAUNCHER Tester",
            "workflow finished: wf with status 'Succeeded'")
        self.assertEqual(len(logs), 4)
        self.assertEqual(logs[0], "command started: 'action.default' (53e2541fe4b0cc5147c57557) by LAUNCHER Tester")
        self.assertEqual(logs[-1], "workflow finished: wf with status 'Succeeded'")

        logs = ActivityLog(self.actlog, severity='INFO').get_interval("command started: 'launch' \(.*\) by .*")
        self.assertEqual(len(logs), 14)

        logs = ActivityLog(self.actlog, severity='INFO').get_interval(
            end_text="workflow finished: destroy with status 'Succeeded'")
        self.assertEqual(len(logs), 13)

    def test_get_wrong_interval(self):
        with self.assertRaises(exceptions.NotFoundError):
            ActivityLog(self.actlog, severity='INFO').get_interval(start_text='foo bar')
        with self.assertRaises(exceptions.NotFoundError):
            ActivityLog(self.actlog, severity='INFO').get_interval(start_text='foo bar', end_text='foo bar')
        with self.assertRaises(exceptions.NotFoundError):
            ActivityLog(self.actlog, severity='INFO').get_interval(end_text='foo bar')

    def test_slice_take_first(self):
        logs = ActivityLog(self.actlog)[:3]  # take 3 first entries only
        self.assertEqual(len(logs), 3)
        self.assertEqual(logs[0], "command started: 'launch' (53e253dae4b0098a7cc0ac62) by LAUNCHER Tester")
        self.assertEqual(logs[1], "status updated: Executing")
        self.assertEqual(logs[2], "workflow started: launch")

    def test_slice_take_last(self):
        logs = ActivityLog(self.actlog)[-3:]  # take 3 last entries only
        self.assertEqual(len(logs), 3)
        self.assertEqual(logs[0], "step finished: destroy")
        self.assertEqual(logs[1], "workflow finished: destroy with status 'Succeeded'")
        self.assertEqual(logs[2], "status updated: Destroyed")

    def test_slice_drop_first(self):
        logs = ActivityLog(self.actlog)[17:]  # drop 17 first entries
        self.assertEqual(len(logs), 4)
        self.assertEqual(logs[0], "step started: destroy")
        self.assertEqual(logs[1], "step finished: destroy")
        self.assertEqual(logs[2], "workflow finished: destroy with status 'Succeeded'")
        self.assertEqual(logs[3], "status updated: Destroyed")

    def test_slice_drop_last(self):
        logs = ActivityLog(self.actlog)[:-17]  # drop 17 last entries
        self.assertEqual(len(logs), 4)
        self.assertEqual(logs[0], "command started: 'launch' (53e253dae4b0098a7cc0ac62) by LAUNCHER Tester")
        self.assertEqual(logs[1], "status updated: Executing")
        self.assertEqual(logs[2], "workflow started: launch")
        self.assertEqual(logs[3], "dynamic links updated: in: This is default manifest\nout: This is default manifest")

    def test_slice_get_last(self):
        logs = ActivityLog(self.actlog_single)
        self.assertEqual(logs[len(logs) - 1], logs[-1])
        self.assertEqual(str(logs[len(logs) - 1]), str(logs[-1]))

    def test_find_empty_result(self):
        logs = ActivityLog(self.actlog_single)
        with self.assertRaises(exceptions.NotFoundError):
            logs.find("foo bar")

    # noinspection PyStatementEffect
    def test_get_empty_result(self):
        logs = ActivityLog(self.actlog_single)
        with self.assertRaises(exceptions.NotFoundError):
            logs[1000000000001]
        with self.assertRaises(exceptions.NotFoundError):
            logs[len(logs)+1]
        with self.assertRaises(exceptions.NotFoundError):
            logs[-5]
        with self.assertRaises(exceptions.NotFoundError):
            logs['qwerty']


    def test_lookup_error(self):
        l = ActivityLog(self.actlog_single)[object()]
        assert not l
        # todo: should throw with self.assertRaises(LookupError):

    def test_search_with_colon(self):
        l = ActivityLog(self.actlog_single)
        item = l.find('in: This is default')
        assert item

    def test_not_in(self):
        assert not "foo bar" in ActivityLog(self.actlog_single)
