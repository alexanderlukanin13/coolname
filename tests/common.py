import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).parent
PROJECT_DIR = TESTS_DIR.parent
EXAMPLES_DIR = PROJECT_DIR / 'examples'
DATA_DIR = TESTS_DIR / 'data'
COOLNAME_DATA_DIR = PROJECT_DIR / 'src' / 'coolname' / 'data'


class TestCase(unittest.TestCase):
    pass


class FakeRandom:
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
