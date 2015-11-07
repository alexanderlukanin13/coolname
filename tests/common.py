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
