#!/usr/bin/env python
# -*- coding: utf-8 -*-
# AnnotationHandler.py

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

from __future__ import division, print_function

from qtpy import QtGui, QtCore, QtWidgets
from qtpy.QtCore import Qt
import qtawesome as qta

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "includes"))
from clickpoints.includes.Tools import BroadCastEvent
import peewee
from datetime import datetime
import sqlite3


# enables .access on dicts
class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    def __getattr__(self, attr):
        return self.get(attr)
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class AnnotationFile:
    def __init__(self, datafile, server=None):
        self.data_file = datafile
        self.server = server

        if server:
            class BaseModel(peewee.Model):
                class Meta:
                    database = server
            base_model = BaseModel
        else:
            base_model = datafile.base_model

        if server:
            class SqlAnnotation(base_model):
                timestamp = peewee.DateTimeField(null=True)
                reffilename = peewee.CharField()
                reffileext = peewee.CharField()
                file_id = peewee.IntegerField(null=True)
                comment = peewee.TextField(default="")
                rating = peewee.IntegerField(default=0)
                tag_type = peewee.CharField(default="SQLTags")
                frame = peewee.IntegerField()
                #system = peewee.IntegerField(null=True)
                #device = peewee.IntegerField(null=True)
            self.table_annotation = SqlAnnotation

            class Tags(base_model):
                name = peewee.CharField()

            class Tagassociation(base_model):
                annotation = peewee.ForeignKeyField(self.table_annotation)
                tag = peewee.ForeignKeyField(Tags)

            self.table_tag = Tags
            self.table_tagassociation = Tagassociation
        else:
            self.table_annotation = self.data_file.table_annotation
            self.table_tag = self.data_file.table_tag
            self.table_tagassociation = self.data_file.table_tagassociation

        if not self.server:
            self.data_file._tables.extend([self.table_annotation, self.table_tag, self.table_tagassociation])
            for table in [self.table_annotation, self.table_tag, self.table_tagassociation]:
                if not table.table_exists():
                    table.create_table()

        self.annotation = None

    def add_annotation(self, **kwargs):
        if self.server:
            kwargs.update(dict(timestamp=self.data_file.timestamp, reffilename=self.data_file.image.filename, reffileext=self.data_file.image.ext, file_id=self.data_file.image.external_id, frame=self.data_file.image.frame))
        else:
            kwargs.update(dict(timestamp=self.data_file.timestamp, image=self.data_file.image))
        self.annotation = self.table_annotation(**kwargs)
        return self.annotation

    def remove_annotation(self, annotation):
        self.table_tagassociation.delete().where(self.table_tagassociation.annotation == annotation.id).execute()
        annotation.delete_instance()

    def getAnnotation(self):
        try:
            if self.server:
                if self.data_file.current_reference_image.external_id is not None:
                    self.annotation = self.table_annotation.get(file_id=self.data_file.current_reference_image.external_id, frame=self.data_file.current_reference_image.frame)
                else:
                    self.annotation = self.table_annotation.get(self.table_annotation.reffilename == self.data_file.current_reference_image.filename)
            else:
                self.annotation = self.table_annotation.get(self.table_annotation.image == self.data_file.current_reference_image.id)
        except peewee.DoesNotExist:
            self.annotation = None
        return self.annotation

    def getTagList(self):
        return [tag.name for tag in self.table_tag.select()]

    def getTagsFromAnnotation(self):
        return [tag.name for tag in self.table_tag.select().join(self.table_tagassociation).join(self.table_annotation).where(self.table_annotation.id == self.annotation)]

    def setTags(self, tags):
        if len(tags):
            # Add new tags
            if self.server or sqlite3.sqlite_version_info[1] < 8:  # MySQL has no WITH statements :-(
                for tag in tags:
                    try:
                        self.table_tag.get(self.table_tag.name == tag)
                    except peewee.DoesNotExist:
                        self.table_tag(name=tag).save()
            else:
                query = self.table_tag.raw("WITH check_tags(name) AS ( VALUES %s ) SELECT check_tags.name, tag.id FROM check_tags LEFT JOIN tag ON check_tags.name = tag.name" % ",".join('("%s")' % x for x in tags))
                new_tags = [dict(name=tag.name) for tag in query if tag.id is None]
                if len(new_tags):
                    self.table_tag.insert_many(new_tags).execute()
            # Get ids of tags
            query = self.table_tag.select().where(self.table_tag.name << tags)
            ids = [tag.id for tag in query]
            # Delete unused old tag associations
            self.table_tagassociation.delete().where(~ self.table_tagassociation.id << ids, self.table_tagassociation.annotation == self.annotation).execute()
            # Add new associations
            query = self.table_tagassociation.select().where(self.table_tagassociation.annotation == self.annotation)
            current_ids = [a.tag_id for a in query]
            new_tag_associations = [dict(tag=id, annotation=self.annotation.id) for id in ids if id not in current_ids]
            if len(new_tag_associations):
                self.table_tagassociation.insert_many(new_tag_associations).execute()
        else:
            # Delete all old tag associations
            self.table_tagassociation.delete().where(self.table_tagassociation.annotation == self.annotation).execute()


    def get_annotation_frames(self):
        if self.server:
            return self.table_annotation.select()
        return self.table_annotation.select()

    def getAnnotationsByIds(self, id_list):
        # are the annotations on the server?
        if self.server is not None:
            # get the server data
            query = (self.table_annotation.select(peewee.SQL("t1.id as id"), peewee.SQL("t1.timestamp as timestamp"),
                                                peewee.SQL("t1.comment as comment"),
                                                peewee.SQL("t1.reffilename as image_filename"),
                                                peewee.SQL("t1.file_id as image_id"),
                                                peewee.SQL("t1.rating as rating"),
                                                peewee.SQL("GROUP_CONCAT(t3.name) as tags"))
                     .where(self.table_annotation.id << id_list)
                     .join(self.table_tagassociation, join_type="LEFT JOIN")
                     .join(self.table_tag, join_type="LEFT JOIN")
                     .group_by(self.table_annotation.id))
            annotations = [q for q in query]
            # new query on local database to the the sort_index
            query = (self.data_file.table_image.select(self.data_file.table_image.sort_index, self.data_file.table_image.external_id)
                     .where(self.data_file.table_image.external_id << [q.image_id for q in annotations]))
            id_to_sort_index = {q.external_id: q.sort_index for q in query}
            # add the sort index to the query data
            for annotation in annotations:
                annotation.image_sort_index = id_to_sort_index[annotation.image_id]
            # return composed annotations
            return annotations
        db = self.data_file
        # no server? than we can use a direct query with join
        query = (db.table_annotation.select(db.table_annotation.id, db.table_annotation.timestamp,
                                        db.table_annotation.comment,
                                        db.table_image.filename.alias("image_filename"),
                                        db.table_image.sort_index.alias("image_sort_index"),
                                        db.table_annotation.image_id, db.table_annotation.rating,
                                        peewee.fn.GROUP_CONCAT(db.table_tag.name).alias("tags"))
             # .where(db.table_annotation.id << id_list)
             .join(db.table_tagassociation, join_type="LEFT")
             .join(db.table_tag, join_type="LEFT")
             .group_by(db.table_annotation.id)
             .switch(db.table_annotation)
             .join(db.table_image))
        query = [dotdict(item) for item in query.dicts()]
        return query

