"""Offline, fail-closed matching and durable simulated dispatch (stdlib only)."""
import hashlib
import hmac
import re
import sqlite3


class Matcher:
    def __init__(self, path=':memory:', secret=b'demo-only-secret'):
        self.db = sqlite3.connect(str(path), timeout=5)
        self.secret = secret
        self.db.execute('PRAGMA busy_timeout=5000')
        self.db.execute('CREATE TABLE IF NOT EXISTS bindings (person TEXT PRIMARY KEY, chat TEXT UNIQUE NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS deliveries (event TEXT PRIMARY KEY, person TEXT NOT NULL, chat TEXT NOT NULL, payload_hash TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL DEFAULT \'pending\')')
        self.db.commit()

    def token(self, person):
        return hmac.new(self.secret, person.encode(), hashlib.sha256).hexdigest()

    def bind(self, person, chat, token):
        if not isinstance(person, str) or not person or not isinstance(chat, str) or not isinstance(token, str):
            raise ValueError('invalid binding fields')
        if not hmac.compare_digest(self.token(person), token):
            raise ValueError('invalid binding proof')
        if not re.fullmatch(r'[1-9][0-9]{0,15}', chat) or int(chat) >= 2**52:
            raise ValueError('invalid chat_id')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            existing = self.db.execute('SELECT chat FROM bindings WHERE person=?', (person,)).fetchone()
            if existing and existing[0] != chat:
                raise ValueError('rebind requires separate verification')
            other = self.db.execute('SELECT person FROM bindings WHERE chat=?', (chat,)).fetchone()
            if other and other[0] != person:
                raise ValueError('chat already owned')
            self.db.execute('INSERT OR IGNORE INTO bindings VALUES (?,?)', (person, chat))

    def deliver(self, event, person, payload):
        if not all(isinstance(x, str) and x for x in (event, person, payload)):
            raise ValueError('missing delivery fields')
        digest = hashlib.sha256(payload.encode()).hexdigest()
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            chat = self.db.execute('SELECT chat FROM bindings WHERE person=?', (person,)).fetchone()
            if not chat:
                raise ValueError('unverified recipient')
            prior = self.db.execute('SELECT person,chat,payload_hash FROM deliveries WHERE event=?', (event,)).fetchone()
            if prior:
                if prior != (person, chat[0], digest):
                    raise ValueError('event_id collision')
                return False
            self.db.execute('INSERT INTO deliveries(event,person,chat,payload_hash,payload) VALUES (?,?,?,?,?)', (event, person, chat[0], digest, payload))
        return True

    def pending(self):
        return [{'event_id': e, 'chat_id': c, 'text': p} for e, c, p in self.db.execute("SELECT event,chat,payload FROM deliveries WHERE status='pending' ORDER BY rowid")]

    def acknowledge(self, event):
        """Only mark delivered after a simulated successful send; no actual network call."""
        with self.db:
            result = self.db.execute("UPDATE deliveries SET status='sent' WHERE event=? AND status='pending'", (event,))
            return result.rowcount == 1

    @property
    def outbox(self):
        return self.pending()
