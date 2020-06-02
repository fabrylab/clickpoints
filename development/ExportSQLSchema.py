#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ExportSQLSchema.py

# Copyright (c) 2015-2020, Richard Gerum, Sebastian Richter, Alexander Winterl
#
# This file is part of ClickPoints.
#
# ClickPoints is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ClickPoints is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ClickPoints. If not, see <http://www.gnu.org/licenses/>

from __future__ import print_function
import clickpoints
import os

# to get query results as dictionaries
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

# create a temporary ClickPoints table
db = clickpoints.DataFile("tmp.cdb", "w")
# enable dictionaries as query results
db.db.connection().row_factory = dict_factory

# open schema.sql
with open("schema.sql", "w") as fp:
    # get al entries in the database table schema
    for row in db.db.execute_sql("SELECT * FROM sqlite_master").fetchall():
        # write the sql commends to the file
        fp.write(row["sql"]+";\n")

    # query and write the version of the database
    row = db.db.execute_sql("SELECT * FROM meta WHERE key='version'").fetchone()
    fp.write("INSERT OR REPLACE INTO meta (id,key,value) VALUES\
            ((SELECT id FROM meta WHERE key='version'),'version',%s);\n" % row["value"])
# close the database
db.db.close()
# delete the temporary database
os.remove("tmp.cdb")
