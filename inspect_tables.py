import sqlite3

conn = sqlite3.connect("life_insurance.db")
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'fact_%'").fetchall()]
print("Fact tables in life_insurance.db:")
for t in tables:
    print(" -", t)
conn.close()
