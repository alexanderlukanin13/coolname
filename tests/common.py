import binascii
import unittest
import six


try:
    from unittest import mock
    from unittest.mock import patch
except ImportError:
    import mock
    from mock import patch


class TestCase(unittest.TestCase):
    pass


if six.PY2:
    def assertRaisesRegex(self, *args, **kwargs):
        return six.assertRaisesRegex(self, *args, **kwargs)
    TestCase.assertRaisesRegex = assertRaisesRegex


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
