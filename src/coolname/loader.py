"""
This module provides `load_config` function,
which loads configuration from file or directory.

You will need this only if you are creating
custom instance of RandomGenerator.
"""

import json
import os
import re
from pathlib import Path
from typing import cast, TextIO

from .config import _CONF
from .exceptions import InitializationError, ConfigurationError


# Top-level values of config dict, for example:
# {"comment": "adjective-adjective-noun",
#  "type": "cartesian",
#  "lists": ["adj_far", "adj_near", "subj"]}
_ListConfigT = dict[str, str | list[str] | list[tuple[str, ...]] | int]
_ConfigT = dict[str, _ListConfigT]


def load_config(path: str | Path) -> _ConfigT:
    """
    Loads configuration from a path.

    Path can be a json file, or a directory containing config.json
    and zero or more *.txt files with word lists or phrase lists.

    Returns config dict.

    Raises InitializationError when something is wrong.
    """
    path = os.path.abspath(path)
    if os.path.isdir(path):
        config, wordlists = _load_data(path)
    elif os.path.isfile(path):
        config = _load_config(path)
        wordlists = {}
    else:
        raise InitializationError(f'File or directory not found: {path}')
    for name, wordlist in wordlists.items():
        if name in config:
            raise InitializationError(f"Conflict: list {name!r} is defined both in config "
                                      f"and in *.txt file. If it's a {_CONF.TYPE.WORDS!r} list, "
                                      f"you should remove it from config.")
        config[name] = wordlist
    return config


def _load_data(path: str | Path) -> tuple[_ConfigT, dict[str, _ListConfigT]]:
    """
    Loads data from a directory.
    Returns tuple (config_dict, wordlists).
    Raises Exception on failure (e.g. if data is corrupted).
    """
    path = os.path.abspath(path)
    if not os.path.isdir(path):
        raise InitializationError(f'Directory not found: {path}')
    wordlists = {}
    for file_name in os.listdir(path):
        if os.path.splitext(file_name)[1] != '.txt':
            continue
        file_path = os.path.join(path, file_name)
        name = os.path.splitext(os.path.split(file_path)[1])[0]
        try:
            with open(file_path, encoding='utf-8') as file:
                wordlists[name] = _load_wordlist(name, file)
        except (OSError, FileNotFoundError) as ex:
            raise InitializationError(f'Failed to read {file_path}: {ex}')
    config = _load_config(os.path.join(path, 'config.json'))
    return (config, wordlists)


def _load_config(config_file_path: str | Path) -> _ConfigT:
    try:
        with open(config_file_path, encoding='utf-8') as file:
            return cast(_ConfigT, json.load(file))
    except (OSError, FileNotFoundError) as ex:
        raise InitializationError(f'Failed to read config from {config_file_path}: {ex}')
    except ValueError as ex:
        raise ConfigurationError(f'Invalid JSON: {ex}')


# Word must be in English, 1-N letters, lowercase.
_WORD_REGEX = re.compile(r'^[a-z]+$')
_PHRASE_REGEX = re.compile(r'^\w+(?: \w+)*$')


# Options are defined using simple notation: 'option = value'
# Value is always integer
_OPTION_REGEX = re.compile(r'^([a-z_]+)\s*=\s*(\w+)$', re.UNICODE)
_OPTIONS: list[str] = [
    _CONF.FIELD.MAX_LENGTH,
    _CONF.FIELD.NUMBER_OF_WORDS,
]


def _parse_option(line: str) -> tuple[str, int]:
    """
    Parses option line.
    Returns (name, value).
    Raises ValueError on invalid syntax or unknown option.
    """
    match = _OPTION_REGEX.match(line)
    if not match:
        raise ValueError('Invalid syntax')
    for name in _OPTIONS:
        if name == match.group(1):
            return name, int(match.group(2))
    raise ValueError('Unknown option')


def _load_wordlist(name: str, stream: TextIO) -> _ListConfigT:
    """
    Loads list of words or phrases from *.txt file.

    Returns "words" or "phrases" dictionary, the same as used in config.
    Raises Exception if file is missing or invalid.
    """
    items: list[str | tuple[str, ...]] = []
    max_length: int | None = None
    multiword_start: int | None = None
    number_of_words: int | None = None
    for i, line in enumerate(stream, start=1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        # Is it an option line, e.g. 'max_length = 10'?
        if '=' in line:
            if items:
                raise ConfigurationError(f'Invalid assignment at list {name!r} line {i}: {line!r} '
                                         f'(options must be defined before words)')
            try:
                option, option_value = _parse_option(line)
            except ValueError as ex:
                raise ConfigurationError(f'Invalid assignment at list {name!r} line {i}: {line!r} ({ex})')
            if option == _CONF.FIELD.MAX_LENGTH:
                max_length = option_value
            elif option == _CONF.FIELD.NUMBER_OF_WORDS:
                number_of_words = option_value
            continue  # pragma: no cover
        # Parse words
        if multiword_start is None and _WORD_REGEX.match(line):
            if max_length is not None and len(line) > max_length:
                raise ConfigurationError(f'Word is too long at list {name!r} line {i}: {line!r}')
            items.append(line)
        elif _PHRASE_REGEX.match(line):
            if multiword_start is None:
                multiword_start = len(items)
            phrase = tuple(line.split(' '))
            if number_of_words is not None and len(phrase) != number_of_words:
                raise ConfigurationError(f'Phrase has {len(phrase)} word(s) (while number_of_words={number_of_words}) '
                                         f'at list {name!r} line {i}: {line!r}')
            if max_length is not None and sum(len(x) for x in phrase) > max_length:
                raise ConfigurationError(f'Phrase is too long at list {name!r} line {i}: {line!r}')
            items.append(phrase)
        else:
            raise ConfigurationError(f'Invalid syntax at list {name!r} line {i}: {line!r}')
    if multiword_start is not None:
        # If in phrase mode, convert everything to tuples
        for i in range(0, multiword_start):
            items[i] = (items[i], )
        result = {
            _CONF.FIELD.TYPE: _CONF.TYPE.PHRASES,
            _CONF.FIELD.PHRASES: items
        }
        if number_of_words is not None:
            result[_CONF.FIELD.NUMBER_OF_WORDS] = number_of_words
    else:
        result = {
            _CONF.FIELD.TYPE: _CONF.TYPE.WORDS,
            _CONF.FIELD.WORDS: items
        }
    if max_length is not None:
        result[_CONF.FIELD.MAX_LENGTH] = max_length
    return result
