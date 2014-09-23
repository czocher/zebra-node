#! /usr/bin/env python
#-*- coding: utf8 -*-


class Result(object):
    """Result for one test. Contain return code, is solution valid and time of execution"""
    def __init__(self, a, b, c):
        self.statusCode = a
        self.result = b
        self.time = c

    def __repr__(self):
        return str(self.statusCode) + " " + str(self.result) + " " + str(self.time)
