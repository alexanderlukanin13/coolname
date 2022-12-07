from functools import partial
from itertools import cycle
import random
import sys
import unittest
import warnings

import coolname
from coolname import RandomGenerator, InitializationError
from coolname.exceptions import ConfigurationError
from coolname.loader import load_config

from .common import patch, TestCase, FakeRandom


class TestCoolname(TestCase):

    def test_slug(self):
        # Basic test, to check that it doesn't crash.
        # Output of default generator is always unicode.
        items = coolname.generate()
        self.assertIsInstance(items[0], str)
        name = coolname.generate_slug()
        self.assertIsInstance(name, str)
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
            RandomGenerator(load_config('dummy'))

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
        generator = RandomGenerator(load_config('dummy'))
        with patch.object(generator, '_randrange', return_value=35):
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
            RandomGenerator(load_config('dummy'))

    def test_generate_by_pattern(self):
        generator = RandomGenerator({
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
        with patch.object(generator, '_randrange', return_value=0):
            self.assertEqual(generator.generate_slug(), 'small-green-apple')
            self.assertEqual(generator.generate_slug('justcolor'), 'green-apple')

    def test_unicode_config(self):
        generator = RandomGenerator({
            'all': {
                'type': 'cartesian',
                'lists': ['прилагательное', 'существительное']
            },
            'прилагательное': {
                'type': 'words',
                'words': ['белый', 'черный']
            },
            'существительное': {
                'type': 'words',
                'words': ['круг', 'квадрат']
            }
        })
        with patch.object(generator, '_randrange',
                   side_effect=partial(next, cycle(iter(range(4))))):
            self.assertEqual(generator.generate_slug(), 'белый-круг')
            self.assertEqual(generator.generate_slug(), 'белый-квадрат')
            self.assertEqual(generator.generate_slug(), 'черный-круг')
            self.assertEqual(generator.generate(), ['черный', 'квадрат'])

    def test_ensure_unique(self):
        # Test without ensure_unique - should yield repeats
        config = {
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
        }
        generator = RandomGenerator(config)
        with patch.object(generator, '_randrange',
                          side_effect=partial(next, cycle(iter([0, 1, 2, 3])))):
            self.assertEqual(generator.generate_slug(), 'one-of-one')
            self.assertEqual(generator.generate_slug(), 'one-of-two')
            self.assertEqual(generator.generate_slug(), 'two-of-one')
            self.assertEqual(generator.generate_slug(), 'two-of-two')
            self.assertEqual(generator.generate_slug(), 'one-of-one')
        # Invalid ensure_unique
        config['all']['ensure_unique'] = 'qwe'
        with self.assertRaisesRegex(ConfigurationError, "Invalid config: Invalid ensure_unique value: expected boolean, got 'qwe'"):
            RandomGenerator(config)
        # Test with ensure_unique
        config['all']['ensure_unique'] = True
        with warnings.catch_warnings(record=True) as w:
            generator = RandomGenerator(config)
            if len(w) > 0:
                assert len(w) == 1
                assert str(w[0].message) == 'coolname.generate() may be slow because a significant fraction of combinations contain repeating words and ensure_unique is set'
        with patch.object(generator, '_randrange',
                          side_effect=partial(next, cycle(iter([0, 1, 2, 3])))):
            self.assertEqual(generator.generate_slug(), 'one-of-two')
            self.assertEqual(generator.generate_slug(), 'two-of-one')
            self.assertEqual(generator.generate_slug(), 'one-of-two')
            self.assertEqual(generator.generate_slug(), 'two-of-one')

    def test_ensure_unique_error(self):
        config = {
            'all': {'type': 'cartesian', 'lists': ['one', 'one']},
            'one': {'type': 'words', 'words': ['one', 'one']}
        }
        RandomGenerator(config)  # this is fine
        config['all']['ensure_unique'] = True
        with self.assertRaisesRegex(ConfigurationError, r'Invalid config: Impossible to generate with ensure_unique'):
            RandomGenerator(config)

    def test_ensure_unique_error_on_list(self):
        config = {
            'all': {'type': 'cartesian', 'lists': ['one', 'two']},
            'bad': {'type': 'cartesian', 'generator': True, 'lists': ['one', 'one']},
            'one': {'type': 'words', 'words': ['one', 'one']},
            'two': {'type': 'words', 'words': ['two', 'two']}
        }
        RandomGenerator(config)  # this is fine
        config['all']['ensure_unique'] = True
        with self.assertRaisesRegex(ConfigurationError, r'Invalid config: Impossible to generate with ensure_unique'):
            RandomGenerator(config)


    def test_ensure_unique_prefix(self):
        config = {
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
        }
        generator = RandomGenerator(config)
        with patch.object(generator, '_randrange',
                          side_effect=partial(next, cycle(iter(range(8))))):
            self.assertEqual(generator.generate_slug(), 'brave-bravery')  # This sucks

        # ensure_unique_prefix = 0 is not allowed
        config['all']['ensure_unique_prefix'] = 0
        with self.assertRaisesRegex(ConfigurationError, 'Invalid config: Invalid ensure_unique_prefix value: expected a positive integer, got 0'):
            RandomGenerator(config)

        # Now enable unique prefix
        config['all']['ensure_unique_prefix'] = 4
        generator = RandomGenerator(config)
        with patch.object(generator, '_randrange',
                          side_effect=partial(next, cycle(iter(range(8))))):
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
            RandomGenerator({'all': ['wrong']})
        with self.assertRaisesRegex(InitializationError,
                                    "Invalid config: Config at key 'all' has no 'type'"):
            RandomGenerator({'all': {'typ': 'wrong'}})
        with self.assertRaisesRegex(InitializationError,
                                    "Invalid config: Config at key 'all' has invalid 'type'"):
            RandomGenerator({'all': {'type': 'wrong'}})
        with self.assertRaisesRegex(InitializationError,
                                    "Invalid config: Config at key 'all' has no 'lists'"):
            RandomGenerator({'all': {'type': 'nested'}})
        with self.assertRaisesRegex(InitializationError,
                                    "Invalid config: Config at key 'all' has invalid 'lists'"):
            RandomGenerator({'all': {'type': 'nested', 'lists': 'wrong'}})
        with self.assertRaisesRegex(InitializationError,
                                    "Invalid config: Config at key 'all' has no 'value'"):
            RandomGenerator({'all': {'type': 'const'}})
        with self.assertRaisesRegex(InitializationError,
                                    "Invalid config: Config at key 'all' has invalid 'value'"):
            RandomGenerator({'all': {'type': 'const', 'value': 123}})
        with self.assertRaisesRegex(InitializationError,
                                    "Invalid config: Config at key 'all' has no 'words'"):
            RandomGenerator({'all': {'type': 'words'}})
        with self.assertRaisesRegex(InitializationError,
                                    "Invalid config: Config at key 'all' has invalid 'words'"):
            RandomGenerator({'all': {'type': 'words', 'words': []}})
        with self.assertRaisesRegex(InitializationError,
                                    "Invalid config: Lists are referenced but not defined: one, two"):
            RandomGenerator({'all': {'type': 'nested', 'lists': ['one', 'two']}})
        with self.assertRaisesRegex(InitializationError,
                                   "Invalid config: Rule 'all' is recursive: \['all', 'one'\]"):
            RandomGenerator({
                'all': {'type': 'nested', 'lists': ['one']},
                'one': {'type': 'nested', 'lists': ['all']}
            })

    def test_configuration_error_phrases(self):
        with self.assertRaisesRegex(InitializationError,
                                    "Invalid config: Config at key 'all' has no 'phrases'"):
            RandomGenerator({'all': {'type': 'phrases', 'words': []}})
        with self.assertRaisesRegex(InitializationError,
                                    "Invalid config: Config at key 'all' has invalid 'phrases'"):
            RandomGenerator({'all': {'type': 'phrases', 'phrases': []}})
        generator = RandomGenerator({'all': {'type': 'phrases', 'phrases': ['str is allowed']}})
        assert generator.generate_slug() == 'str-is-allowed'
        with self.assertRaisesRegex(InitializationError,
                                    "Invalid config: Config at key 'all' has invalid 'phrases': must be all string/tuple/list"):
            RandomGenerator({'all': {'type': 'phrases', 'phrases': [[['too many square brackets']]]}})
        # Number of words
        RandomGenerator({
            'all': {
                'type': 'phrases',
                'number_of_words': 2,
                'phrases': [['one', 'two'], ['three', 'four']]}
        })
        with self.assertRaisesRegex(InitializationError,
                                    "Invalid config: Config at key 'all' has invalid phrase 'five' \(1 word\(s\) but number_of_words=2\)"):
            RandomGenerator({
                'all': {
                    'type': 'phrases',
                    'number_of_words': 2,
                    'phrases': [['one', 'two'], ['three', 'four'], ['five']]}
            })
        # Max length
        RandomGenerator({
            'all': {
                'type': 'phrases',
                'max_length': 10,
                'phrases': [['black', 'goose'], ['white', 'hare']]}
        })
        with self.assertRaisesRegex(InitializationError,
                                    "Invalid config: Config at key 'all' has invalid phrase 'white rabbit' \(longer than 10 characters\)"):
            RandomGenerator({
                'all': {
                    'type': 'phrases',
                    'max_length': 10,
                    'phrases': [['black', 'goose'], ['white', 'rabbit']]}
            })

    def test_max_length(self):
        with self.assertRaisesRegex(InitializationError,
                                   "Config at key 'one' has invalid word 'tiger' "
                                   "\(longer than 4 characters\)"):
            RandomGenerator({
                'all': {'type': 'nested', 'lists': ['one']},
                'one': {'type': 'words', 'max_length': 4, 'words': ['cat', 'lion', 'tiger']}
            })

    def test_max_slug_length_invalid(self):
        with self.assertRaisesRegex(InitializationError,
                                    r'Invalid config: Invalid max_slug_length value'):
            RandomGenerator({
                'all': {'type': 'words', 'max_slug_length': 'invalid', 'words': ['one', 'two']},
            })

    def test_max_slug_length(self):
        with warnings.catch_warnings(record=True) as w:
            generator = RandomGenerator({
                'all': {'type': 'cartesian', 'max_slug_length': 9, 'lists': ['one', 'two']},
                'one': {'type': 'words', 'words': ['big',  'small']},
                'two': {'type': 'words', 'words': ['cat',  'tiger']},
            })
            if len(w) > 0:
                assert len(w) == 1
                assert str(w[0].message) == 'coolname.generate() may be slow because a significant fraction of combinations exceed max_slug_length=9'
        self.assertEqual(set(generator.generate_slug() for i in range(0, 100)),
                         set(['big-cat', 'big-tiger', 'small-cat']))

    def test_max_slug_length_too_small(self):
        badlist = [str(i) for i in range(10, 100)]
        with self.assertRaisesRegex(InitializationError,
                                    r'Invalid config: Impossible to generate '
                                    r'with max_slug_length=3'):
            RandomGenerator({
                'all': {'type': 'cartesian', 'max_slug_length': 3, 'lists': ['one', 'two']},
                'one': {'type': 'words', 'words': badlist},
                'two': {'type': 'words', 'words': badlist},
            })

    @patch('warnings.warn')
    def test_max_slug_length_warning(self, warn_mock):
        RandomGenerator({
            'all': {'type': 'cartesian', 'max_slug_length': 3, 'lists': ['one', 'two']},
            'one': {'type': 'words', 'words': ['a']*70 + ['bb']*30},
            'two': {'type': 'words', 'words': ['c']*70 + ['dd']*30},
        })
        warn_mock.assert_called_with('coolname.generate() may be slow because a significant '
                                     'fraction of combinations exceed max_slug_length=3')

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
            RandomGenerator(config)


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
            RandomGenerator(config)

    def test_mix_phrases_and_words_in_nested_list(self):
        config = {
            'all': {
                'type': 'cartesian',
                'lists': ['a', 'nested']
            },
            'a': {
                'type': 'const',
                'value': 'a'
            },
            'nested': {
                'type': 'nested',
                'lists': ['words', 'phrases']
            },
            'words': {
                'type': 'words',
                'words': ['one', 'two']
            },
            'phrases': {
                'type': 'phrases',
                'phrases': [
                    'three four',    # Can be space-separated string
                    ['five', 'six']  # or a list/tuple
                ]
            }
        }
        generator = RandomGenerator(config)
        random.seed(0)
        values = set(generator.generate_slug() for i in range(28))
        self.assertEqual(values, set(['a-one', 'a-two', 'a-three-four', 'a-five-six']))

    # randrange returns different results in Python 2. We skip this test to avoid updating it every time.
    @unittest.skipUnless(sys.version_info[0] >= 3, "Skipped on Python 2")
    def test_random_default(self):
        # NOTE: two slugs in this test must be updated every time you change word lists

        # 1. Re-seed default generator
        random.seed(123)
        self.assertEqual(random.random(), 0.052363598850944326)
        self.assertEqual(coolname.generate_slug(), 'accelerated-frog-of-enjoyable-abracadabra')

        # 2. Replace default generator
        rand = random.Random()
        rand.seed(456)
        self.assertEqual(rand.random(), 0.7482025358782363)
        coolname.replace_random(rand)
        self.assertEqual(coolname.generate_slug(), 'glorious-rose-mouflon-of-opportunity')

        # 3. Custom generator with custom Random
        config = {
            'all': {
                'type': 'cartesian',
                'lists': ['digits', 'digits']
            },
            'digits': {
                'type': 'words',
                'words': list(str(x) for x in range(10))
            }
        }
        generator = RandomGenerator(config)
        generator.random.seed(12)
        self.assertEqual(generator.generate_slug(), '6-0')
        generator.random = FakeRandom(33)
        self.assertEqual(generator.generate_slug(), '3-4')

    @patch.object(sys, 'argv', ['coolname', '3', '-s', '_', '-n', '10'])
    def test_command_line(self, *args):
        from coolname.__main__ import main
        main()  # just for the sake of coverage


if __name__ == '__main__':
    import sys
    sys.exit(unittest.main())