class pyQtTagSelector(QtWidgets.QWidget):
    class unCheckBox(QtWidgets.QCheckBox):
        def __init__(self, parent, name):
            super(QtWidgets.QCheckBox, self).__init__(parent)
            self.name = name
            self.parent = parent

            self.setText(self.name)
            self.setChecked(True)
            self.toggled.connect(self.hCB_remove)

            # add to list of currently used tags
            self.parent.list.append(str(name))

        def hCB_remove(self):
            # remove from tag list
            self.parent.list.remove(self.name)

            # delete icon
            self.deleteLater()

    def __init__(self, parent=None, add_button=True):
        super(QtWidgets.QWidget, self).__init__(parent)

        self.cbTag = QtWidgets.QComboBox(self)
        self.cbTag.addItems([''])
        self.cbTag.setInsertPolicy(QtWidgets.QComboBox.InsertAtBottom)
        self.cbTag.setEditable(True)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(1)
        self.cbTag.setSizePolicy(sizePolicy)
        self.cbTag.activated.connect(self.hPB_add)

        if add_button:
            self.pbAdd = QtWidgets.QPushButton(self)
            self.pbAdd.setIcon(qta.icon("fa.plus"))
            self.pbAdd.setMaximumWidth(30)
            self.pbAdd.released.connect(self.hPB_add)
        else:
            self.cbTag.setInsertPolicy(QtWidgets.QComboBox.NoInsert)

        self.layout_main = QtWidgets.QVBoxLayout()
        self.layout_main.setAlignment(Qt.AlignTop)
        self.layout_tag = QtWidgets.QHBoxLayout()
        self.layout_list = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout_main)
        self.layout_main.addLayout(self.layout_tag)
        self.layout_main.addLayout(self.layout_list)
        self.layout_tag.addWidget(self.cbTag)

        if add_button:
            self.layout_tag.addWidget(self.pbAdd)

        self.layout_main.setContentsMargins(0, 0, 0, 0)

        self.list = []

    def setText(self, string):
        self.cbTag.setEditText(string)

    def setStringList(self, string_list):
        self.cbTag.addItems(string_list)

    def setActiveTagList(self, string_list):
        for tag in string_list:
            # on add create checked checkbox
            cb = self.unCheckBox(self, tag)
            self.layout_list.addWidget(cb)

    def getTagList(self):
        return self.list

    def hPB_add(self):
        name = self.cbTag.currentText()
        # check if already in list
        if name not in self.list and not name == '':
            # on add create checked checkbox
            cb = self.unCheckBox(self, self.cbTag.currentText())
            self.layout_list.addWidget(cb)


