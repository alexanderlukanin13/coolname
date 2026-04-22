import copy
import importlib
import pathlib
from re import escape as esc
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

    @patch('coolname.loader.open', side_effect=OSError('BOOM!'))
    @patch('coolname.loader._load_config', return_value={"all": {"type": "nested", "lists": ["one", "two"]}})
    @patch.object(pathlib.Path, 'is_dir')
    @patch.object(pathlib.Path, 'glob', return_value=[NO_DATA_DIR / 'one.txt', NO_DATA_DIR / 'two.txt'])
    def test_load_data_os_error(self, glob_mock, isdir_mock, config_mock, open_mock):
        with pytest.raises(InitializationError, match=r'Failed to read .+one.txt: BOOM!'):
            _load_data(NO_DATA_DIR)

    @patch('coolname.loader.open', side_effect=OSError('BOOM!'))
    @patch.object(pathlib.Path, 'is_dir')
    @patch.object(pathlib.Path, 'glob', return_value=[NO_DATA_DIR / 'one.txt'])
    def test_load_data_failed_to_read_config(self, glob_mock, isdir_mock, open_mock):
        with pytest.raises(InitializationError, match=r"Failed to read config from .+config\.json: BOOM!"):
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

    @patch('coolname.loader._load_config', return_value={'all': {'type': 'nested', 'lists': ['one']}})
    @patch('coolname.loader.open')
    @patch.object(pathlib.Path, 'is_dir')
    @patch.object(pathlib.Path, 'glob', return_value=[NO_DATA_DIR / 'one.txt'])
    def test_invalid_options_in_txt(self, mock1, mock2, open_mock, config_mock):
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
                                    r"'unknown_option=10' \(Unknown parameter\)"):
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


def test_filter_no_words_error():
    config = {
        'all': {
            'type': 'nested',
            'lists': ['words1', 'phrases1']
        },
        'words1': {
            'type': 'words',
            'words': ['dog', 'dingo'],
        },
        'phrases1': {
            'type': 'phrases',
            'phrases': ['blue whale']
        }
    }
    with pytest.raises(InitializationError, match=esc(r"word_filter returned empty list for words list 'words1'")):
        filter_config(copy.deepcopy(config), lambda x: not x.startswith('d'))
    with pytest.raises(InitializationError, match=esc(r"word_filter returned empty list for phrase list 'phrases1'")):
        filter_config(copy.deepcopy(config), lambda x: 'g' in x)

def test_filter_phrase_splitter_error():
    config = {'all': {'type': 'phrases', 'separator': '/', 'phrases': ['one/two', 'three/four', 'five/six']}}
    def three_filter(x):
        if x == 'three':
            return False
        return True
    filter_config(config, three_filter)
    assert config == {'all': {'type': 'phrases', 'separator': '/', 'phrases': ['one/two', 'five/six']}}

    config = {'all': {'type': 'phrases', 'separator': '/', 'phrases': ['one/two', 'three/four', 'five/six/']}}
    with pytest.raises(InitializationError, match=esc(r"word_filter failed for phrase list 'all': Config at key 'all' has invalid 'phrases': can't split phrase 'five/six/' nicely into words using separator '/' - refusing to guess")):
        filter_config(config, three_filter)
