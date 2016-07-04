from __future__ import print_function
import clickpoints
import os

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

db = clickpoints.DataFile("tmp.cdb", "w")
db.db.get_conn().row_factory = dict_factory

with open("schema.sql", "w") as fp:
    for row in db.db.execute_sql("SELECT * FROM sqlite_master ORDER BY type DESC, name").fetchall():
        fp.write(row["sql"]+";\n")
db.db.close()

os.remove("tmp.cdb")
