import copy
import importlib
import pathlib
import sys
from functools import partial
from io import StringIO

from pathlib import Path
from typing import Callable
from unittest.mock import patch

import pytest

from coolname import InitializationError
from coolname.loader import _load_wordlist, _load_data, load_config, filter_config, save_config_as_module
from coolname.types import CoolnameConfigT

from .common import TestCase, DATA_DIR, COOLNAME_DATA_DIR

NO_DATA_DIR = Path('.') / 'no_such_dir' / 'data'


class LoaderTest(TestCase):

    def test_load_wordlist(self):
        s = StringIO('\n'.join([
            'alpha',
            '',  # blank line
            'beta',
            '# Some comment',
            'gamma',
        ]))
        wordlist = _load_wordlist('words', s)
        self.assertEqual(wordlist, {
            'type': 'words',
            'words': ['alpha', 'beta', 'gamma']
        })

    def test_load_wordlist_max_length(self):
        s = StringIO('\n'.join([
            'max_length = 11',
            'alpha',
        ]))
        wordlist = _load_wordlist('words', s)
        self.assertEqual(wordlist, {
            'type': 'words',
            'max_length': 11,
            'words': ['alpha']
        })

    def test_invalid_wordlist(self):
        s = StringIO('\n'.join([
            'alpha',
            'invalid?syntax',
        ]))
        with self.assertRaisesRegex(InitializationError,
                                    r"Invalid config: Invalid syntax "
                                    r"at list 'words' line 2: 'invalid\?syntax'"):
            _load_wordlist('words', s)

    def test_word_too_long(self):
        s = StringIO('\n'.join([
            'max_length = 11',
            'alpha',
            'augmentation',  # line exceeds 11 characters
        ]))
        with self.assertRaisesRegex(InitializationError,
                                    r"Invalid config: Word is too long "
                                    r"at list 'words' line 3: 'augmentation'"):
            _load_wordlist('words', s)

    def test_load_phrases(self):
        s = StringIO('\n'.join([
            'one',
            'two',
            'three',
            'four five',
            'six',
            'seven eight'
        ]))
        wordlist = _load_wordlist('phrases', s)
        self.assertEqual(wordlist, {
            'type': 'phrases',
            'phrases': [
                ['one'],
                ['two'],
                ['three'],
                ['four', 'five'],
                ['six'],
                ['seven', 'eight']
            ]
        })

    def test_phrase_too_long(self):
        s = StringIO('\n'.join([
            'max_length = 9',
            'alpha beta',
            'gamma delta',  # 10 characters
        ]))
        with self.assertRaisesRegex(InitializationError,
                                    r"Invalid config: Phrase is too long "
                                    r"at list 'words' line 3: 'gamma delta'"):
            _load_wordlist('words', s)

    @patch('json.load')
    @patch('coolname.loader._load_wordlist')
    @patch('coolname.loader.open')
    @patch.object(pathlib.Path, 'is_dir')
    @patch.object(pathlib.Path, 'glob')
    def test_load_data(self,
                       glob_mock, isdir_mock, open_mock,
                       load_wordlist_mock, json_mock):
        glob_mock.return_value = [NO_DATA_DIR / 'one.txt', NO_DATA_DIR / 'two.txt']
        isdir_mock.return_value = True
        lists = iter([['one', 'ichi'], ['two', 'ni']])
        load_wordlist_mock.side_effect = lambda x, y: next(lists)
        json_mock.return_value = {'hello': 'world'}
        config, wordlists = _load_data(NO_DATA_DIR)
        self.assertEqual(config, {'hello': 'world'})
        self.assertEqual(wordlists, {
            'one': ['one', 'ichi'],
            'two': ['two', 'ni'],
        })

    @patch('coolname.loader.open', side_effect=OSError('BOOM!'))
    @patch.object(pathlib.Path, 'is_dir')
    @patch.object(pathlib.Path, 'glob', return_value=[NO_DATA_DIR / 'one.txt', NO_DATA_DIR / 'two.txt'])
    def test_load_data_os_error(self, listdir_mock, isdir_mock, open_mock):
        with self.assertRaisesRegex(InitializationError,
                                    r'Failed to read .+one.txt: BOOM!'):
            _load_data(NO_DATA_DIR)

    @patch('coolname.loader.open')
    @patch.object(pathlib.Path, 'is_dir')
    @patch.object(pathlib.Path, 'glob', return_value=[NO_DATA_DIR / 'one.txt'])
    def test_load_data_failed_to_read_config(self, listdir_mock, isdir_mock,
                                             open_mock):
        # First call to open() should pass,
        # second call should raise OSError.
        class open_then_fail(object):

            def __init__(self):
                self.called = False

            def __call__(self, *x, **y):
                if self.called:
                    raise OSError('BOOM!')
                self.called = True
                return StringIO('word')

        open_mock.side_effect = open_then_fail()
        with self.assertRaisesRegex(InitializationError,
                                    r"Failed to read config from "
                                    r".+config\.json: BOOM!"):
            _load_data(NO_DATA_DIR)

    @patch('coolname.loader.open', side_effect=lambda *x, **y: StringIO('word'))
    @patch.object(pathlib.Path, 'is_dir')
    @patch.object(pathlib.Path, 'glob', return_value=[NO_DATA_DIR / 'one.txt', NO_DATA_DIR / 'two.txt'])
    def test_load_data_invalid_json(self, *args):
        with self.assertRaisesRegex(InitializationError,
                                    r"Invalid config: Invalid JSON: "
                                    r"((?:Expecting value|Unexpected 'w'(?: at)?): line 1 column 1 \(char 0\)|"
                                    r"No JSON object could be decoded)"):
            _load_data(NO_DATA_DIR)

    @patch('coolname.loader.open')
    @patch.object(pathlib.Path, 'is_dir')
    @patch.object(pathlib.Path, 'glob', return_value=[NO_DATA_DIR / 'one.txt'])
    def test_invalid_options_in_txt(self, mock1, mock2, open_mock):
        load_data = partial(_load_data, NO_DATA_DIR)
        # Invalid syntax
        open_mock.return_value = StringIO('max_length=\n')
        with self.assertRaisesRegex(InitializationError,
                                    r"Invalid config: Invalid assignment "
                                    r"at list 'one' line 1: "
                                    r"'max_length=' \(Invalid syntax\)"):
            load_data()

        # Unknown option
        open_mock.return_value = StringIO('unknown_option=10\n')
        with self.assertRaisesRegex(InitializationError,
                                    r"Invalid config: Invalid assignment "
                                    r"at list 'one' line 1: "
                                    r"'unknown_option=10' \(Unknown option\)"):
            load_data()

        # max_length is not int
        open_mock.return_value = StringIO('max_length=string\n')
        with self.assertRaisesRegex(InitializationError,
                                    r"Invalid config: Invalid assignment "
                                    r"at list 'one' line 1: "
                                    r"'max_length=string' \(invalid literal.*\)"):
            load_data()

        # max_length after some words are defined
        open_mock.return_value = StringIO('something\nmax_length=9\n')
        with self.assertRaisesRegex(InitializationError,
                                    r"Invalid config: Invalid assignment "
                                    r"at list 'one' line 2: "
                                    r"'max_length=9' \(options must be defined before words\)"):
            load_data()


    @patch('coolname.loader.open')
    @patch.object(pathlib.Path, 'is_dir')
    @patch.object(pathlib.Path, 'glob', return_value=[NO_DATA_DIR / 'one.txt'])
    def test_max_length_in_txt(self, mock1, mock2, open_mock):
        # Valid option max_length
        open_mock.return_value = StringIO('max_length=5\nabcde\nabcdef\nabc\n')
        with self.assertRaisesRegex(InitializationError,
                                    r"Invalid config: Word is too long "
                                    r"at list 'one' line 3: 'abcdef'"):
            _load_data(NO_DATA_DIR)

    @patch('coolname.loader.open')
    @patch.object(pathlib.Path, 'is_dir')
    @patch.object(pathlib.Path, 'glob', return_value=[NO_DATA_DIR / 'one.txt'])
    def test_number_of_words_in_txt(self, mock1, mock2, open_mock):
        open_mock.return_value = StringIO('number_of_words=2\none two\nathree four\nfive\nsix\n')
        with self.assertRaisesRegex(InitializationError,
                                    r"Invalid config: Phrase has 1 word\(s\) \(while number_of_words=2\) "
                                    r"at list 'one' line 4: 'five'"):
            _load_data(NO_DATA_DIR)


