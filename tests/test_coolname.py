import copy
import pathlib
from functools import partial
from itertools import cycle
import random
from re import escape as esc
import sys
import warnings
from unittest.mock import patch

import pytest

import coolname
from coolname import RandomGenerator, InitializationError
import coolname.data
from coolname.exceptions import ConfigurationError
from coolname.loader import load_config, filter_config

from .common import TestCase, FakeRandom, DATA_DIR, EXAMPLES_DIR
from .generate import PROJECT_PATH


class TestCoolname(TestCase):

    def test_random_default(self):
        # ==================================================================================
        # IMPORTANT: TWO SLUGS IN THIS TEST MUST BE UPDATED EVERY TIME YOU CHANGE WORD LISTS
        # ==================================================================================

        # 1. Re-seed default generator
        random.seed(123)
        self.assertEqual(random.random(), 0.052363598850944326)
        self.assertEqual(coolname.generate_slug(), 'slim-bald-pronghorn-of-temperance')

        # 2. Replace default generator
        rand = random.Random()
        rand.seed(456)
        self.assertEqual(rand.random(), 0.7482025358782363)
        coolname.replace_random(rand)
        self.assertEqual(coolname.generate_slug(), 'enormous-elusive-mandrill-of-youth')

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

    @patch.object(pathlib.Path, 'is_dir', return_value=False)
    @patch.object(pathlib.Path, 'is_file', return_value=True)
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

    @patch.object(pathlib.Path, 'is_dir', return_value=True)
    @patch.object(pathlib.Path, 'is_file', return_value=False)
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
                                    esc(r"Conflict: list 'mywords' is defined both in config.json "
                                        r"and in mywords.txt file. If it's a 'words' or 'phrases' list, "
                                        r"you should remove it from config.json - mywords.txt file is enough.")):
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
                'ensure_unique': False
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
            'all': {'type': 'cartesian', 'lists': ['one', 'one'], 'ensure_unique': False},
            'one': {'type': 'words', 'words': ['one', 'one']}
        }
        RandomGenerator(config)  # this is fine
        config['all']['ensure_unique'] = True
        with self.assertRaisesRegex(ConfigurationError, r'Invalid config: Impossible to generate with ensure_unique'):
            RandomGenerator(config)

    def test_ensure_unique_error_on_list(self):
        config = {
            'all': {'type': 'cartesian', 'ensure_unique': False, 'lists': ['one', 'two']},
            'bad': {'type': 'cartesian', 'generator': True, 'lists': ['one', 'one']},
            'one': {'type': 'words', 'words': ['one', 'one']},
            'two': {'type': 'words', 'words': ['two', 'two']}
        }
        RandomGenerator(config)  # this is fine
        config['all']['ensure_unique'] = True
        with self.assertRaisesRegex(ConfigurationError, r'Invalid config: Impossible to generate with ensure_unique'):
            RandomGenerator(config)


    def test_nocheck_skips_hanging_check(self):
        # __nocheck must skip _check_not_hanging() entirely. Due to operator
        # precedence (and binds tighter than or), it previously only suppressed
        # the ensure_unique branch, so the check still ran when
        # ensure_unique_prefix / max_slug_length were set (as in the default
        # config, which sets __nocheck precisely to skip this).
        config = {
            'all': {
                'type': 'cartesian',
                'lists': ['w1', 'w2'],
                'max_slug_length': 50,
                '__nocheck': True,
            },
            'w1': {'type': 'words', 'words': ['brave', 'agile']},
            'w2': {'type': 'words', 'words': ['bravery', 'brass']},
        }
        with patch.object(RandomGenerator, '_check_not_hanging') as mock_check:
            RandomGenerator(config)
        mock_check.assert_not_called()

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
                                    "Invalid config: Config at key 'all' is not a dict"):
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
                                   r"Invalid config: Rule 'all' is recursive: \['all', 'one'\]"):
            RandomGenerator({
                'all': {'type': 'nested', 'lists': ['one']},
                'one': {'type': 'nested', 'lists': ['all']}
            })

    def test_configuration_error_words(self):
        # No "words" key
        with pytest.raises(InitializationError, match="Invalid config: Config at key 'all' has no 'words'"):
            RandomGenerator({'all': {'type': 'words', 'phrases': []}})
        # 'words' is not a list
        with pytest.raises(InitializationError, match=esc("Invalid config: Config at key 'all' has invalid 'words': "
                                                          "expected list[str], got dict")):
            RandomGenerator({'all': {'type': 'words', 'words': {}}})
        # 'words' list is empty
        with pytest.raises(InitializationError, match="Invalid config: Config at key 'all' has invalid 'words': list is empty"):
            RandomGenerator({'all': {'type': 'words', 'words': []}})
        # 'words' list contains invalid item
        with pytest.raises(InitializationError, match=esc("Invalid config: Config at key 'all' has invalid 'words': "
                                     "expected all words to be str, "
                                     "got ['too many square brackets']")):
            RandomGenerator({'all': {'type': 'words', 'words': [['too many square brackets']]}})
        # 'words' list contains empty or blank string
        # tab is also treated as whitespace
        with pytest.raises(InitializationError, match="Invalid config: Config at key 'all' has invalid 'words': empty word is not allowed"):
            RandomGenerator({'all': {'type': 'words', 'words': ['good', '']}})
        with pytest.raises(InitializationError, match="Invalid config: Config at key 'all' has invalid 'words': whitespace-only word '  ' is not allowed"):
            RandomGenerator({'all': {'type': 'words', 'words': ['good', '  ']}})
        with pytest.raises(InitializationError, match=esc(r"Invalid config: Config at key 'all' has invalid 'words': whitespace-only word '\t' is not allowed")):
            RandomGenerator({'all': {'type': 'words', 'words': ['good', '\t']}})

    def test_configuration_error_phrases(self):
        generator = RandomGenerator({'all': {'type': 'phrases', 'phrases': ['  str  is  allowed  ']}})
        assert generator.generate_slug() == 'str-is-allowed'

        # No "phrases" key
        with pytest.raises(InitializationError, match=r"Invalid config: Config at key 'all' has no 'phrases'"):
            RandomGenerator({'all': {'type': 'phrases', 'words': []}})

        # 'phrases' is not a list
        with pytest.raises(InitializationError, match=esc(r"Invalid config: Config at key 'all' has invalid 'phrases': expected list[str] | list[list[str]] | list[tuple[str, ...]], got dict")):
            RandomGenerator({'all': {'type': 'phrases', 'phrases': {}}})

        # 'phrases' list is empty
        with pytest.raises(InitializationError, match=r"Invalid config: Config at key 'all' has invalid 'phrases': list is empty"):
            RandomGenerator({'all': {'type': 'phrases', 'phrases': []}})

        # 'phrases' list contains invalid item
        with pytest.raises(InitializationError, match=esc(r"Invalid config: Config at key 'all' has invalid 'phrases': empty phrase is not allowed")):
            RandomGenerator({'all': {'type': 'phrases', 'phrases': [['good', 'phrase'], []]}})
        with pytest.raises(InitializationError, match=esc(r"Invalid config: Config at key 'all' has invalid 'phrases': expected all phrases to be str | list[str] | tuple[str, ...], got [['too many square brackets']]")):
            RandomGenerator({'all': {'type': 'phrases', 'phrases': [[['too many square brackets']]]}})

        # 'phrases' list contains empty or blank string
        # tab is also treated as whitespace
        with pytest.raises(InitializationError, match=r"Invalid config: Config at key 'all' has invalid 'phrases': empty phrase is not allowed"):
            RandomGenerator({'all': {'type': 'phrases', 'phrases': ['good phrase', '']}})
        with pytest.raises(InitializationError, match=r"Invalid config: Config at key 'all' has invalid 'phrases': whitespace-only phrase is not allowed with strip_whitespace=True"):
            RandomGenerator({'all': {'type': 'phrases', 'phrases': ['good phrase', '  ']}})
        with pytest.raises(InitializationError, match=esc(r"Invalid config: Config at key 'all' has invalid 'phrases': whitespace-only phrase is not allowed with strip_whitespace=True")):
            RandomGenerator({'all': {'type': 'phrases', 'phrases': ['good phrase', '\t']}})

        # subitem within an item in 'phrase' list contains empty or blank string
        # tab is also treated as whitespace
        with pytest.raises(InitializationError, match=esc(r"Invalid config: Config at key 'all' has invalid 'phrases': empty word within phrase ['good', ''] is not allowed")):
            RandomGenerator({'all': {'type': 'phrases', 'phrases': ['good phrase', ['good', '']]}})
        with pytest.raises(InitializationError, match=esc(r"Invalid config: Config at key 'all' has invalid 'phrases': whitespace-only word within phrase ['good', '  '] is not allowed while strip_whitespace=True")):
            RandomGenerator({'all': {'type': 'phrases', 'phrases': ['good phrase', ['good', '  ']]}})
        with pytest.raises(InitializationError, match=esc(r"Invalid config: Config at key 'all' has invalid 'phrases': whitespace-only word within phrase ['good', '\t'] is not allowed while strip_whitespace=True")):
            RandomGenerator({'all': {'type': 'phrases', 'phrases': ['good phrase', ['good', '\t']]}})

        # subitem within an item in 'phrase' list contains space
        with pytest.raises(InitializationError, match=esc(r"Invalid config: Config at key 'all' has invalid 'phrases': word within phrase ['bad', 'phrase with space'] contains whitespace while strip_whitespace=True, allow_whitespace=False")):
            RandomGenerator({'all': {'type': 'phrases', 'phrases': ['good phrase', ['bad', 'phrase with space']]}})

        # Number of words
        RandomGenerator({
            'all': {
                'type': 'phrases',
                'number_of_words': 2,
                'phrases': [['one', 'two'], ['three', 'four']]}
        })
        with pytest.raises(InitializationError, match=esc(r"Invalid config: Config at key 'all' has invalid phrase ['five'] (1 word(s) but number_of_words=2)")):
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
        with pytest.raises(InitializationError, match=esc(r"Invalid config: Config at key 'all' has invalid phrase ['white', 'rabbit'] (longer than 10 characters)")):
            RandomGenerator({
                'all': {
                    'type': 'phrases',
                    'max_length': 10,
                    'phrases': [['black', 'goose'], ['white', 'rabbit']]}
            })

        # Invalid separator
        with pytest.raises(InitializationError, match=esc(r"Invalid config: Config at key 'all' has invalid separator 're:(\\s+': missing ), unterminated subpattern at position 0")):
            RandomGenerator({
                'all': {
                    'type': 'phrases',
                    'separator': r're:(\s+',
                    'phrases': [['good', 'phrase']]}
            })

    def test_max_length(self):
        with pytest.raises(InitializationError, match=r"Config at key 'one' has invalid word 'tiger' \(longer than 4 characters\)"):
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
        assert set(generator.generate_slug() for i in range(0, 100)) == {'big-cat', 'big-tiger', 'small-cat'}

    def test_max_slug_length_too_small(self):
        bad_list = [str(i) for i in range(10, 100)]
        with self.assertRaisesRegex(InitializationError,
                                    r'Invalid config: Impossible to generate '
                                    r'with max_slug_length=3'):
            RandomGenerator({
                'all': {'type': 'cartesian', 'max_slug_length': 3, 'lists': ['one', 'two']},
                'one': {'type': 'words', 'words': bad_list},
                'two': {'type': 'words', 'words': bad_list},
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

    def test_configuration_error_cartesian_inside_cartesian(self):
        config = {
            'all': {
                'type': 'cartesian',
                'lists': ['word_list', 'cart_list']
            },
            'word_list': {
                'type': 'words',
                'words': ['one', 'two'],
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
        assert {generator.generate_slug() for i in range(28)} == {'a-one', 'a-two', 'a-three-four', 'a-five-six'}

    def test_render(self):
        generator = RandomGenerator({
            'all': {'type': 'nested', 'lists': ['long', 'short']},
            'long': {'type': 'cartesian', 'generator': True, 'lists': ['adj', 'noun', 'from', 'loc']},
            'short': {'type': 'cartesian', 'generator': True, 'lists': ['adj', 'noun']},
            'adj': {'type': 'words', 'words': ['white', 'black']},
            'noun': {'type': 'words', 'words': ['dog', 'cat', 'bird']},
            'from': {'type': 'const', 'value': 'from'},
            'loc': {'type': 'phrases', 'phrases': ['big city', 'small town']}
        })
        expected_all =("RandomGenerator\n"
                       "  NestedList(2, len=18)\n"
                       "    CartesianList(4, len=12)\n"
                       "      WordList(['white', 'black'], len=2)\n"
                       "      WordList(['dog', 'cat', 'bird'], len=3)\n"
                       "      Constant(value='from')\n"
                       "      PhraseList([('big', 'city'), ('small', 'town')], len=2)\n"
                       "    CartesianList(2, len=6)\n"
                       "      WordList(['white', 'black'], len=2)\n"
                       "      WordList(['dog', 'cat', 'bird'], len=3)\n")
        assert generator.render() == expected_all
        expected = ("RandomGenerator\n"
                    "   CartesianList(4, len=12)\n"
                    "      WordList(['white', 'black'], len=2)\n"
                    "      WordList(['dog', 'cat', ...], len=3)\n"
                    "      Constant(value='from')\n"
                    "      PhraseList([('big', 'city'), ('small', 'town')], len=2)\n")
        assert generator.render("long", indent='   ', max_items=2) == expected
        assert generator.render("long", indent=3, max_items=2) == expected
        expected_short = ("RandomGenerator\n"
                          "  CartesianList(2, len=6)\n"
                          "    WordList(['white', 'black'], len=2)\n"
                          "    WordList(['dog', 'cat', 'bird'], len=3)\n")
        assert generator.render('short') == expected_short


@patch.object(sys, 'argv', ['coolname', '3', '-s', '_', '-n', '10'])
def test_command_line():
    from coolname.__main__ import main
    main()  # just for the sake of coverage


def test_phrases_in_txt_with_custom_separator():
    generator = RandomGenerator(load_config(DATA_DIR / 'phrases_txt_custom_sep'))
    assert {generator.generate_slug() for i in range(10)} == {
        'big - dog',    # sic!
        'small - cat',  # sic!
        'quick-fox',
        'lazy-dog',
        'quick-baby fox',
        'lazy-little puppy'
    }


def test_non_az_wordlist():
    with pytest.raises(ConfigurationError, match=esc(r"Invalid config: Config at key 'words1' has invalid 'words': word 'not?az' doesn't match word_regex='\\w+'")):
        RandomGenerator(load_config(DATA_DIR / 'non_az_wordlist'))


def test_default_config_word_regex_error():
    config = copy.deepcopy(coolname.data.config)
    config['animal']['words'][0] = 'EarthWorm'
    with pytest.raises(ConfigurationError, match=esc(r"Invalid config: Config at key 'animal' has invalid 'words': word 'EarthWorm' doesn't match word_regex='[a-z]+'")):
        RandomGenerator(config)

def test_invalid_word_regex():
    with pytest.raises(ConfigurationError, match=esc(r"Invalid config: Config at key 'all' has invalid word_regex: must be a string")):
        RandomGenerator({'all': {'type': 'words', 'words': ['one', 'two'], 'word_regex': 123}})
    with pytest.raises(ConfigurationError, match=esc(r"Invalid config: Config at key 'all' has invalid word_regex: missing ), unterminated subpattern at position 0")):
        RandomGenerator({'all': {'type': 'words', 'words': ['one', 'two'], 'word_regex': r"(\w+"}})

def test_unexpected_option_in_txt():
    with pytest.raises(ConfigurationError, match=esc(r"Invalid config: Invalid assignment at list 'words1' line 1: 'max_slug_length = 50' (Parameter max_slug_length is not allowed in *.txt files)")):
        RandomGenerator(load_config(DATA_DIR / 'unexpected_option'))

def test_invalid_boolean_in_txt():
    with pytest.raises(ConfigurationError, match=esc(r"Invalid config: Invalid assignment at list 'words1' line 1: 'strip_whitespace = Ture' (Parameter must be a valid boolean)")):
        RandomGenerator(load_config(DATA_DIR / 'invalid_boolean'))

def test_invalid_config():
    with pytest.raises(ConfigurationError, match=r"Invalid config: Expected config dict, got list"):
        RandomGenerator([])
    with pytest.raises(ConfigurationError, match=r"Invalid config: Config must have 'all' key"):
        RandomGenerator({"alu": {"type": "words", "words": ["one", "two", "three"]}})

def test_word_with_spaces_in_txt_error():
    with pytest.raises(ConfigurationError, match=esc(r"Invalid config: Config at key 'words1' has invalid 'words': word 'beta gamma' contains whitespace while strip_whitespace=True, allow_whitespace=False")):
        RandomGenerator(load_config(DATA_DIR / 'word_with_spaces_error'))

def test_phrase_with_spaces_in_txt_error():
    with pytest.raises(ConfigurationError, match=esc(r"Invalid config: Config at key 'phrases1' has invalid 'phrases': word within phrase ['three four', 'five'] contains whitespace while strip_whitespace=True, allow_whitespace=False")):
        RandomGenerator(load_config(DATA_DIR / 'phrase_with_spaces_error'))

def test_phrase_with_spaces_in_txt_ok():
    assert RandomGenerator(load_config(DATA_DIR / 'phrase_with_spaces_ok')).generate_slug()

def test_phrase_with_spaces_in_txt_ok_2():
    assert RandomGenerator(load_config(DATA_DIR / 'phrase_with_spaces_ok_2')).generate_slug()

def test_number_of_words_in_txt():
    with pytest.raises(InitializationError, match=esc(r"Invalid config: Phrase has 1 word(s) (while number_of_words=2) at list 'phrases1' line 5: 'five'")):
        RandomGenerator(load_config(DATA_DIR / 'number_of_words_in_txt'))

def test_max_length_in_txt():
    with pytest.raises(InitializationError, match=esc(r"Invalid config: Word is too long at list 'words1' line 4: 'abcdef'")):
        RandomGenerator(load_config(DATA_DIR / 'max_length_in_txt'))

def test_value_not_a_dict():
    with pytest.raises(ConfigurationError, match=esc(r"Invalid config: Value at key 'one' is not a dict")):
        RandomGenerator({'all': {'type': 'nested', 'lists': ['one']}, 'one': []})

def test_invalid_constant():
    with pytest.raises(ConfigurationError, match=esc(r"Invalid config: Config at key 'one' has invalid 'value' (doesn't match word_regex='\\w+')")):
        RandomGenerator({'all': {'type': 'nested', 'lists': ['one']}, 'one': {'type': 'const', 'value': '!!'}})

def test_empty_phrase():
    with pytest.raises(ConfigurationError, match=esc(r"Invalid config: Config at key 'all' has invalid 'phrases': whitespace-only phrase is not allowed with strip_whitespace=True")):
        RandomGenerator({'all': {'type': 'phrases', 'phrases': ['one two', 'three four', '  ']}})
    generator = RandomGenerator({
        'all': {
            'type': 'phrases',
            'separator': '/',
            'word_regex': r'.+',
            'strip_whitespace': False,
            'phrases': ['one/two', 'three/four', '  /xx']
        }
    })
    random.seed(0)
    assert set(generator.generate_slug() for i in range(5)) == {'one-two', 'three-four', '  -xx'}

def test_invalid_word_in_phrase():
    with pytest.raises(ConfigurationError, match=esc(r"Invalid config: Config at key 'all' has invalid 'phrases': word within phrase '@&! ???' doesn't match word_regex='\\w+'")):
        RandomGenerator({'all': {'type': 'phrases', 'phrases': ['one two', 'three four', '@&! ???']}})

def test_strip_words():
    random.seed(0)
    generator = RandomGenerator({'all': {'type': 'words', 'words': ['one ', ' two']}})
    assert set(generator.generate_slug() for i in range(7)) == {'one', 'two'}

    random.seed(0)
    generator = RandomGenerator({'all': {'type': 'words', 'words': ['one ', ' two'], 'strip_whitespace': False, 'allow_whitespace': True}})
    assert set(generator.generate_slug() for i in range(7)) == {'one ', ' two'}


def test_ensure_unique_false():
    # For the sake of coverage
    random.seed(0)
    config = {
        'all': {
            'type': 'cartesian',
            'lists': ['words1', 'words2'],
            'ensure_unique': False,
            'max_slug_length': 50,
        },
        'words1': {
            'type': 'words',
            'words': ['one', 'two', 'three'],
        },
        'words2': {
            'type': 'words',
            'words': ['three', 'four'],
        },
    }
    generator = RandomGenerator(config)
    assert 'three-three' in [generator.generate_slug() for i in range(11)]

def test_invalid_strip_whitespace():
    with pytest.raises(ConfigurationError, match=esc(r"Invalid config: Config at key 'all' has invalid strip_whitespace: must be a boolean")):
        RandomGenerator({'all': {'type': 'words', 'words': ['one', 'two'], 'strip_whitespace': 'true'}})

def test_invalid_all():
    with pytest.raises(ConfigurationError, match=esc(r"Invalid config: Config must have 'all' key")):
        RandomGenerator(load_config(DATA_DIR / 'invalid_all'))
    with pytest.raises(ConfigurationError, match=esc(r"Invalid config: Config at key 'all' is not a dict")):
        RandomGenerator(load_config(DATA_DIR / 'invalid_all_dict'))


def test_number():
    # Test validation
    with pytest.raises(ConfigurationError, match=r"Invalid config: Config at key 'all' has invalid 'digits': must be between 1 and 7"):
        RandomGenerator({'all': {'type': 'number', 'digits': 0}})

    generator = RandomGenerator({
        'all': {
            'type': 'cartesian',
            'lists': ['word', 'number']
        },
        'word': {
            'type': 'words',
            'words': ['dog', 'cat', 'bird']
        },
        'number': {
            'type': 'number'
        }
    })
    random.seed(0)
    assert generator.generate_slug() == 'cat-579'

    # Also test render() for the sake of coverage
    assert generator.render() == ("RandomGenerator\n"
                                  "  CartesianList(2, len=2997)\n"
                                  "    WordList(['dog', 'cat', 'bird'], len=3)\n"
                                  "    Number(digits=3)\n")
