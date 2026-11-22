import unittest
from project import analyze


class GuideTests(unittest.TestCase):
    def test_multiple_actions_and_alias(self):
        output = analyze({"guide": "# Edit\nClick **OLD** and tap “New”.",
                          "controls": [{"label": "New", "formerly": ["Old"]}]})
        self.assertEqual([x["Status"] for x in output["rows"]], ["Renamed", "Current"])
        self.assertEqual(output["rows"][1]["Line"], 2)

    def test_ignore_fences_and_unmarked_prose(self):
        result = analyze({"guide": "~~~sh\nopen **Store**\n~~~\nOpen the door.",
                          "controls": [{"label": "Store"}]})
        self.assertEqual(result["rows"], [])

    def test_similarity_never_proves_a_rename(self):
        result = analyze({"guide": "Tap **Saves**", "controls": [{"label": "Save"}]})
        self.assertEqual((result["rows"][0]["Status"], result["rows"][0]["Candidate"]), ("Unverified", "Save"))

    def test_ambiguous_alias(self):
        row = analyze({"guide": "Click **More**", "controls": [
            {"label": "Account", "formerly": ["More"]}, {"label": "Settings", "formerly": ["More"]}]})["rows"][0]
        self.assertEqual(row["Status"], "Ambiguous alias")

    def test_invalid_registry(self):
        with self.assertRaises(ValueError):
            analyze({"guide": "", "controls": [{"label": "Save"}, {"label": "save"}]})
