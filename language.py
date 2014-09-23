#! /usr/bin/env python
#-*- coding: utf8 -*-


class Language(object):
    """Define programming language. Contain compiler name, compiler arguments and execution file"""
    def __init__(self, compiler, compilerArg, execution, filename):
        self.compiler = compiler
        self.compilerArg = compilerArg
        self.execution = execution
        self.fileName = filename
