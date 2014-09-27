#! /usr/bin/env python
#-*- coding: utf8 -*-


class Result(object):
    """Result for one test. Contains the return code,
    mark and execution time"""

    def __init__(self, returncode, mark, time):
        self.returncode = returncode
        self.mark = mark
        self.time = time

    def __repr__(self):
        return "Result(returncode={}, mark={}, time={})".format(
            self.returncode, self.mark, self.time
        )
