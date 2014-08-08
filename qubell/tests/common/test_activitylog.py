import unittest
from qubell.api.private.instance import activityLog

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
               "eventTypeText": "workflow started"}, {"time": 1407341614000, "self": "true",
                                                      "description": "'destroy' (53e2542ee4b0098a7cc0ac63) by LAUNCHER Tester",
                                                      "severity": "INFO", "eventTypeText": "command started"},
              {"time": 1407341600208, "self": "true", "description": "Action WF launched", "severity": "DEBUG",
               "source": "out.app_output", "eventTypeText": "signals updated"},
              {"time": 1407341599550, "self": "true", "description": "wf with status 'Succeeded'", "severity": "INFO",
               "source": "wfapp", "eventTypeText": "workflow finished"},
              {"time": 1407341599477, "self": "true", "description": "out: Action WF launched", "severity": "DEBUG",
               "source": "wfapp", "eventTypeText": "dynamic links updated"},
              {"time": 1407341599409, "self": "true", "description": "wf", "severity": "INFO", "source": "wfapp",
               "eventTypeText": "workflow started"}, {"time": 1407341599000, "self": "true",
                                                      "description": "'action.default' (53e2541fe4b0cc5147c57557) by LAUNCHER Tester",
                                                      "severity": "INFO", "eventTypeText": "command started"},
              {"time": 1407341599000, "self": "true", "description": "'action.default' (53e2541fe4b0cc5147c57557)",
               "severity": "INFO", "eventTypeText": "command finished"},
              {"time": 1407341594969, "self": "true", "description": "Running", "severity": "INFO",
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
               "eventTypeText": "status updated"}, {"time": 1407341530000, "self": "true",
                                                    "description": "'launch' (53e253dae4b0098a7cc0ac62) by LAUNCHER Tester",
                                                    "severity": "INFO", "eventTypeText": "command started"}]

    def test_sugar(self):
        all_logs = activityLog(self.actlog)
        info_logs = activityLog(self.actlog, severity='INFO')

        self.assertEqual(len(all_logs), 21)
        self.assertEqual(len(info_logs), 14)

        for log in info_logs:
            assert log['severity'] == 'INFO'

        assert 'status updated: Running' in info_logs
        self.assertEqual(all_logs["command started: 'launch' \(.*\) by LAUNCHER Tester"], 1407341530000)
        self.assertEqual(all_logs[1407341530000], "command started: 'launch' (53e253dae4b0098a7cc0ac62) by LAUNCHER Tester")
        self.assertEqual(all_logs[0], "command started: 'launch' (53e253dae4b0098a7cc0ac62) by LAUNCHER Tester")
        self.assertEqual(all_logs[-1], 'status updated: Destroyed')

    def test_interval_start(self):
        logs = activityLog(self.actlog, severity='INFO', start=1407341614922)
        self.assertEqual(len(logs), 4)
        self.assertEqual(logs[0], "workflow started: destroy")
        self.assertEqual(logs[-1], "status updated: Destroyed")

    def test_interval_end(self):
        logs = activityLog(self.actlog, severity='INFO', end=1407341594969)
        self.assertEqual(len(logs), 5)
        self.assertEqual(logs[0], "command started: 'launch' (53e253dae4b0098a7cc0ac62) by LAUNCHER Tester")
        self.assertEqual(logs[-1], "status updated: Running")

    def test_get_interval(self):
        logs = activityLog(self.actlog, severity='INFO').get_interval("command started: 'action.default' \(.*\) by LAUNCHER Tester", "workflow finished: wf with status 'Succeeded'")
        self.assertEqual(len(logs), 4)
        self.assertEqual(logs[0], "command started: 'action.default' (53e2541fe4b0cc5147c57557) by LAUNCHER Tester")
        self.assertEqual(logs[-1], "workflow finished: wf with status 'Succeeded'")

        logs = activityLog(self.actlog, severity='INFO').get_interval("command started: 'launch' \(.*\) by .*")
        self.assertEqual(len(logs), 14)

        logs = activityLog(self.actlog, severity='INFO').get_interval(end_text="workflow finished: destroy with status 'Succeeded'")
        self.assertEqual(len(logs), 13)
