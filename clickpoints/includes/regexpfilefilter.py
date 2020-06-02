#!/usr/bin/env python
# -*- coding: utf-8 -*-
# regexpfilefilter.py

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

import glob, re, os
import natsort

# input values:
# regexp string of time stamps
# filter dictionary
#
# filtparam = {}
# filtparam.update({'regexp':r".*(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})-(?P<hour>\d{2})(?P<minute>\d{2})(?P<second>\d{2})"})
# filtparam.update({'filterlist':[[FILTER_InList, "hour", [12,13,14]], [FILTER_First, "hour"]]})
# filtparam.update({'keyranking':["second", "minute", "hour", "day", "month", "year"]})

# # TESTBLOCK
# srcpath='/media/fox/ATKASPOT_DATA_1_/campbell/2013/04/03/'
#
# files = glob.glob(os.path.join(srcpath,"*-*.jpg"))
# files = natsort.natsorted(files)
# fl=[]
# for file in files:
#     path,fname=os.path.split(file)
#     fl.append(fname)
# files=fl



# FILTER definitions
last_re_dict = None
def FILTER_First(re_dict, key):
    global last_re_dict
    if last_re_dict is None:
        last_re_dict = re_dict
        return True
    if key in key_ranking:
        for key2 in key_ranking[key_ranking.index(key):]:
            if last_re_dict[key2] != re_dict[key2]:
                last_re_dict = re_dict
                return True
    return False

def FILTER_InRange(re_dict, key, start, stop):
    if start < int(re_dict[key]) < stop:
        return True
    return False

def FILTER_InList(re_dict, key, number_list):
    if int(re_dict[key]) in number_list:
        return True
    return False

skip_filter_count = -1
def FILTER_Skip(re_dict, number):
    global skip_filter_count
    skip_filter_count += 1
    if skip_filter_count % number == 0:
        return True
    return False

def FILTER_Tag(re_dict, tag):
    if re_dict["filename"][-len(tag):] == tag:
        return False
    return True

# Filter class
class regexpfilefilter:
    def __init__(self,filter_param={}):
        #def values
        self.re_string = r""#r".*(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})-(?P<hour>\d{2})(?P<minute>\d{2})(?P<second>\d{2})"
        self.key_ranking = ["second", "minute", "hour", "day", "month", "year"]
        self.filters = [[FILTER_InList, "hour", [12,13,14]], [FILTER_First, "hour"]] #[FILTER_Skip, 1]]
        self.filters = [ [FILTER_First, "hour"]] #[FILTER_Skip, 1]]
        self.reg = None

        #get parameter from dict
        if 'regexp' in filter_param:
            self.re_string = filter_param['regexp']
            self.reg = re.compile(self.re_string)
        if 'filterlist' in filter_param:
            self.filters = filter_param['filterlist']
        if 'keyranking' in filter_param:
            self.key_ranking = filter_param['keyranking']

        #hack
        global key_ranking
        key_ranking = self.key_ranking

    def file_filter(self,re_dict):
        for filter in self.filters:
            if filter[0](re_dict, *filter[1:]) is False:
                return False
        return True

    def apply_filter(self,files):
        used_files = []
        for file in files:
            if self.reg is not None:
                match = self.reg.match(file)
                if not match:
                    continue
                re_dict = match.groupdict()
            else:
                re_dict = {}
            re_dict["filename"] = file
            if self.file_filter(re_dict):
                used_files.append(file)

        return used_files

