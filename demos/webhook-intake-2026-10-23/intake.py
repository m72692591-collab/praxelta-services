"""PRAXELTA intake reference implementation: local-only, synthetic-data demo.

No third-party services, production deployment, or outbound messages.
"""
import hashlib
import json
import re
import sqlite3
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

MAX_BODY = 16_384
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

class BadRequest(ValueError):
    pass

class Conflict(ValueError):
    pass

def normalize(obj: Any) -> dict:
    if not isinstance(obj, dict):
        raise BadRequest("Object expected")
    if set(obj) - {"event_id", "email", "name", "source", "message"}:
        raise BadRequest("Unexpected fields")
    for key in ("event_id", "email", "name", "source"):
        if not isinstance(obj.get(key), str) or not obj[key].strip():
            raise BadRequest(f"Missing or invalid {key}")
    event_id = obj["event_id"].strip()
    name = obj["name"].strip()
    email = obj["email"].strip().casefold()
    source = obj["source"].strip().lower()
    message = obj.get("message", "")
    if not isinstance(message, str):
        raise BadRequest("Invalid message")
    message = message.strip()
    if len(event_id) > 80 or len(name) > 120 or len(email) > 254 or len(message) > 2000:
        raise BadRequest("Field too long")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}", event_id):
        raise BadRequest("Invalid event_id")
    if not EMAIL_PATTERN.fullmatch(email):
        raise BadRequest("Invalid email")
    if source not in {"website", "telegram", "form"}:
        raise BadRequest("Invalid source")
    return {"event_id": event_id, "email": email, "name": name, "source": source, "message": message}

def init_db(path: str):
    with closing(sqlite3.connect(path)) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("CREATE TABLE IF NOT EXISTS leads (id INTEGER PRIMARY KEY, email TEXT NOT NULL UNIQUE, name TEXT NOT NULL, source TEXT NOT NULL, message TEXT NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS receipts (event_id TEXT PRIMARY KEY, digest TEXT NOT NULL, lead_id INTEGER NOT NULL, operation TEXT NOT NULL)")
        db.commit()

def process_event(path: str, event: Any) -> dict:
    data = normalize(event)
    digest = hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=True).encode("utf-8")).hexdigest()
    with closing(sqlite3.connect(path, timeout=10, isolation_level=None)) as db:
        db.row_factory = sqlite3.Row
        db.execute("BEGIN IMMEDIATE")
        try:
            prior = db.execute("SELECT * FROM receipts WHERE event_id=?", (data["event_id"],)).fetchone()
            if prior:
                if prior["digest"] != digest:
                    raise Conflict("Event ID reused for different content")
                result = {"status": "duplicate_event", "lead_id": prior["lead_id"], "operation": prior["operation"]}
            else:
                person = db.execute("SELECT id FROM leads WHERE email=?", (data["email"],)).fetchone()
                if person:
                    lead_id = person["id"]
                    db.execute("UPDATE leads SET name=?,source=?,message=? WHERE id=?", (data["name"], data["source"], data["message"], lead_id))
                    operation = "updated"
                else:
                    cur = db.execute("INSERT INTO leads(email,name,source,message) VALUES(?,?,?,?)", (data["email"], data["name"], data["source"], data["message"]))
                    lead_id = cur.lastrowid
                    operation = "created"
                db.execute("INSERT INTO receipts(event_id,digest,lead_id,operation) VALUES(?,?,?,?)", (data["event_id"], digest, lead_id, operation))
                result = {"status": "accepted", "lead_id": lead_id, "operation": operation}
            db.execute("COMMIT")
            return result
        except Exception:
            db.execute("ROLLBACK")
            raise

class Handler(BaseHTTPRequestHandler):
    db_path = "intake-demo.sqlite3"
    def do_POST(self):
        if self.path != "/intake":
            return self.answer(404, {"error": "not_found"})
        try:
            size = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            size = -1
        if size < 0 or size > MAX_BODY:
            return self.answer(413, {"error": "invalid_length"})
        try:
            data = json.loads(self.rfile.read(size))
            result = process_event(self.db_path, data)
            return self.answer(200, result)
        except (json.JSONDecodeError, UnicodeDecodeError, BadRequest) as ex:
            return self.answer(400, {"error": "invalid_input", "detail": str(ex)[:140]})
        except Conflict as ex:
            return self.answer(409, {"error": "conflict", "detail": str(ex)})
    def do_GET(self):
        if self.path == "/health":
            return self.answer(200, {"status": "ok", "mode": "local_demo"})
        return self.answer(404, {"error": "not_found"})
    def answer(self, code, obj):
        blob = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(blob)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(blob)
    def log_message(self, format, *args):
        pass

def serve(db_path="intake-demo.sqlite3"):
    init_db(db_path)
    Handler.db_path = db_path
    srv = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    print("Local-only demo: http://127.0.0.1:8765/intake")
    srv.serve_forever()

if __name__ == "__main__":
    serve()
