"""Prove the independent verifier rejects false labels in every dataset."""
import copy
import contextlib
import io
import unittest
from unittest.mock import patch

import verify_golden as golden


class GoldenIntegrity(unittest.TestCase):
    def test_all_categories_have_effective_proof_checks(self):
        original = {name: golden.read(name) for name in golden.NAMES}
        def corrupt(name, rows):
            exp = rows[0]['expected_output']
            if name == 'extraction':
                exp['labs'][0]['result'] = '999'
            elif name == 'classification':
                exp['status'] = 'Normal'
            elif name == 'normalization':
                exp['converted_value'] = '999'
            elif name == 'retrieval':
                exp['relevant_evidence_ids'] = ['E3']
            elif name in ('explanations', 'chat'):
                exp['required_facts'][0]['result'] = '999'
            elif name == 'workflow':
                exp['summary']['normal'] = 99
            else:
                exp['verdict'] = 'fail'
        for name in golden.NAMES:
            with self.subTest(dataset=name):
                changed = copy.deepcopy(original)
                corrupt(name, changed[name])
                with patch.object(golden, 'read', side_effect=lambda n: changed[n]):
                    with contextlib.redirect_stdout(io.StringIO()):
                        with self.assertRaises(AssertionError):
                            golden.verify(check_manifest=False)

    def test_empty_category_is_rejected(self):
        original = {name: golden.read(name) for name in golden.NAMES}
        for name in golden.NAMES:
            with self.subTest(dataset=name):
                with patch.object(golden, 'read', side_effect=lambda n: [] if n == name else original[n]):
                    with self.assertRaises(AssertionError):
                        golden.verify(check_manifest=False)


if __name__ == '__main__':
    unittest.main()
