"""Unit tests on invented data; no network accounts are accessed."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from intake import BadRequest, Conflict, init_db, normalize, process_event

SAMPLE = {"event_id": "evt-001", "email": "DEMO@example.com", "name": "Demo Person", "source": "website", "message": "Need a quote"}

class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.temp.name) / "test.sqlite")
        init_db(self.path)
    def tearDown(self):
        self.temp.cleanup()
    def test_new_lead(self):
        self.assertEqual(process_event(self.path, SAMPLE)["operation"], "created")
    def test_duplicate_retry_same_event(self):
        first = process_event(self.path, SAMPLE)
        second = process_event(self.path, SAMPLE)
        self.assertEqual(second["status"], "duplicate_event")
        self.assertEqual(first["lead_id"], second["lead_id"])
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM receipts").fetchone()[0], 1)
    def test_conflicting_payload_for_same_id_is_rejected(self):
        process_event(self.path, SAMPLE)
        with self.assertRaises(Conflict):
            process_event(self.path, {**SAMPLE, "message": "changed"})
    def test_same_email_second_request_updates(self):
        process_event(self.path, SAMPLE)
        second = process_event(self.path, {**SAMPLE, "event_id": "evt-002", "email": "demo@EXAMPLE.com"})
        self.assertEqual(second["operation"], "updated")
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM leads").fetchone()[0], 1)
    def test_invalid_email(self):
        with self.assertRaises(BadRequest):
            process_event(self.path, {**SAMPLE, "email": "not-an-email"})
    def test_invalid_source(self):
        with self.assertRaises(BadRequest):
            process_event(self.path, {**SAMPLE, "source": "unrecognized"})
    def test_unexpected_field(self):
        with self.assertRaises(BadRequest):
            process_event(self.path, {**SAMPLE, "admin": True})
    def test_missing_fields(self):
        with self.assertRaises(BadRequest):
            process_event(self.path, {"event_id": "x"})
    def test_invalid_event_id(self):
        with self.assertRaises(BadRequest):
            process_event(self.path, {**SAMPLE, "event_id": "../oops"})
    def test_bad_message_type(self):
        with self.assertRaises(BadRequest):
            process_event(self.path, {**SAMPLE, "message": ["bad"]})
    def test_field_limits(self):
        with self.assertRaises(BadRequest):
            process_event(self.path, {**SAMPLE, "name": "a" * 121})
    def test_normalization(self):
        self.assertEqual(normalize(SAMPLE)["email"], "demo@example.com")

if __name__ == "__main__":
    unittest.main()
