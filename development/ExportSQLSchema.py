from __future__ import print_function
import peewee

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

db = peewee.SqliteDatabase(r"D:\Repositories\ClickPointsExamples\PlantRoot\Test_MaskHandler_Test_MaskHandler_test_brushSizeMask.db_mask.png\test.cdb")
db.get_conn().row_factory = dict_factory

with open("schema.sql", "w") as fp:
    for row in db.execute_sql("SELECT * FROM sqlite_master ORDER BY tbl_name;").fetchall():
        fp.write(row["sql"]+"\n")
