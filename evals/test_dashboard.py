import unittest
from email.message import Message
from unittest.mock import Mock, patch
import dashboard


class DashboardTests(unittest.TestCase):
    def tearDown(self): dashboard.ACTIVE.clear()

    def test_untrusted_origin_and_host_are_rejected(self):
        handler=object.__new__(dashboard.Handler)
        for host,origin,allowed in [('localhost:5173','http://localhost:5173',True),
                                     ('evil.example','http://localhost:5173',False),
                                     ('localhost:8766','https://evil.example',False)]:
            handler.headers=Message();handler.headers['Host']=host;handler.headers['Origin']=origin
            self.assertEqual(handler.local(),allowed)

    def test_run_input_cannot_select_arbitrary_commands_or_silent_paid_runs(self):
        for payload in [{'suite':'anything'}, {'suite':'calibration'},
                        {'suite':'deterministic','model':'model; malicious command'},
                        {'suite':'deterministic','limit':True}]:
            with self.subTest(payload=payload), self.assertRaises(ValueError): dashboard.launch(payload)

    def test_only_one_fixed_runner_is_launched(self):
        process=Mock();process.poll.return_value=None
        with patch.object(dashboard.subprocess,'Popen',return_value=process) as launch:
            id=dashboard.launch({'suite':'deterministic'})
            argv=launch.call_args.args[0]
            self.assertEqual(argv[1],str(dashboard.ROOT/'evals/run.py'))
            self.assertNotIn('--judge',argv)
            self.assertEqual(dashboard.active()['id'],id)
            with self.assertRaises(ValueError): dashboard.launch({'suite':'deterministic'})
            self.assertEqual(launch.call_count,1)


if __name__=='__main__': unittest.main()
