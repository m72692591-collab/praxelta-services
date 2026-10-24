import unittest
from src.matching import Matcher

class MatchingTests(unittest.TestCase):
    def setUp(self):
        self.m = Matcher()
        self.m.bind('fake-user-1','10001',self.m.token('fake-user-1'))

    def test_verified_delivery(self):
        self.assertTrue(self.m.deliver('event-1','fake-user-1','CODE-TEST'))
        self.assertEqual(self.m.outbox[0]['chat_id'],'10001')

    def test_duplicate_suppressed(self):
        self.m.deliver('event-1','fake-user-1','CODE-TEST')
        self.assertFalse(self.m.deliver('event-1','fake-user-1','CODE-TEST'))
        self.assertEqual(len(self.m.outbox),1)

    def test_collision_rejected(self):
        self.m.deliver('event-1','fake-user-1','CODE-TEST')
        with self.assertRaises(ValueError): self.m.deliver('event-1','fake-user-1','DIFFERENT')

    def test_unknown_recipient_rejected(self):
        with self.assertRaises(ValueError): self.m.deliver('event-2','unknown','CODE')

    def test_wrong_proof_rejected(self):
        with self.assertRaises(ValueError): self.m.bind('fake-user-2','10002','wrong')

    def test_chat_takeover_rejected(self):
        with self.assertRaises(ValueError): self.m.bind('fake-user-2','10001',self.m.token('fake-user-2'))

    def test_rebind_rejected(self):
        with self.assertRaises(ValueError): self.m.bind('fake-user-1','10003',self.m.token('fake-user-1'))

    def test_bad_chat_rejected(self):
        with self.assertRaises(ValueError): self.m.bind('fake-user-2','@handle',self.m.token('fake-user-2'))


class DurabilityTests(unittest.TestCase):
    def test_restart_recovers_pending(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / 'demo.sqlite')
            a = Matcher(db)
            a.bind('person','123',a.token('person'))
            a.deliver('evt','person','FAKE-CODE')
            a.db.close()
            b = Matcher(db)
            self.assertEqual(b.pending(), [{'event_id':'evt','chat_id':'123','text':'FAKE-CODE'}])
            self.assertTrue(b.acknowledge('evt'))
            self.assertEqual(b.pending(), [])
            self.assertFalse(b.acknowledge('evt'))
            b.db.close()

    def test_replay_after_acknowledgement(self):
        m = Matcher()
        m.bind('p','1',m.token('p'))
        self.assertTrue(m.deliver('e','p','FAKE'))
        m.acknowledge('e')
        self.assertFalse(m.deliver('e','p','FAKE'))
        self.assertEqual(m.pending(), [])

    def test_event_recipient_collision(self):
        m = Matcher()
        for p, c in [('p1','1'),('p2','2')]:
            m.bind(p,c,m.token(p))
        m.deliver('e','p1','FAKE')
        with self.assertRaises(ValueError):
            m.deliver('e','p2','FAKE')

    def test_empty_payload_rejected(self):
        m = Matcher()
        m.bind('p','1',m.token('p'))
        with self.assertRaises(ValueError):
            m.deliver('e','p','')
