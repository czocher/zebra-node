#! /usr/bin/env python
#-*- coding: utf8 -*-
from judge import Judge
from utils import get_free_memory
from task import Task
from settings import NODE
from rest import RESTConnection, UnauthorizedException, NotFoundException
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

    def judge(self, submission):
        logging.info(
            "Starting to judge submission: "
            "id {id} pid {problem} language {language}.".format(**submission)
        )
        task = self.get_task(submission['problem'])
        judge = Judge(task, submission)

        judge.start()
        judge.join()

        logging.info("Judging of submission {id} finished.".format(
            **submission
        ))

        return (judge.results, judge.compilation_log)

    def post_results(self, results, submission):

        logging.info("Sending the judging results.")

        results, compilelog = results

        data = {
            'error': False,
            'compilelog': escape(compilelog),
            'results': [result.__dict__ for result in results]
        }

        RESTConnection.post_submission(submission['id'], data)

    def report_judging_error(self, submission):
        logging.info("Reporting the error...")
        RESTConnection.post_submission(submission['id'], {'error': True, })

    def run(self):
        """Start the Node daemon. Try to judge a submission
        then sleep and repeat."""

        logging.info("Node has been started.")

        while True:
            try:
                submission = RESTConnection.get_submission()
            except NotFoundException:
                # No submissions then wait and retry
                logging.info("No submission to judge. Waiting...")
                sleep(NODE['QUERY_TIME'])
                continue
            except UnauthorizedException:
                # Session expired or node was unauthorized retry
                logging.warning("Node unauthorized. Waiting...")
                sleep(NODE['QUERY_TIME'])
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
                try:
                    self.post_results(results, submission)
                except Exception as e:
                    logging.error(
                        "There was an error during judging: {}".format(e)
                    )
                    self.report_judging_error(submission)


            # Sleep for a few seconds waiting for a next turn
            logging.info("Waiting for next request.")
            sleep(NODE['QUERY_TIME'])
