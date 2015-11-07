# -*- coding: utf-8 -*-
import io
import unittest

import six

from coolname import RandomNameGenerator, InitializationError
from coolname.impl import NestedList, CartesianList, Scalar,\
    _create_lists, _encode, _create_default_generator

from .common import TestCase, patch


class TestImplementation(TestCase):

    def test_nested_list(self):
        # Note that lists are internally sorted
        nested_list = NestedList([[1, 2, 3],
                                  [4, 5],
                                  [6, 7, 8, 9]])
        self.assertEqual(len(nested_list), 9)
        self.assertEqual(nested_list[0], 6)
        self.assertEqual(nested_list[1], 7)
        self.assertEqual(nested_list[2], 8)
        self.assertEqual(nested_list[3], 9)
        self.assertEqual(nested_list[4], 1)
        self.assertEqual(nested_list[5], 2)
        self.assertEqual(nested_list[6], 3)
        self.assertEqual(nested_list[7], 4)
        self.assertEqual(nested_list[8], 5)

    def test_nested_list_out_of_range(self):
        nested_list = NestedList([[1, 2, 3],
                                  [4, 5]])
        self.assertEqual(nested_list[4], 5)
        with self.assertRaises(IndexError):
            nested_list[5]

    def test_carthesian_list(self):
        cart_list = CartesianList([[1, 2, 3], [4, 5], [6, 7, 8, 9]])
        self.assertEqual(len(cart_list), 24)
        self.assertEqual(cart_list[0], [1, 4, 6])
        self.assertEqual(cart_list[1], [1, 4, 7])
        self.assertEqual(cart_list[4], [1, 5, 6])
        self.assertEqual(cart_list[8], [2, 4, 6])
        self.assertEqual(cart_list[9], [2, 4, 7])
        self.assertEqual(cart_list[23], [3, 5, 9])
        # One more level of nesting
        cart_list = NestedList([
            CartesianList([[10, 11], [12, 13]]),
            CartesianList([[1, 2, 3], [4, 5], [6, 7, 8, 9]]),
        ])
        self.assertEqual(len(cart_list), 28)
        self.assertEqual(cart_list[0], [1, 4, 6])
        self.assertEqual(cart_list[23], [3, 5, 9])
        self.assertEqual(cart_list[24], [10, 12])
        self.assertEqual(cart_list[27], [11, 13])

    def test_scalar(self):
        self.assertTrue(Scalar(10).random(), 10)

    def test_str(self):
        nested_list = NestedList([
            CartesianList([[10, 11], [12, 13]]),
            CartesianList([[1, 2, 3], [4, 5], [6, 7, 8, 9]]),
        ])
        self.assertEqual(str(nested_list), 'NestedList(2, len=28)')
        cart_list = CartesianList([[1, 2, 3], [4, 5], [6, 7, 8, 9]])
        self.assertEqual(str(cart_list), 'CartesianList(3, len=24)')
        scalar = Scalar('10')
        self.assertEqual(str(scalar), "Scalar(value='10')")

    def test_dump_list(self):
        cart_list = NestedList([
            CartesianList([[10, 11], [12, 13]]),
            CartesianList([[1, 2, 3], [4, 5], [6, 7, 8, 9]]),
        ])
        stream = io.StringIO()
        cart_list._dump(stream)
        self.assertEqual(stream.getvalue(),
                         'NestedList(2, len=28)\n'
                         '  CartesianList(3, len=24)\n'
                         '    WordList([1, 2, 3], len=3)\n'
                         '    WordList([4, 5], len=2)\n'
                         '    WordList([6, 7, 8, ...], len=4)\n'
                         '  CartesianList(2, len=4)\n'
                         '    WordList([10, 11], len=2)\n'
                         '    WordList([12, 13], len=2)\n')

    def test_dump_generator(self):
        config = {
            'all': {
                'type': 'words',
                'words': ['one', 'two', 'three']
            }
        }
        generator = RandomNameGenerator(config)
        stream = io.StringIO()
        generator._dump(stream)
        self.assertEqual(stream.getvalue(),
                         "WordList(['one', 'two', 'three'], len=3)\n")

    def test_create_lists(self):
        # For the sake of coverage
        with self.assertRaisesRegex(InitializationError, r"Unknown list type: 'wrong'"):
            config = {
                'all': {'type': 'wrong'}
            }
            _create_lists(config, {}, 'all', [])

    def test_encode(self):
        # _encode must encode unicode strings
        self.assertEqual(_encode(six.u('привет')),
                         six.u('привет').encode('utf-8'))
        # _encode must return byte strings unchanged
        self.assertEqual(_encode(six.u('привет').encode('utf-8')),
                         six.u('привет').encode('utf-8'))

    @patch('os.path.isdir', return_value=False)
    def test_import_data_from_init_py(self, *args):
        generator = _create_default_generator()
        assert isinstance(generator.generate_slug(), six.text_type)


if __name__ == '__main__':
    import sys
    sys.exit(unittest.main())
