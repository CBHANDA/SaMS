"""SACCO Management System - Tkinter GUI. Run: python sacco_app.py"""
import tkinter as tk
from tkinter import ttk, messagebox
from sacco_core import Sacco, SaccoError, seed_demo


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SACCO Management System")
        self.geometry("860x560")
        self.s = Sacco()  # in-memory database
        seed_demo(self.s)
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=8)
        self.t_mem, self.t_tx, self.t_an = (ttk.Frame(nb) for _ in range(3))
        nb.add(self.t_mem, text="Members")
        nb.add(self.t_tx, text="Deposit / Withdraw")
        nb.add(self.t_an, text="Performance Analysis")
        nb.bind("<<NotebookTabChanged>>", lambda e: self.refresh())
        self.build_members(); self.build_tx(); self.build_analysis()
        self.refresh()

    def build_members(self):
        f = ttk.Frame(self.t_mem); f.pack(fill="x", pady=6)
        self.name, self.phone, self.village = tk.StringVar(), tk.StringVar(), tk.StringVar()
        for lbl, var in (("Name", self.name), ("Phone", self.phone), ("Village", self.village)):
            ttk.Label(f, text=lbl).pack(side="left", padx=(8, 2))
            ttk.Entry(f, textvariable=var, width=16).pack(side="left")
        ttk.Button(f, text="Add member", command=self.add_member).pack(side="left", padx=8)
        cols = ("ID", "Name", "Phone", "Village", "Balance (UGX)")
        self.tv_mem = ttk.Treeview(self.t_mem, columns=cols, show="headings")
        for c in cols:
            self.tv_mem.heading(c, text=c); self.tv_mem.column(c, width=140)
        self.tv_mem.pack(fill="both", expand=True)

    def build_tx(self):
        f = ttk.Frame(self.t_tx); f.pack(fill="x", pady=6)
        self.mid, self.amt = tk.StringVar(), tk.StringVar()
        ttk.Label(f, text="Member ID").pack(side="left", padx=(8, 2))
        ttk.Entry(f, textvariable=self.mid, width=6).pack(side="left")
        ttk.Label(f, text="Amount").pack(side="left", padx=(8, 2))
        ttk.Entry(f, textvariable=self.amt, width=12).pack(side="left")
        ttk.Button(f, text="Deposit", command=lambda: self.tx("deposit")).pack(side="left", padx=6)
        ttk.Button(f, text="Withdraw", command=lambda: self.tx("withdraw")).pack(side="left")
        cols = ("ID", "Member", "Type", "Amount", "Time")
        self.tv_tx = ttk.Treeview(self.t_tx, columns=cols, show="headings")
        for c in cols:
            self.tv_tx.heading(c, text=c); self.tv_tx.column(c, width=150)
        self.tv_tx.pack(fill="both", expand=True)

    def build_analysis(self):
        self.txt = tk.Text(self.t_an, font=("Courier", 11), state="disabled")
        self.txt.pack(fill="both", expand=True)

    def add_member(self):
        try:
            self.s.add_member(self.name.get(), self.phone.get(), self.village.get())
            self.name.set(""); self.phone.set(""); self.village.set("")
            self.refresh()
        except SaccoError as e:
            messagebox.showerror("Error", str(e))

    def tx(self, kind):
        try:
            bal = getattr(self.s, kind)(int(self.mid.get()), int(self.amt.get()))
            messagebox.showinfo("Done", f"New balance: {bal:,} UGX")
            self.refresh()
        except ValueError:
            messagebox.showerror("Error", "Enter a numeric member ID and whole-number amount.")
        except SaccoError as e:
            messagebox.showerror("Error", str(e))

    def refresh(self):
        for tv in (self.tv_mem, self.tv_tx):
            tv.delete(*tv.get_children())
        for r in self.s.members():
            self.tv_mem.insert("", "end", values=(r["id"], r["name"], r["phone"], r["village"], f"{r['balance']:,}"))
        for r in self.s.statement():
            self.tv_tx.insert("", "end", values=(r["id"], r["name"], r["type"], f"{r['amount']:,}", r["ts"]))
        a = self.s.analysis()
        lines = [f"Members            : {a['members']}",
                 f"Total deposits     : {a['total_deposits']:,} UGX",
                 f"Total withdrawals  : {a['total_withdrawals']:,} UGX",
                 f"Net savings        : {a['net_savings']:,} UGX",
                 f"Average balance    : {a['average_balance']:,} UGX",
                 f"Savings retention  : {a['retention_ratio']}%", "", "Top savers:"]
        lines += [f"  {i}. {n:<18}{b:>12,} UGX" for i, (n, b) in enumerate(a["top_savers"], 1)]
        lines += ["", "Monthly flow (deposits / withdrawals):"]
        lines += [f"  {m}   {d:>10,}  /  {w:>10,}" for m, d, w in a["monthly"]]
        self.txt.config(state="normal"); self.txt.delete("1.0", "end")
        self.txt.insert("end", "\n".join(lines)); self.txt.config(state="disabled")


if __name__ == "__main__":
    App().mainloop()
