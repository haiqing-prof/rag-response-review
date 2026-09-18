import copy
import unittest

from rag_response_review_sample import SYNTHETIC_CASES, response, review_response, run_all


class MetadataReviewTests(unittest.TestCase):
    def review(self, **changes):
        return review_response({"case_id": "edge", "response": response(**changes)})

    def test_eight_cases_and_expected_decisions(self):
        self.assertEqual(len(SYNTHETIC_CASES), 8)
        self.assertEqual([x["decision"] for x in run_all()],
                         ["pass", "flag", "abstain", "flag", "flag", "flag", "flag", "flag"])

    def test_unknown_source(self):
        self.assertIn("unknown_source:S9", run_all()[1]["issues"])

    def test_correct_abstention(self):
        self.assertEqual(run_all()[2]["issues"], [])

    def test_permission_is_checked_against_catalog(self):
        self.assertIn("permission_mismatch:S2", run_all()[3]["issues"])

    def test_caller_can_supply_team_permission(self):
        self.assertEqual(review_response(SYNTHETIC_CASES[3], ("team",))["decision"], "pass")

    def test_self_declared_permission_does_not_grant_access(self):
        data = copy.deepcopy(SYNTHETIC_CASES[3])
        data["response"]["granted_scopes"] = ["team"]
        self.assertEqual(review_response(data)["decision"], "flag")

    def test_version_mismatch(self):
        self.assertIn("version_mismatch:S1", run_all()[4]["issues"])

    def test_malformed_source_list(self):
        self.assertIn("source_ids_must_be_string_list", run_all()[5]["issues"])

    def test_unhashable_source_item_is_handled(self):
        self.assertEqual(self.review(source_ids=[{}])["decision"], "flag")

    def test_explicit_stale_marker(self):
        self.assertIn("stale_marker:S1", run_all()[6]["issues"])

    def test_unsupported_answer_is_flagged(self):
        self.assertIn("no_evidence_requires_abstain", run_all()[7]["issues"])

    def test_empty_sources_cannot_pass_with_evidence_flag(self):
        self.assertIn("evidence_requires_source_ids", self.review(source_ids=[])["issues"])

    def test_evidence_flag_must_be_boolean(self):
        self.assertIn("evidence_present_must_be_boolean", self.review(evidence="true")["issues"])

    def test_invalid_answer_mode(self):
        self.assertIn("invalid_answer_mode", self.review(mode="unknown")["issues"])

    def test_bad_versions_and_stale_list_are_flagged(self):
        result = self.review(versions=[], stale_source_ids="S1")
        self.assertIn("source_versions_must_be_mapping", result["issues"])
        self.assertIn("stale_source_ids_must_be_string_list", result["issues"])

    def test_missing_response_is_flagged(self):
        self.assertEqual(review_response({"case_id": "missing"})["decision"], "flag")

    def test_invalid_caller_permission_is_rejected(self):
        with self.assertRaises(ValueError):
            review_response(SYNTHETIC_CASES[0], "public")

    def test_no_input_mutation(self):
        before = copy.deepcopy(SYNTHETIC_CASES)
        run_all()
        self.assertEqual(before, SYNTHETIC_CASES)

    def test_semantic_truth_is_deliberately_not_checked(self):
        self.assertEqual(self.review(answer="The moon is made of cheese.")["decision"], "pass")


if __name__ == "__main__":
    unittest.main()
