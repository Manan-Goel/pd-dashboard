import sqlite3
from src.db.schema import SQL_DDL

print("Length of SQL_DDL:", len(SQL_DDL))
print("Last 200 chars of SQL_DDL:")
print(repr(SQL_DDL[-200:]))