def test_load_config_word_filter():

    def load_and_filter(path: str | Path, word_filter_: Callable[[str], bool]) -> CoolnameConfigT:
        config = load_config(path)
        filter_config(config, word_filter_)
        return config

    def word_filter(s: str) -> bool:
        return 'a' not in s

    assert load_and_filter(DATA_DIR / 'load_config' / 'word_filter', word_filter) == {
        "all": {
            "type": "nested",
            "lists": ["words1", "words2", "phrases1", "phrases2", "phrases3"]
        },
        "words1": {
            "type": "words",
            "words": ["bull", "dog"]
        },
        "words2": {
            "type": "words",
            "words": ["crow"]
        },
        "phrases1": {
            "type": "phrases",
            "phrases": ["little mouse"]
        },
        "phrases2": {
            "type": "phrases",
            "phrases": [["iron", "moose"]]
        },
        "phrases3": {
            "type": "phrases",
            "phrases": [["mini", "fish"]]
        }
    }


def test_load_data_no_dir(tmp_path):
    path = tmp_path / 'does' / 'not' / 'exist'
    with pytest.raises(InitializationError, match=r'Directory not found: .+exist'):
        _load_data(path)


def test_save_config(tmp_path):
    # Save default config, load it again and compare to the original
    config = load_config(COOLNAME_DATA_DIR)
    filename = tmp_path / 'saved_config.py'
    save_config_as_module(config, filename)
    sys.path.append(str(tmp_path))
    module = importlib.import_module('saved_config')
    assert module.config
    assert module.config['all']
    assert module.config == config

    # Filter out a word and try again
    orig_config = copy.deepcopy(config)
    filter_config(config, lambda x: x != 'aardvark')
    filename = tmp_path / 'saved_config_filtered.py'
    save_config_as_module(config, filename)
    module = importlib.import_module('saved_config_filtered')
    assert module.config
    assert module.config['all']
    assert module.config != orig_config
