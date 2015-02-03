import threading
from subprocess import Popen
from time import time


class Command(object):
    """Run the given command in a separate process
    and it kill if time limit was exceeded."""

    def __init__(self, cmd, *args, **kwargs):
        self.cmd = cmd
        self.args = args
        self.kwargs = kwargs
        self.output = None
        self.returncode = None
        self.process = None

    def run(self, input, timeLimit):
        def target():
            self.process = Popen(self.cmd, *self.args, **self.kwargs)
            self.output = self.process.communicate(input)

        thread = threading.Thread(target=target)
        start_time = time()
        thread.start()
        thread.join(timeout=timeLimit)
        if thread.is_alive():
            self.process.kill()
            thread.join()
        end_time = time()
        self.time = end_time - start_time
        self.returncode = self.process.returncode

    def __repr__(self):
        return 'Command({})'.format(self.cmd)
