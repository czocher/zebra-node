#! /usr/bin/env python
#-*- coding: utf8 -*-
from judge import Judge
from settings import SUPERVISOR_HOST, NODE_VERSION, NODE_KEY, NODE_NAME, REFRESH_TIME, REST_URL_PREFIX, MAX_MEMORY
from task import Task
from rest import RESTConnection, UnauthorizedException
from time import time, sleep
from xml.sax.saxutils import unescape, escape
from httplib import HTTPException
import logging
import xml.dom.minidom


logging.basicConfig(filename='example.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - ' + NODE_NAME + ' - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')


class Node(object):
    """Node supervisor. Manage connection to Supervisor and process judge requests"""
    def __init__(self):
        self.tasks = dict()
        self.connection = RESTConnection(SUPERVISOR_HOST, NODE_NAME, NODE_KEY)

    def memoryLeft(self):
        with open("/proc/meminfo", "r") as mem:
            total = int(mem.readline().split()[1])
            free = int(mem.readline().split()[1])
            buffers = int(mem.readline().split()[1])
            cached = int(mem.readline().split()[1])
            return free + cached

    def getTask(self, tid):
        """Check if task with specified task id is already in tasks dictionary.
        If not get it."""
        if tid not in self.tasks:
            self.tasks[tid] = Task(tid)
        while self.memoryLeft() < MAX_MEMORY and len(self.tasks) > 1:
            minTime = time()
            lru = None
            for task in self.tasks:
                if self.tasks[task].lastUseTime < minTime:
                    minTime = self.tasks[task].lastUseTime
                    lru = task
            del self.tasks[lru]
        task = self.tasks[tid].getTask()
        return task

    def judgeSubmission(self, sourceCode, language, tid, sampleTests):
        try:
            task = self.getTask(tid)
            judge = Judge(sourceCode, language, task, sampleTests)
        except HTTPException:
            return None
        except ValueError:
            return ["No public class found", []]
        judge.start()
        judge.join()
        return judge.getResults()

    def getSubmission(self):
        """Get a request to judge from Supervisor."""
        sid = -1
        result = None
        try:
            self.connection.GET(REST_URL_PREFIX + "submission/")
            dom = xml.dom.minidom.parseString(self.connection.response)
            if int(dom.getElementsByTagName("status")[0].childNodes[0].data) == 400:
                return False
        except HTTPException:
            return False
        except IndexError:
            logging.warn("Wrong answer from supervisor - get request")
        try:
            sid = int(dom.getElementsByTagName("sid")[0].childNodes[0].data)
            sourceCode = unescape(dom.getElementsByTagName("content")[0].childNodes[0].data)
            language = dom.getElementsByTagName("lang")[0].childNodes[0].data
            tid = int(dom.getElementsByTagName("pid")[0].childNodes[0].data)
            sampleTests = int(dom.getElementsByTagName("sample")[0].childNodes[0].data)
            logging.info("Start judging: sid " + str(sid) + " tid " + str(tid) + " lang " + language)
            result = self.judgeSubmission(sourceCode, language, tid, sampleTests)
            if result == None:
                return False
            return True
        except IndexError:
            logging.warn("Wrong answer from supervisor - get request")
        finally:
            self.returnSubmission(sid, result)

    def returnSubmission(self, sid, result):
        """Return results to Supervisor"""
        response = "<submission><sid>" + str(sid) + "</sid>"
        if result == None:
            response += "<status>200</status>"
        else:
            response += "<status>100</status>"
            response += "<compilelog>" + escape(result[0]) + "</compilelog>"
            response += "<results>"
            for res in result[1]:
                response += "<result>"
                response += "<returncode>" + str(res.statusCode) + "</returncode>"
                response += "<mark>" + str(int(res.result)) + "</mark>"
                response += "<time>" + str(res.time) + "</time>"
                response += "</result>"
            response += "</results>"
        response += "</submission>"
        try:
            self.connection.POST(REST_URL_PREFIX + "submission/", response)
            logging.info("Submission has been send")
        except HTTPException:
            logging.warning("Unable to send sumbission")

    def getAuthenticate(self):
        """Get a request to judge from Supervisor."""
        try:
            self.connection.POST(REST_URL_PREFIX + "node/", "<node><name>" + NODE_NAME + "</name><key>" + NODE_KEY + "</key><version>" + NODE_VERSION + "</version></node>")
            return True
        except HTTPException:
            logging.warning("Unable to send request for authenticate")
        except UnauthorizedException:
            try:
                dom = xml.dom.minidom.parseString(self.connection.response)
                if int(dom.getElementsByTagName("status")[0].childNodes[0].data) == 200:
                    return False
                else:
                    return True
            except IndexError:
                logging.warn("Wrong answer from supervisor - authenticate")
        return False

    def run(self):
        '''
        Start Node daemon. Try to judge a submission. After this attempt sleep for time specify at settings file
        '''
        logging.info("Node has been started")
        self.getAuthenticate()
        while True:
            try:
                if self.getSubmission() == True:
                    continue
                sleep(REFRESH_TIME)
            except UnauthorizedException:
                while self.getAuthenticate() == False:
                    sleep(REFRESH_TIME)
            except KeyboardInterrupt:
                logging.info("Node has been stoped")
                return
            except:
                logging.exception("Unknown error:")

if __name__ == '__main__':
    check = Node()
    check.run()
