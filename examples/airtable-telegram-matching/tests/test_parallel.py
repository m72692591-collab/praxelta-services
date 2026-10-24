"""Independent connections exercise actual SQLite intake races, with fake data."""
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

from src.matching import Matcher


class ParallelTests(unittest.TestCase):
    def test_three_traders_simultaneously_keep_their_own_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'test.sqlite'
            setup = Matcher(path)
            for n in range(1, 4):
                setup.bind(f'fake-{n}', str(10000+n), setup.token(f'fake-{n}'))
            setup.db.close()
            barrier = Barrier(3)

            def submit(n):
                m = Matcher(path)
                try:
                    barrier.wait(timeout=5)
                    return m.deliver(f'evt-{n}', f'fake-{n}', f'DEMO-{n}')
                finally:
                    m.db.close()

            with ThreadPoolExecutor(max_workers=3) as pool:
                self.assertEqual(list(pool.map(submit, range(1, 4))), [True]*3)
            result = Matcher(path)
            self.assertEqual(
                {row['chat_id']: row['text'] for row in result.pending()},
                {'10001': 'DEMO-1', '10002': 'DEMO-2', '10003': 'DEMO-3'},
            )
            result.db.close()

    def test_same_event_simultaneously_queues_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'test.sqlite'
            setup = Matcher(path)
            setup.bind('fake', '10001', setup.token('fake'))
            setup.db.close()
            barrier = Barrier(2)

            def submit(_):
                m = Matcher(path)
                try:
                    barrier.wait(timeout=5)
                    return m.deliver('same-event', 'fake', 'DEMO-1')
                finally:
                    m.db.close()

            with ThreadPoolExecutor(max_workers=2) as pool:
                self.assertEqual(sorted(pool.map(submit, range(2))), [False, True])
            result = Matcher(path)
            self.assertEqual(len(result.pending()), 1)
            result.db.close()

    def test_noncanonical_or_group_chat_ids_rejected(self):
        m = Matcher()
        try:
            for value in ['00', '01', '--123', '-123', '１２３', ' 123', str(2**52)]:
                with self.subTest(value=value), self.assertRaises(ValueError):
                    m.bind('fake', value, m.token('fake'))
        finally:
            m.db.close()
