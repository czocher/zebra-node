#-*- coding: utf8 -*-


class Test(object):
    """Class represents an input and reference output for a single test."""

    def __init__(self, *args, **kwargs):
        self.input = kwargs.get('input')
        self.output = kwargs.get('output')
        self.memoryLimit = kwargs.get('memoryLimit')
        self.timeLimit = kwargs.get('timeLimit')
        self.isSampleTest = kwargs.get('isSampleTest')

    def __repr__(self):
        out = "Test(input={}, output={}, memoryLimit={}, " \
                + "timeLimit={}, isSampleTest={})"
        return out.format(self.input.strip(), self.output.strip(),
                          self.memoryLimit, self.timeLimit, self.isSampleTest)
