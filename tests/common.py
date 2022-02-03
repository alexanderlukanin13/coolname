import os.path as op
import unittest
from unittest import mock
from unittest.mock import patch

TESTS_DIR = op.dirname(op.abspath(__file__))
PROJECT_DIR = op.abspath(op.join(TESTS_DIR, '..'))
EXAMPLES_DIR = op.join(PROJECT_DIR, 'examples')


class TestCase(unittest.TestCase):
    pass


class FakeRandom(object):
    """Generates 0, 1, 2..."""

    def __init__(self, i=0):
        self.i = i

    def randrange(self, stop):
        result = (self.i + 1) % stop
        self.i += 1
        return result

    def seed(self, a):
        assert isinstance(a, int)
        self.i = a
