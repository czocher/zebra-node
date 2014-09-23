#! /usr/bin/env python
#-*- coding: utf8 -*-
from test import Test
from settings import TASK_BACKEND, TEST_BACKEND, SUPERVISOR_HOST, NODE_KEY, NODE_NAME, \
    REST_URL_PREFIX
from rest import RESTConnection
from StringIO import StringIO
from httplib import HTTPException
from time import time
import os
import xml.dom.minidom
import tarfile
import logging


class Task(object):
    """Class represents single task. It is define by tid and contains test for task, limit of execution time and memory limit"""
    def __init__(self, tid):
        self.connection = RESTConnection(SUPERVISOR_HOST, NODE_NAME, NODE_KEY)
        self.tid = tid
        self.tests = {}
        self.timeStamp = [0, 0, 0]
        self.lastUseTime = time()
        self.getTask()

    def __downloadTests(self, timeStamp):
        """Download all tests for this particular task"""
        if TEST_BACKEND == "file":
            for dummy, dummy, files in os.walk("tests/in/" + str(self.tid) + "/"):
                for fil in files:
                    with open("tests/in/" + str(self.tid) + "/" + fil) as fileIn, open("tests/ref/" + str(self.tid) + "/" + fil) as fileRef:
                        tIn = fileIn.read()
                        tRef = fileRef.read()
                        tmp = Test(tIn, tRef)
                        self.tests.append(tmp)
        elif TEST_BACKEND == "http":
            testIn = None
            testOut = None
            testConf = None
            try:
                self.connection.GET(REST_URL_PREFIX + "problem/" + str(self.tid) + "/tests/")
                dom = xml.dom.minidom.parseString(self.connection.response)
                if (timeStamp[0] != self.timeStamp[0]):
                    self.connection.GET(dom.getElementsByTagName("in")[0].childNodes[0].data, notXML=True)
                    testIn = StringIO(self.connection.response)
                if (timeStamp[1] != self.timeStamp[1]):
                    self.connection.GET(dom.getElementsByTagName("out")[0].childNodes[0].data, notXML=True)
                    testOut = StringIO(self.connection.response)
                if (timeStamp[2] != self.timeStamp[2]):
                    self.connection.GET(dom.getElementsByTagName("conf")[0].childNodes[0].data, notXML=True)
                    testConf = StringIO(self.connection.response)
            except HTTPException:
                logging.error("Tests not avaliable")
                raise
            except IndexError:
                logging.warn("Wrong answer from supervisor - tests")
            try:
                tarOut = tarfile.open(fileobj=testOut, mode="r:gz")
                del testOut
            except:
                tarOut = None
            try:
                tarIn = tarfile.open(fileobj=testIn, mode="r:gz")
                del testIn
            except:
                tarIn = None
            try:
                tarConf = tarfile.open(fileobj=testConf, mode="r:gz")
                del testConf
            except:
                tarConf = None
            tarFor = tarIn
            if tarIn == None:
                if tarOut == None:
                    tarFor = tarConf
                else:
                    tarFor = tarOut
            for tarinfo in tarFor:
                try:
                    if tarinfo.name not in self.tests:
                        tIn = tarIn.extractfile(tarinfo.name).read()
                        tRef = tarOut.extractfile(tarinfo.name).read()
                        tConf = tarConf.extractfile(tarinfo.name).read()
                        dom = xml.dom.minidom.parseString(tConf)
                        tmp = Test(tIn, tRef, int(dom.getElementsByTagName("memory")[0].childNodes[0].data), float(dom.getElementsByTagName("time")[0].childNodes[0].data), int(dom.getElementsByTagName("sample")[0].childNodes[0].data))
                        del tIn
                        del tRef
                        del tConf
                        self.tests[tarinfo.name] = tmp
                    else:
                        if tarIn != None:
                            self.tests[tarinfo.name].input = tarIn.extractfile(tarinfo.name).read()
                        if tarOut != None:
                            self.tests[tarinfo.name].reference = tarOut.extractfile(tarinfo.name).read()
                        if tarConf != None:
                            dom = xml.dom.minidom.parseString(tarConf.extractfile(tarinfo.name).read())
                            self.tests[tarinfo.name].memoryLimit = int(dom.getElementsByTagName("memory")[0].childNodes[0].data)
                            self.tests[tarinfo.name].timeLimit = float(dom.getElementsByTagName("time")[0].childNodes[0].data)
                            self.tests[tarinfo.name].sampleTest = int(dom.getElementsByTagName("sample")[0].childNodes[0].data)
                except Exception:
                    logging.exception("Error during test fetching.")
                    raise
            if tarIn != None:
                tarIn.close()
                del tarIn
            if tarOut != None:
                tarOut.close()
                del tarOut
            if tarConf != None:
                tarConf.close()
                del tarConf
        elif TEST_BACKEND == "S3":
            raise NotImplementedError

    def __downloadTimeStamp(self):
        timeStamp = []
        if TASK_BACKEND == "file":
            with open("tests/conf/" + str(self.tid) + "/timestampIN") as fileIN, open("tests/conf/" + str(self.tid) + "/timestampOUT") as fileOUT, open("tests/conf/" + str(self.tid) + "/timestampCONF") as fileCONF:
                timeStamp.append(int(fileIN.read()))
                timeStamp.append(int(fileOUT.read()))
                timeStamp.append(int(fileCONF.read()))
            return timeStamp
        elif TASK_BACKEND == "supervisor":
            try:
                self.connection.GET(REST_URL_PREFIX + "problem/" + str(self.tid) + "/")
            except HTTPException:
                logging.error("Error during fetching timestamp - supervisor")
                raise
            dom = xml.dom.minidom.parseString(self.connection.response)
            try:
                timeStamp.append(int(dom.getElementsByTagName("in")[0].childNodes[0].data))
                timeStamp.append(int(dom.getElementsByTagName("out")[0].childNodes[0].data))
                timeStamp.append(int(dom.getElementsByTagName("conf")[0].childNodes[0].data))
                return timeStamp
            except IndexError:
                logging.warn("Wrong answer from supervisor - timestamp")
                return Exception

    def getTask(self):
        """Download all necessary data if their are not up to date and return task"""
        timeStamp = self.__downloadTimeStamp()
        if timeStamp != self.timeStamp:
            try:
                self.__downloadTests(timeStamp)
                self.timeStamp = timeStamp
            except HTTPException:
                raise
        self.lastUseTime = time()
        return self
