#! /usr/bin/env python
#-*- coding: utf8 -*-


class Test(object):
    """Class represents input and reference output for single test"""
    def __init__(self, input, reference, memoryLimit, timeLimit, sampleTest):
        self.input = input
        self.reference = reference
        self.memoryLimit = memoryLimit
        self.timeLimit = timeLimit
        self.sampleTest = sampleTest