class AnnotationEditor(QtWidgets.QWidget):
    def __init__(self, annotation_handler, filename, filenr, db, modules, config):
        QtWidgets.QWidget.__init__(self)

        # default settings and parameters
        self.annotation_handler = annotation_handler
        self.db = db
        self.modules = modules
        self.config = config

        self.annotation = self.db.getAnnotation()
        if self.annotation is None:
            self.annotation = self.db.add_annotation()
            exists = False
        else:
            exists = True

        # widget layout and elements
        self.setMinimumWidth(650)
        self.setMinimumHeight(400)
        self.setWindowTitle("Edit Annotation - ClickPoints")
        self.setWindowIcon(qta.icon("fa.file-text-o"))
        self.layout = QtWidgets.QGridLayout(self)

        self.layout.addWidget(QtWidgets.QLabel('Filename:'), 0, 0)
        self.leAName = QtWidgets.QLineEdit(filename, self)
        self.leAName.setEnabled(False)
        self.layout.addWidget(self.leAName, 0, 1, 1, 3)

        self.laTag = QtWidgets.QLabel('Tag:', self)
        self.laTag.setContentsMargins(0, 4, 0, 0)
        self.layout.addWidget(self.laTag, 4, 0, Qt.AlignTop)

        self.leTag = pyQtTagSelector()
        self.layout.addWidget(self.leTag, 4, 1)

        self.laRating = QtWidgets.QLabel('Rating:', self)
        self.laRating.setContentsMargins(0, 4, 0, 0)
        self.layout.addWidget(self.laRating, 4, 2, Qt.AlignTop)
        self.leRating = QtWidgets.QComboBox(self)
        for index, text in enumerate(['0 - none', '1 - bad', '2', '3', '4', '5 - good']):
            self.leRating.insertItem(index, text)
        self.leRating.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        self.leRating.setContentsMargins(0, 5, 0, 0)
        self.layout.addWidget(self.leRating, 4, 3, Qt.AlignTop)

        self.pbConfirm = QtWidgets.QPushButton('S&ave', self)
        self.pbConfirm.pressed.connect(self.saveAnnotation)
        self.layout.addWidget(self.pbConfirm, 0, 4)

        self.pbDiscard = QtWidgets.QPushButton('&Cancel', self)
        self.pbDiscard.pressed.connect(self.close)
        self.layout.addWidget(self.pbDiscard, 1, 4)

        if exists:
            self.pbRemove = QtWidgets.QPushButton('&Remove', self)
            self.pbRemove.pressed.connect(self.removeAnnotation)
            self.layout.addWidget(self.pbRemove, 4, 4, Qt.AlignTop)

        self.pbOverview = QtWidgets.QPushButton('Show Overview', self)
        self.pbOverview.pressed.connect(self.annotation_handler.showAnnotationOverview)
        self.layout.addWidget(self.pbOverview, 5, 4, Qt.AlignTop)

        self.pteAnnotation = QtWidgets.QPlainTextEdit(self)
        self.pteAnnotation.setFocus()
        self.layout.addWidget(self.pteAnnotation, 5, 0, 5, 4)

        # fill gui entries
        #if self.config.server_annotations is True:
            #self.leTStamp.setText(self.annotation.timestamp)
            #self.leSystem.setText(self.annotation.system)
            #self.leCamera.setText(self.annotation.camera)
        #if self.annotation.timestamp:
        #    self.leTStamp.setText(datetime.strftime(self.annotation.timestamp, '%Y%m%d-%H%M%S'))
        if self.annotation.rating:
            self.leRating.setCurrentIndex(self.annotation.rating)
        self.leRating.currentIndexChanged.connect(lambda x: setattr(self.annotation, "rating", x))
        if self.annotation.comment:
            self.pteAnnotation.setPlainText(self.annotation.comment)
        self.pteAnnotation.textChanged.connect(lambda: setattr(self.annotation, "comment", self.pteAnnotation.toPlainText()))

        # update active tags
        self.leTag.setStringList(db.getTagList())
        self.leTag.setActiveTagList(db.getTagsFromAnnotation())

    def saveAnnotation(self):
        # save the annotation
        self.db.annotation.save()
        # update tag association table
        self.db.setTags(self.leTag.getTagList())
        self.db.annotation.tags = ",".join(self.leTag.getTagList())
        self.close()
        BroadCastEvent(self.modules, "AnnotationAdded", self.db.annotation)
        # set the database changed flag
        self.db.data_file.setChangesMade()

    def removeAnnotation(self):
        self.annotation_handler.db.remove_annotation(self.annotation)
        BroadCastEvent(self.modules, "AnnotationRemoved", self.db.annotation)
        self.close()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.close()
        if event.key() == QtCore.Qt.Key_S and event.modifiers() & Qt.ControlModifier:
            self.saveAnnotation()


