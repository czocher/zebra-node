#! /usr/bin/env python
#-*- coding: utf8 -*-
from judge import Judge
from utils import get_free_memory
from task import Task
from settings import NODE
from rest import RESTConnection, UnauthorizedException, \
    SessionExpiredException, NotFoundException
from time import time, sleep
from xml.sax.saxutils import escape
import logging


class Node(object):
    """Manage the connection to the Supervisor and process judge requests."""

    def __init__(self):
        self.tasks = dict()

    def get_task(self, pid):
        """Check if a task with specified problem id is already in tasks
        dictionary and if not get it."""

        if pid not in self.tasks:
            self.tasks[pid] = Task.new(pid)
        while get_free_memory() < NODE['MAX_MEMORY'] and len(self.tasks) > 1:
            minTime = time()
            lru = None
            for task in self.tasks:
                if self.tasks[task].lastUseTime < minTime:
                    minTime = self.tasks[task].lastUseTime
                    lru = task
            del self.tasks[lru]
        task = self.tasks[pid]
        task.lastUseTime = time()
        return task

    def authenticate(self):
        """Authenticate with the Supervisor."""

        while True:
            try:
                RESTConnection.get_session()
            except UnauthorizedException:
                # If not authorized by the Supervisor slee and retry
                logging.warning("Retrying in {} seconds.".format(
                    NODE['QUERY_TIME']
                ))
                sleep(NODE['QUERY_TIME'])
                continue
            # Else return
            RESTConnection.post_report()
            break

    def judge(self, submission):
        logging.info(
            "Starting to judge submission: "
            "sid {sid} pid {pid} language {language}.".format(**submission)
        )

        task = self.get_task(submission['pid'])
        judge = Judge(task, submission)

        judge.start()
        judge.join()
        logging.info("Judging of submission {sid} finished.".format(
            **submission
        ))

        return (judge.get_results(), judge.get_compilation_log())

    def post_results(self, results, submission):

        logging.info("Sending the judging results.")

        results, compilelog = results

        data = {
            'status': 1,
            'compilelog': escape(compilelog),
            'results': {'result': [result.__dict__ for result in results]}
        }

        RESTConnection.post_submission(submission['sid'], data)

    def report_judging_error(self, submission):
        logging.info("Reporting the error...")
        RESTConnection.post_submission(submission['sid'], {'status': 0, })

    def run(self):
        """Start the Node daemon. Try to judge a submission
        then sleep and repeat."""

        logging.info("Node has been started.")

        self.authenticate()

        while True:
            try:
                submission = RESTConnection.get_submission()
            except NotFoundException:
                # No submissions then wait and retry
                logging.info("No submission to judge. Waiting...")
                sleep(NODE['QUERY_TIME'])
                continue
            except (SessionExpiredException, UnauthorizedException):
                # Session expired or node was unauthorized retry
                self.authenticate()
                continue

            try:
                results = self.judge(submission)
            except Exception as e:
                logging.error(
                    "There was an error during judging: {}".format(e)
                )
                self.report_judging_error(submission)
            except KeyboardInterrupt:
                logging.info("Node termination requested.")
                self.report_judging_error(submission)
                raise
            else:
                self.post_results(results, submission)

            # Sleep for a few seconds waiting for a next turn
            logging.info("Waiting for next request.")
            sleep(NODE['QUERY_TIME'])
