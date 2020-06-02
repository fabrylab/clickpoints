#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ChangeTracker.py

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

import re
from typing import List, Tuple, Union

import peewee
import qtawesome as qta
from peewee import SqliteDatabase
from qtpy import QtWidgets, QtGui

from clickpoints.includes.BigImageDisplay import BigImageDisplay
from clickpoints.includes.Database import DataFileExtended
from clickpoints.includes.Tools import BroadCastEvent


class undo:
    active = 0
    first_log = 1
    frozen = -1

    undo_stack = None
    redo_stack = None

    next_text = ""

    def __init__(self, db: SqliteDatabase, tables: List[str]) -> None:
        # store the database and the tables
        self.db = db
        self.tables = tables

    def activate(self) -> None:
        """
        Start up the undo/redo system
        """
        # already active? do nothing
        if self.active:
            return
        # create the triggers to log changes
        self._create_triggers()
        # initialize the stacks
        self.undo_stack = []
        self.redo_stack = []
        # initialize the variables
        self.active = 1
        self.frozen = -1
        # start the first undo interval
        self._start_interval()

    def deactivate(self) -> None:
        """
        Halt the undo/redo system and delete the undo/redo stacks
        """
        # not active? do nothing
        if not self.active:
            return
        # delete the triggers from the database
        self._drop_triggers()
        # remove the stacks
        self.undo_stack = None
        self.redo_stack = None
        # reset the variables
        self.active = 0
        self.frozen = -1

    def freeze(self):
        """
        Stop accepting database changes into the undo stack

        From the point when this routine is called up until the next unfreeze,
        new database changes are rejected from the undo stack.
        """
        # if the recording is frozen, do nothing
        if self.frozen >= 0:
            return
        # get the current index from the undo log
        self.frozen = self._get_last_index()

    def unfreeze(self) -> None:
        """
        Begin accepting undo actions again.
        """
        # if the recording is not frozen, do nothing
        if self.frozen < 0:
            return
        # delete the recorded changes during the frozen period
        self.db.execute_sql("DELETE FROM undolog WHERE seq > ?", (self.frozen,))
        # reset the frozen variable
        self.frozen = -1

    def barrier(self, text: str = "") -> None:
        """
        Create an undo barrier right now.
        """
        # get the index of the last recorded change
        end = self._get_last_index()
        # if there were some changes recorded during the freezing, omit those
        if 0 <= self.frozen < end:
            end = self.frozen
        # the beginning is the stored first index
        begin = self.first_log
        # start a new undo interval
        self._start_interval()
        # if the beginning of the undo is the same as the current index, no changes occurred since the last barrier
        if begin == self.first_log:
            self.refresh()
            return
        # add the interval to the undo stack, together with the optional descriptive text
        self.undo_stack.append((begin, end, text))
        # delete the redo stack
        self.redo_stack = []
        # refresh the gui
        self.refresh()

    def __call__(self, text: str = "") -> "undo":
        self.next_text = text
        return self

    def __enter__(self) -> None:
        """
        Enter an undo context where every changes is gathered into an undo interval
        """
        pass

    def __exit__(self, exc_type: None, exc_val: None, exc_tb: None) -> None:
        """
        Exit an undo context and an undo barrier
        """
        self.barrier(self.next_text)
        self.next_text = ""

    def undo(self) -> None:
        """
        Do a single step of undo
        """
        self._step(self.undo_stack, self.redo_stack)

    def redo(self) -> None:
        """
        Redo a single step
        """
        self._step(self.redo_stack, self.undo_stack)

    def get_state(self) -> Union[Tuple[str, str], Tuple[str, None]]:
        """
        Get the text for the last undo and redo command, or None if it is not available
        """
        try:
            undo = self.undo_stack[-1][2]
        except IndexError:
            undo = None

        try:
            redo = self.redo_stack[-1][2]
        except IndexError:
            redo = None
        return undo, redo

    def refresh(self):
        """
        Update the status of controls after a database change

        The undo module calls this routine after any undo/redo in order to
        cause controls gray out appropriately depending on the current state
        of the database. This routine works by invoking the status_refresh
        module in all top-level namespaces.
        """
        pass

    def reload_all(self) -> None:
        """
        Redraw everything based on the current database

        The undo module calls this routine after any undo/redo in order to
        cause the screen to be completely redrawn based on the current database
        contents. This is accomplished by calling the "reload" module in
        every top-level namespace other than ::undo.
        """
        pass

    def status_refresh(self):
        """
        Enable and/or disable menu options a buttons
        """
        pass

    def _create_triggers(self) -> None:
        """
        Create change recording triggers for all tables listed

        Create a temporary table in the database named "undolog". Create triggers that fire on any insert, delete, or
        update of TABLE1, TABLE2, .... When those triggers fire, insert records in undolog that contain SQL text for
        statements that will undo the insert, delete, or update.
        """
        # delete a potential previous undo log table
        try:
            self.db.execute_sql('DROP TABLE undolog')
        except peewee.OperationalError:
            pass
        # create a new undo log table
        self.db.execute_sql('CREATE TEMP TABLE undolog(seq integer primary key, sql text)')

        # iterate over the tables to track
        for tbl in self.tables:
            # get a list of all columns
            collist = self.db.execute_sql('pragma table_info({tbl})'.format(tbl=tbl)).fetchall()

            # create a trigger for insert commands on the table
            sql = "CREATE TEMP TRIGGER _{tbl}_it AFTER INSERT ON {tbl} BEGIN\n"
            sql += "  INSERT INTO undolog VALUES(NULL,"
            sql += "'DELETE FROM {tbl} WHERE rowid='||new.rowid);\nEND\n"
            # add the trigger
            self.db.execute_sql(sql.format(tbl=tbl))

            # create a trigger for update commands on the table
            sql = "CREATE TEMP TRIGGER _{tbl}_ut AFTER UPDATE ON {tbl} BEGIN\n"
            sql += "  INSERT INTO undolog VALUES(NULL,"
            sql += "'UPDATE {tbl} "
            # add a set with the old values
            sep = "SET "
            for x1, name, x2, x3, x4, x5 in collist:
                sql += "{sep}{name}='||quote(old.{name})||'".format(sep=sep, name=name)
                sep = ","
            sql += " WHERE rowid='||old.rowid);\nEND\n"
            # add the trigger
            self.db.execute_sql(sql.format(tbl=tbl))

            # create a trigger for delete commands on the table
            sql = "CREATE TEMP TRIGGER _{tbl}_dt BEFORE DELETE ON {tbl} BEGIN\n"
            sql += "  INSERT INTO undolog VALUES(NULL,"
            sql += "'INSERT INTO {tbl}(rowid"
            # add a set with the old values
            for x1, name, x2, x3, x4, x5 in collist:
                sql += "," + name
            sql += ") VALUES('||old.rowid||'"
            for x1, name, x2, x3, x4, x5 in collist:
                sql += ",'||quote(old.{name})||'".format(name=name)
            sql += ")');\nEND\n"
            # add the trigger
            self.db.execute_sql(sql.format(tbl=tbl))

    def _drop_triggers(self) -> None:
        """
        Drop all of the triggers that _create_triggers created.
        """
        # get the list of triggers
        trigger_list = self.db.execute_sql("SELECT name FROM sqlite_temp_master WHERE type='trigger'").fetchall()

        # iterate over all triggers
        for trigger, in trigger_list:
            # if the trigger is named in the form e.g. _marker_it
            if re.match(r"_.*_", trigger):
                # remove the trigger
                self.db.execute_sql("DROP TRIGGER {trigger}".format(trigger=trigger))

        # drop the undo log table
        try:
            self.db.execute_sql('DROP TABLE undolog')
        except peewee.OperationalError:
            pass

    def _start_interval(self) -> None:
        """
        Record the starting conditions of an undo interval
        """
        self.first_log = self._get_last_index() + 1

    def _step(self, stack_source: List[Tuple[int, int, str]], stack_target: List[Tuple[int, int, str]]) -> None:
        """
        Do a single step of undo or redo

        For an undo stack_source = self.undo_stack and stack_target = self.redo_stack.
        For a redo, stack_source = self.redo_stack and stack_target = self.undo_stack.
        """
        # pop begin and end from the current stack
        begin, end, text = stack_source.pop(-1)

        # get the list of sql commands to revert the action
        sql_list = self.db.execute_sql("SELECT sql FROM undolog WHERE seq>=? AND seq<=? ORDER BY seq DESC",
                                       (begin, end)).fetchall()

        # delete these entries from the undo log
        self.db.execute_sql("DELETE FROM undolog WHERE seq>=? AND seq<=?", (begin, end))

        # find the new first entry
        self.first_log = self._get_last_index() + 1

        # execute all commands to revert the action
        with self.db.atomic():
            for sql, in sql_list:
                self.db.execute_sql(sql)

        # reload all stuff that depends on the database
        self.reload_all()

        # get the new end and beginning
        end = self._get_last_index()
        begin = self.first_log

        # add them to the other stack
        stack_target.append((begin, end, text))
        # start a new action interval
        self._start_interval()
        # refresh the gui
        self.refresh()

    def _get_last_index(self) -> int:
        # get the index of the most recent entry to the undo log
        return self.db.execute_sql("SELECT coalesce(max(seq),0) FROM undolog").fetchone()[0]