class AnnotationOverview(QtWidgets.QWidget):
    def __init__(self, window, config, annoation_ids, db):
        QtWidgets.QWidget.__init__(self)

        # widget layout and elements
        self.setMinimumWidth(700)
        self.setMinimumHeight(300)
        self.setWindowTitle('Annotations Overview - ClickPoints')
        self.setWindowIcon(qta.icon("fa.list"))
        self.layout = QtWidgets.QGridLayout(self)
        self.annoation_ids = annoation_ids
        self.window = window
        self.config = config
        self.db = db

        self.table = QtWidgets.QTableWidget(0, 7, self)
        self.table.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        self.table.setHorizontalHeaderLabels(['Date', 'Tag', 'Comment', 'R', 'image', 'image_frame', 'id'])
        self.table.hideColumn(4)
        self.table.hideColumn(5)
        self.table.hideColumn(6)
        try:  # Qt5
            self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
            self.table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        except AttributeError:  # Qt4
            self.table.horizontalHeader().setResizeMode(QtWidgets.QHeaderView.ResizeToContents)
            self.table.horizontalHeader().setResizeMode(2, QtWidgets.QHeaderView.Stretch)
        self.table.verticalHeader().hide()
        self.layout.addWidget(self.table)

        self.table.doubleClicked.connect(self.JumpToAnnotation)

        for index, annotation in enumerate(self.db.getAnnotationsByIds(self.annoation_ids)):
            # populate table
            annotation.id = self.annoation_ids[index]
            self.UpdateRow(index, annotation)

        # fit column to context
        self.table.resizeColumnToContents(0)
        self.table.sortByColumn(0, Qt.AscendingOrder)

    def JumpToAnnotation(self, idx):
        # get file basename
        image_index = int(self.table.item(idx.row(), 5).text())

        self.window.JumpToFrame(image_index)

    def UpdateRow(self, row, annotation, sort_if_new=False):
        new = False
        if self.table.rowCount() <= row:
            self.table.insertRow(self.table.rowCount())
            for j in range(7):
                self.table.setItem(row, j, QtWidgets.QTableWidgetItem())
            new = True
        if self.config.server_annotations is True:
            filename = annotation.reffilename
        else:
            filename = annotation.image_filename
        if annotation.tags is None:
            annotation.tags = ""
        if annotation.timestamp is not None and annotation.timestamp:
            timestamp = datetime.strftime(annotation.timestamp, '%Y%m%d-%H%M%S')
        else:
            timestamp = ""
        #if self.config.server_annotations is True:
        #    image = self.window.data_file.table_image.get(external_id = annotation.file_id, frame=annotation.frame)
        #else:
        #    image = annotation.image
        texts = [timestamp, annotation.tags, annotation.comment, str(annotation.rating), filename, str(annotation.image_sort_index), str(annotation.id)]
        for index, text in enumerate(texts):
            self.table.item(row, index).setText(text)
        if new and sort_if_new:
            self.table.sortByColumn(0, Qt.AscendingOrder)

    def AnnotationAdded(self, annotation):
        row = self.table.rowCount()
        for i in range(self.table.rowCount()):
            if int(self.table.item(i, 6).text()) == annotation.id:
                row = i
                break
        self.UpdateRow(row, annotation, sort_if_new=True)

    def AnnotationRemoved(self, annotation):
        for i in range(self.table.rowCount()):
            if int(self.table.item(i, 6).text()) == annotation.id:
                self.table.removeRow(i)
                break

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.close()


