# -*- coding: utf-8 -*-
from functools import partial
from itertools import cycle
import unittest

import six
from six import u

import coolname
from coolname import RandomNameGenerator, InitializationError
from coolname.loader import load_config

from .common import patch, TestCase


class TestCoolname(TestCase):

    def test_slug(self):
        # Basic test, to check that it doesn't crash.
        # Output of default generator is always unicode.
        items = coolname.generate()
        self.assertIsInstance(items[0], six.text_type)
        name = coolname.generate_slug()
        self.assertIsInstance(name, six.text_type)
        self.assertGreater(len(name), 10)
        self.assertIn('-', name)

    def test_combinations(self):
        combinations_2 = 10**5
        combinations_3 = 10**8
        combinations_4 = 10**10
        self.assertGreater(coolname.get_combinations_count(), combinations_4)
        self.assertGreater(coolname.get_combinations_count(2), combinations_2)
        self.assertGreater(coolname.get_combinations_count(3), combinations_3)
        self.assertGreater(coolname.get_combinations_count(4), combinations_4)
        self.assertLess(coolname.get_combinations_count(3),
                        coolname.get_combinations_count())
        self.assertLess(coolname.get_combinations_count(4),
                        coolname.get_combinations_count())
        self.assertEqual(coolname.get_combinations_count(2) +
                         coolname.get_combinations_count(3) +
                         coolname.get_combinations_count(4),
                         coolname.get_combinations_count())

    @patch('os.path.isdir', return_value=False)
    @patch('os.path.isfile', return_value=False)
    def test_create_from_file_not_found(self, *args):
        with self.assertRaisesRegex(InitializationError,
                                    r'File or directory not found: .*dummy'):
            RandomNameGenerator(load_config('dummy'))

    @patch('os.path.isdir', return_value=False)
    @patch('os.path.isfile', return_value=True)
    @patch('coolname.loader._load_config')
    def test_create_from_file(self, load_config_mock, *args):
        load_config_mock.return_value = {
            'all': {
                'type': 'cartesian',
                'lists': ['number', 'number']
            },
            'number': {
                'type': 'words',
                'words': [str(x) for x in range(0, 10)]
            }
        }
        generator = RandomNameGenerator(load_config('dummy'))
        with patch('coolname.impl.randrange', return_value=35):
            self.assertEqual(generator.generate_slug(), '3-5')

    @patch('os.path.isdir', return_value=True)
    @patch('os.path.isfile', return_value=False)
    @patch('coolname.loader._load_data')
    def test_create_from_directory_conflict(self, load_data_mock, *args):
        load_data_mock.return_value = (
            {
                'all': {
                    'type': 'cartesian',
                    'lists': ['mywords']
                },
                'mywords': {
                    'type': 'words',
                    'words': ['this', 'is', 'a', 'conflict']
                }
            },
            {'mywords': ['a', 'b']})
        with self.assertRaisesRegex(InitializationError,
                                    r"^Conflict: list 'mywords' is defined both in config "
                                    "and in \*\.txt file. If it's a 'words' list, "
                                    "you should remove it from config\.$"):
            RandomNameGenerator(load_config('dummy'))

    def test_generate_by_pattern(self):
        generator = RandomNameGenerator({
            'all': {
                'type': 'cartesian',
                'lists': ['size', 'color', 'fruit'],
            },
            'justcolor': {
                'generator': True,
                'type': 'cartesian',
                'lists': ['color', 'fruit'],
            },
            'size': {
                'type': 'words',
                'words': ['small', 'large']
            },
            'color': {
                'type': 'words',
                'words': ['green', 'yellow']
            },
            'fruit': {
                'type': 'words',
                'words': ['apple', 'banana']
            },
        })
        with patch('coolname.impl.randrange', return_value=0):
            self.assertEqual(generator.generate_slug(), 'small-green-apple')
            self.assertEqual(generator.generate_slug('justcolor'), 'green-apple')

    def test_unicode_config(self):
        generator = RandomNameGenerator({
            u('all'): {
                u('type'): u('cartesian'),
                u('lists'): [u('прилагательное'), u('существительное')]
            },
            u('прилагательное'): {
                u('type'): u('words'),
                u('words'): [u('белый'), u('черный')]
            },
            u('существительное'): {
                u('type'): u('words'),
                u('words'): [u('круг'), u('квадрат')]
            }
        })
        with patch('coolname.impl.randrange',
                   side_effect=partial(next, cycle(iter(range(4))))):
            self.assertEqual(generator.generate_slug(), u('белый-круг'))
            self.assertEqual(generator.generate_slug(), u('белый-квадрат'))
            self.assertEqual(generator.generate_slug(), u('черный-круг'))
            self.assertEqual(generator.generate(), [u('черный'), u('квадрат')])

    def test_avoid_repeating(self):
        generator = RandomNameGenerator({
            'all': {
                'type': 'cartesian',
                'lists': ['adjective', 'of', 'noun'],
            },
            'adjective': {
                'type': 'words',
                'words': ['one', 'two']
            },
            'of': {
                'type': 'const',
                'value': 'of'
            },
            'noun': {
                'type': 'words',
                'words': ['one', 'two']
            }
        })
        with patch('coolname.impl.randrange',
                   side_effect=partial(next, cycle(iter([0, 1, 2, 3])))):
            self.assertEqual(generator.generate_slug(), 'one-of-two')
            self.assertEqual(generator.generate_slug(), 'two-of-one')
            self.assertEqual(generator.generate_slug(), 'one-of-two')

    def test_avoid_similar_words(self):
        generator = RandomNameGenerator({
            'all': {
                'type': 'cartesian',
                'lists': ['w1', 'w2'],
            },
            'w1': {
                'type': 'words',
                'words': ['brave', 'agile']
            },
            'w2': {
                'type': 'words',
                'words': ['bravery',  'brass', 'agility', 'age']
            }
        })
        with patch('coolname.impl.randrange',
                   side_effect=partial(next, cycle(iter(range(9))))):
            self.assertEqual(generator.generate_slug(), 'brave-brass')
            self.assertEqual(generator.generate_slug(), 'brave-agility')
            self.assertEqual(generator.generate_slug(), 'brave-age')
            self.assertEqual(generator.generate_slug(), 'agile-bravery')
            self.assertEqual(generator.generate_slug(), 'agile-brass')
            self.assertEqual(generator.generate_slug(), 'agile-age')
            self.assertEqual(generator.generate_slug(), 'brave-brass')

    def test_configuration_error(self):
        with self.assertRaisesRegex(InitializationError,
                                    "Invalid config: Value at key 'all' is not a dict"):
            RandomNameGenerator({'all': ['wrong']})
        with self.assertRaisesRegex(InitializationError,
                                    "Invalid config: Config at key 'all' has no 'type'"):
            RandomNameGenerator({'all': {'typ': 'wrong'}})
        with self.assertRaisesRegex(InitializationError,
                                    "Invalid config: Config at key 'all' has invalid 'type'"):
            RandomNameGenerator({'all': {'type': 'wrong'}})
        with self.assertRaisesRegex(InitializationError,
                                    "Invalid config: Config at key 'all' has no 'lists'"):
            RandomNameGenerator({'all': {'type': 'nested'}})
        with self.assertRaisesRegex(InitializationError,
                                    "Invalid config: Config at key 'all' has invalid 'lists'"):
            RandomNameGenerator({'all': {'type': 'nested', 'lists': 'wrong'}})
        with self.assertRaisesRegex(InitializationError,
                                    "Invalid config: Config at key 'all' has no 'value'"):
            RandomNameGenerator({'all': {'type': 'const'}})
        with self.assertRaisesRegex(InitializationError,
                                    "Invalid config: Config at key 'all' has invalid 'value'"):
            RandomNameGenerator({'all': {'type': 'const', 'value': 123}})
        with self.assertRaisesRegex(InitializationError,
                                    "Invalid config: Config at key 'all' has no 'words'"):
            RandomNameGenerator({'all': {'type': 'words'}})
        with self.assertRaisesRegex(InitializationError,
                                    "Invalid config: Config at key 'all' has invalid 'words'"):
            RandomNameGenerator({'all': {'type': 'words', 'words': []}})
        with self.assertRaisesRegex(InitializationError,
                                    "Invalid config: Lists are referenced but not defined: one, two"):
            RandomNameGenerator({'all': {'type': 'nested', 'lists': ['one', 'two']}})
        with self.assertRaisesRegex(InitializationError,
                                   "Invalid config: Rule 'all' is recursive: \['all', 'one'\]"):
            RandomNameGenerator({
                'all': {'type': 'nested', 'lists': ['one']},
                'one': {'type': 'nested', 'lists': ['all']}
            })

    def test_configuration_error_too_deep(self):
        config = {
            'all': {
                'type': 'nested',
                'lists': ['list0']
            },
            'list100': {
                'type': 'words',
                'words': ['too', 'deep', 'for', 'you'],
            }
        }
        for i in range(100):
            config['list{}'.format(i)] = {'type': 'nested', 'lists': ['list{}'.format(i+1)]}
        with self.assertRaisesRegex(InitializationError,
                                    "Invalid config: Rule 'all' is too deep"):
            RandomNameGenerator(config)


    @patch('coolname.impl.randrange', side_effect=partial(next, cycle(iter(range(8)))))
    def test_configuration_error_cartesian_inside_cartesian(self, mock):
        config = {
            'all': {
                'type': 'cartesian',
                'lists': ['word_list', 'cart_list']
            },
            'word_list': {
                'type': 'words',
                'words': ['word1', 'word2'],
            },
            'cart_list': {
                'type': 'cartesian',
                'lists': ['word_list', 'word_list'],
            },
        }
        with self.assertRaisesRegex(InitializationError,
                                    r"Invalid config: Cartesian list 'all' contains "
                                    r"another Cartesian list 'cart_list'\. Nested Cartesian lists "
                                    r"are not allowed\."):
            RandomNameGenerator(config)

if __name__ == '__main__':
    import sys
    sys.exit(unittest.main())
