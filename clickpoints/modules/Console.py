#!/usr/bin/env python
# -*- coding: utf-8 -*-
# InfoHud.py

# Copyright (c) 2015-2016, Richard Gerum, Sebastian Richter
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ClickPoints. If not, see <http://www.gnu.org/licenses/>

from __future__ import division, print_function

from qtpy import QtCore, QtGui, QtWidgets
import qtawesome as qta

import sys
from includes import GetHooks


class Console(QtWidgets.QTextEdit):
    update_normal = QtCore.Signal(str)
    update_error = QtCore.Signal(str)

    def __init__(self, window):
        QtWidgets.QTextEdit.__init__(self)
        self.window = window
        self.setHidden(True)

        w = QtWidgets.QWidget()
        w.setLayout(self.window.layout)

        self.last_html = False

        l = QtWidgets.QHBoxLayout(self.window)
        l.setContentsMargins(0, 0, 0, 0)
        self.splitter = QtWidgets.QSplitter()
        l.addWidget(self.splitter)
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.splitter.addWidget(w)

        font = QtGui.QFont("Miriam Fixed", 10)
        self.setReadOnly(True)
        self.setFont(font)
        self.setTextColor(QtGui.QColor(192, 192, 192))
        self.setStyleSheet("QTextEdit { background-color: rgb(0, 0, 0); }")
        self.text_string = ""

        self.setWindowIcon(qta.icon("fa.terminal"))
        self.setWindowTitle("Log - ClickPoints")

        self.splitter.addWidget(self)

        self.update_normal.connect(self.add_text)
        self.update_error.connect(self.add_textE)

    def keyPressEvent(self, event):
        # @key ---- Modules ----
        # @key Q: open the console
        if event.key() == QtCore.Qt.Key_Q and not event.modifiers() & QtCore.Qt.ControlModifier:
            self.setVisible(not self.isVisible())
        # @key Cntrl+Q: detach the console
        if event.key() == QtCore.Qt.Key_Q and event.modifiers() & QtCore.Qt.ControlModifier:
            if self.parent() is None:
                self.splitter.addWidget(self)
            else:
                self.setParent(None)
                self.setGeometry(self.x(), self.y(), 500, 300)
                self.show()
            self.setVisible(True)

    def log(self, *args, **kwargs):
        text = " ".join([str(arg) for arg in args])+kwargs.get("end", "\n")
        self.update_normal.emit(text)

    def add_textE(self, text, clear=False):
        self.insertHtml("<p style='color: #ff6b68'>"+text.replace("\n", "<br/>").replace(" ", "&nbsp;")+"</p>")#<p style='color: #c0c0c0'></p>")
        c = self.textCursor()
        c.movePosition(QtGui.QTextCursor.End)
        self.setTextCursor(c)

    def add_text(self, text, clear=False):
        self.insertHtml("<p style='color: #c0c0c0'>" + text.replace("\n", "<br/>").replace(" ", "&nbsp;") + "</p>")  # <p style='color: #c0c0c0'></p>")
        c = self.textCursor()
        c.movePosition(QtGui.QTextCursor.End)
        self.setTextCursor(c)

    def closeEvent(self, QCloseEvent):
        self.close()

    @staticmethod
    def file():
        return __file__
