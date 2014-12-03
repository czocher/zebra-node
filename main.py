#!/usr/bin/env python
# -*- coding: utf-8 -*-
from node import Node
from sandbox import Sandbox
import locale
import logging
import sys

# Set the default locale for dates and times in logs
locale.setlocale(locale.LC_ALL, '')

FORMAT = '%(asctime)s - %(levelname)s - [%(module)s.%(funcName)s] %(message)s'

logging.basicConfig(
    level=logging.DEBUG,
    format=FORMAT,
    datefmt='%c'
)

if __name__ == '__main__':
    # Test if the chosen sandbox can run on this system
    with Sandbox.new() as sandbox:
        sandbox.test_sandbox()

    # Start the Node
    try:
        node = Node()
        node.run()
    except KeyboardInterrupt:
        logging.info("Node successfully terminated.")
        sys.exit(0)