class AnnotationHandler:
    data_file = None
    config = None

    def __init__(self, window, modules):
        # default settings and parameters
        self.window = window
        self.modules = modules

        self.button_annotationEditor = QtWidgets.QPushButton()
        self.button_annotationEditor.setIcon(qta.icon("fa.edit"))
        self.button_annotationEditor.setToolTip("add/edit annotation for current frame")
        self.button_annotationEditor.clicked.connect(self.showAnnotationEditor)
        self.window.layoutButtons.addWidget(self.button_annotationEditor)

        self.AnnotationEditorWindow = None
        self.AnnotationOverviewWindow = None

        self.closeDataFile()

    def closeDataFile(self):
        self.data_file = None
        self.config = None

        self.annoation_ids = []

        if self.AnnotationEditorWindow:
            self.AnnotationEditorWindow.close()
        if self.AnnotationOverviewWindow:
            self.AnnotationOverviewWindow.close()

    def updateDataFile(self, data_file, new_database):
        self.data_file = data_file
        self.config = data_file.getOptionAccess()

    def LoadingFinishedEvent(self):
        if self.config.server_annotations:
            import peewee
            self.server = peewee.MySQLDatabase(self.config.sql_dbname,
                                               host=self.config.sql_host,
                                               port=self.config.sql_port,
                                               user=self.config.sql_user,
                                               passwd=self.config.sql_pwd)
            self.db = AnnotationFile(self.data_file, self.server)

            # place tick marks for already present masks
            for item in self.db.get_annotation_frames():
                try:
                    image = self.data_file.table_image.get(external_id=item.file_id, frame=item.frame)
                    BroadCastEvent(self.modules, "AnnotationMarkerAdd", image.sort_index)
                    self.annoation_ids.append(item.id)
                except peewee.DoesNotExist:
                    pass

        else:
            self.data_file = self.data_file
            self.db = AnnotationFile(self.data_file)

            # place tick marks for already present masks
            for item in self.db.get_annotation_frames():
                BroadCastEvent(self.modules, "AnnotationMarkerAdd", item.image.sort_index)
                self.annoation_ids.append(item.id)

    def AnnotationAdded(self, annotation):
        if annotation.id not in self.annoation_ids:
            self.annoation_ids.append(annotation.id)
        if self.AnnotationOverviewWindow:
            self.AnnotationOverviewWindow.AnnotationAdded(annotation)

    def AnnotationRemoved(self, annotation):
        self.annoation_ids.remove(annotation.id)
        if self.AnnotationOverviewWindow:
            self.AnnotationOverviewWindow.AnnotationRemoved(annotation)

    def showAnnotationEditor(self):
        if self.data_file is None or self.data_file.current_reference_image is None:
            reply = QtWidgets.QMessageBox.warning(self.window, 'Warning', 'To add an annotation to an image, '
                                                                   'an image has to be loaded.')
            return
        if self.AnnotationEditorWindow is not None:
            self.AnnotationEditorWindow.close()
            del self.AnnotationEditorWindow
        self.AnnotationEditorWindow = AnnotationEditor(self, self.data_file.current_reference_image.filename,
                                                           self.data_file.current_reference_image, self.db,
                                                           modules=self.modules, config=self.config)
        self.AnnotationEditorWindow.show()

    def showAnnotationOverview(self):
        self.AnnotationOverviewWindow = AnnotationOverview(self.window, self.config, self.annoation_ids, self.db)
        self.AnnotationOverviewWindow.show()

    def keyPressEvent(self, event):
        # @key A: add/edit annotation
        if event.key() == Qt.Key_A:
            self.showAnnotationEditor()

        # @key Y: show annotation overview
        if event.key() == Qt.Key_Y:
            self.showAnnotationOverview()

    def closeEvent(self, event):
        if self.AnnotationEditorWindow:
            self.AnnotationEditorWindow.close()
        if self.AnnotationOverviewWindow:
            self.AnnotationOverviewWindow.close()

    @staticmethod
    def file():
        return __file__
