"""SACCO core logic: members, deposits, withdrawals, performance analysis.
Uses SQLite in-memory by default (pass a filename to persist)."""
import sqlite3
from datetime import datetime

MIN_BALANCE = 5000  # UGX that must remain after a withdrawal


class SaccoError(Exception):
    pass


class Sacco:
    def __init__(self, db=":memory:"):
        self.db = sqlite3.connect(db)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS members(
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            phone TEXT, village TEXT, joined TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS transactions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL REFERENCES members(id),
            type TEXT NOT NULL CHECK(type IN ('DEPOSIT','WITHDRAWAL')),
            amount INTEGER NOT NULL CHECK(amount > 0), ts TEXT NOT NULL);
        """)

    @staticmethod
    def _now():
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def add_member(self, name, phone="", village=""):
        if not name.strip():
            raise SaccoError("Member name is required.")
        cur = self.db.execute(
            "INSERT INTO members(name,phone,village,joined) VALUES(?,?,?,?)",
            (name.strip(), phone.strip(), village.strip(), self._now()))
        self.db.commit()
        return cur.lastrowid

    def members(self):
        return self.db.execute("""
            SELECT m.id, m.name, m.phone, m.village, m.joined,
                   COALESCE(SUM(CASE t.type WHEN 'DEPOSIT' THEN t.amount
                                ELSE -t.amount END),0) AS balance
            FROM members m LEFT JOIN transactions t ON t.member_id=m.id
            GROUP BY m.id ORDER BY m.id""").fetchall()

    def balance(self, member_id):
        if not self.db.execute("SELECT 1 FROM members WHERE id=?", (member_id,)).fetchone():
            raise SaccoError(f"No member with ID {member_id}.")
        return self.db.execute("""SELECT COALESCE(SUM(CASE type WHEN 'DEPOSIT'
            THEN amount ELSE -amount END),0) FROM transactions WHERE member_id=?""",
            (member_id,)).fetchone()[0]

    def _post(self, member_id, kind, amount):
        if not isinstance(amount, int) or amount <= 0:
            raise SaccoError("Amount must be a positive whole number (UGX).")
        bal = self.balance(member_id)
        if kind == "WITHDRAWAL" and bal - amount < MIN_BALANCE:
            raise SaccoError(f"Withdrawal refused: balance must stay >= {MIN_BALANCE:,} UGX "
                             f"(current {bal:,}).")
        self.db.execute("INSERT INTO transactions(member_id,type,amount,ts) VALUES(?,?,?,?)",
                        (member_id, kind, amount, self._now()))
        self.db.commit()
        return self.balance(member_id)

    def deposit(self, member_id, amount):
        return self._post(member_id, "DEPOSIT", amount)

    def withdraw(self, member_id, amount):
        return self._post(member_id, "WITHDRAWAL", amount)

    def statement(self, member_id=None):
        q = """SELECT t.id, m.name, t.type, t.amount, t.ts FROM transactions t
               JOIN members m ON m.id=t.member_id"""
        args = ()
        if member_id:
            q += " WHERE m.id=?"
            args = (member_id,)
        return self.db.execute(q + " ORDER BY t.id DESC", args).fetchall()

    def analysis(self):
        one = lambda sql: self.db.execute(sql).fetchone()[0] or 0
        n = one("SELECT COUNT(*) FROM members")
        dep = one("SELECT SUM(amount) FROM transactions WHERE type='DEPOSIT'")
        wd = one("SELECT SUM(amount) FROM transactions WHERE type='WITHDRAWAL'")
        rows = self.members()
        top = sorted(rows, key=lambda r: r["balance"], reverse=True)[:3]
        monthly = self.db.execute("""SELECT substr(ts,1,7) AS month,
            SUM(CASE type WHEN 'DEPOSIT' THEN amount ELSE 0 END) AS dep,
            SUM(CASE type WHEN 'WITHDRAWAL' THEN amount ELSE 0 END) AS wd
            FROM transactions GROUP BY month ORDER BY month""").fetchall()
        return {
            "members": n, "total_deposits": dep, "total_withdrawals": wd,
            "net_savings": dep - wd,
            "average_balance": round((dep - wd) / n) if n else 0,
            "retention_ratio": round((dep - wd) / dep * 100, 1) if dep else 0.0,
            "top_savers": [(r["name"], r["balance"]) for r in top],
            "monthly": [(r["month"], r["dep"], r["wd"]) for r in monthly],
        }


def seed_demo(s):
    data = [("Nakato Sarah", "0772000111", "Kasawo"), ("Okello James", "0701222333", "Wakiso"),
            ("Namubiru Grace", "0755444555", "Mukono"), ("Ssempala Peter", "0782666777", "Luwero")]
    ids = [s.add_member(*d) for d in data]
    for i, amt in zip(ids, (150000, 80000, 220000, 45000)):
        s.deposit(i, amt)
    s.withdraw(ids[0], 30000)
    s.deposit(ids[1], 25000)
    return ids
