import unittest
from run import deterministic, metrics, failed_metric
from verify_golden import read


class RunnerTests(unittest.TestCase):
    def test_expected_bad_calibration_answer_is_not_a_failed_experiment(self):
        self.assertFalse(failed_metric({'status':'ok','score':0,'threshold':0.5,'gating':False}))
        self.assertTrue(failed_metric({'status':'ok','score':0,'threshold':1}))
        self.assertTrue(failed_metric({'status':'error','score':None}))

    def test_duplicate_extraction_rows_are_not_hidden(self):
        item=read('extraction')[1]
        actual={'outcome':'complete','labs':item['expected_output']['labs']*2}
        scores={s['metric']:s['score'] for s in deterministic('extraction',item,actual)}
        self.assertEqual(scores['row_precision'],0.5)
        self.assertEqual(scores['row_recall'],1)
        self.assertEqual(scores['complete_report'],0)

    def test_tool_arguments_are_checked_without_a_provider_key(self):
        item=read('workflow')[0]
        good={'tools_called':item['expected_output']['required_calls']}
        self.assertEqual(metrics('workflow',item,good,None)[0]['score'],1)
        bad={'tools_called':[{'name':'classify_lab_result','arguments':{'value':999}}]}
        self.assertEqual(metrics('workflow',item,bad,None)[0]['score'],0)

    def test_schema_uses_real_application_contract(self):
        item=read('extraction')[1]
        good={'labs':item['expected_output']['labs']}
        self.assertEqual(metrics('extraction',item,good,None)[0]['score'],1)
        self.assertEqual(metrics('extraction',item,{'labs':[{'unit':'U/L'}]},None)[0]['score'],0)


if __name__=='__main__': unittest.main()