class ChangeTracker:
    data_file = None
    config = None

    undo = None

    def __init__(self, window: "ClickPointsWindow", modules: List[BigImageDisplay]) -> None:
        # store some references
        self.window = window
        self.modules = modules

        # a undo button
        self.button_undo = QtWidgets.QPushButton()
        self.button_undo.setIcon(qta.icon("fa.undo"))
        self.button_undo.clicked.connect(self.do_undo)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Z"), self.window).activated.connect(self.do_undo)
        self.window.layoutButtons.addWidget(self.button_undo)

        # a button to display/hide the mask interface
        self.button_redo = QtWidgets.QPushButton()
        self.button_redo.setIcon(qta.icon("fa.repeat"))
        self.button_redo.clicked.connect(self.do_redo)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Y"), self.window).activated.connect(self.do_redo)
        self.window.layoutButtons.addWidget(self.button_redo)

        self.closeDataFile()

    def closeDataFile(self) -> None:
        if self.undo is not None:
            self.undo.deactivate()

        self.data_file = None
        self.config = None

        self.button_undo.setDisabled(True)
        self.button_redo.setDisabled(True)

    def updateDataFile(self, data_file: DataFileExtended, new_database: bool) -> None:
        self.data_file = data_file
        self.config = data_file.getOptionAccess()

        self.undo = undo(self.data_file.db, ["mask"])
        self.undo.activate()
        self.undo.refresh = self.updateState

    def do_undo(self) -> None:
        if self.undo.get_state()[0] is not None:
            self.undo.undo()
            BroadCastEvent(self.modules, "imageLoadedEvent", "", 0)

    def do_redo(self) -> None:
        if self.undo.get_state()[1] is not None:
            self.undo.redo()
            BroadCastEvent(self.modules, "imageLoadedEvent", "", 0)

    def updateState(self) -> None:
        undo, redo = self.undo.get_state()
        self.button_undo.setDisabled(undo is None)
        if undo is not None:
            self.button_undo.setToolTip("undo: " + undo)
        else:
            self.button_undo.setToolTip(undo)
        self.button_redo.setDisabled(redo is None)
        if redo is not None:
            self.button_redo.setToolTip("redo: " + redo)
        else:
            self.button_redo.setToolTip(redo)

    def __call__(self, *args, **kwargs) -> undo:
        return self.undo(*args, **kwargs)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.closeDataFile()
