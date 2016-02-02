"""
This module provides `load_config` function,
which loads configuration from file or directory.

You will need this only if you are creating
custom instance of RandomNameGenerator.
"""


import codecs
import json
import os
import re

from .config import _CONF
from .exceptions import InitializationError, ConfigurationError


def load_config(path):
    """
    Loads configuration from a path.

    Path can be a json file, or a directory containing config.json
    and zero or more *.txt files with word lists.

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
        raise InitializationError('File or directory not found: {0}'.format(path))
    for name, wordlist in wordlists.items():
        if name in config:
            raise InitializationError("Conflict: list {!r} is defined both in config "
                                      "and in *.txt file. If it's a {!r} list, "
                                      "you should remove it from config."
                                      .format(name, _CONF.TYPE.WORDS))
        config[name] = wordlist
    return config


def _load_data(path):
    """
    Loads data from a directory.
    Returns tuple (config_dict, wordlists).
    Raises Exception on failure (e.g. if data is corrupted).
    """
    path = os.path.abspath(path)
    if not os.path.isdir(path):
        raise InitializationError('Directory not found: {0}'.format(path))
    wordlists = {}
    for file_name in os.listdir(path):
        if os.path.splitext(file_name)[1] != '.txt':
            continue
        file_path = os.path.join(path, file_name)
        name = os.path.splitext(os.path.split(file_path)[1])[0]
        try:
            with codecs.open(file_path, encoding='utf-8') as file:
                wordlists[name] = _load_wordlist(name, file)
        except OSError as ex:
            raise InitializationError('Failed to read {}: {}'.format(file_path, ex))
    config = _load_config(os.path.join(path, 'config.json'))
    return (config, wordlists)


def _load_config(config_file_path):
    try:
        with codecs.open(config_file_path, encoding='utf-8') as file:
            return json.load(file)
    except OSError as ex:
        raise InitializationError('Failed to read config from {}: {}'.format(config_file_path, ex))
    except ValueError as ex:
        raise ConfigurationError('Invalid JSON: {}'.format(ex))


# Word must be in English, 1-N letters, lowercase.
_WORD_REGEX = re.compile(r'^[a-z]+$')


# Options are defined using simple notation: 'option = value'
_OPTION_REGEX = re.compile(r'^([a-z_]+)\s*=\s*(\w+)$', re.UNICODE)
_OPTIONS = [
    ('max_length', int),
]


def _parse_option(line):
    """
    Parses option line.
    Returns (name, value).
    Raises ValueError on invalid syntax or unknown option.
    """
    match = _OPTION_REGEX.match(line)
    if not match:
        raise ValueError('Invalid syntax')
    for name, type_ in _OPTIONS:
        if name == match.group(1):
            return name, type_(match.group(2))
    raise ValueError('Unknown option')


def _load_wordlist(name, stream):
    """
    Loads list of words from file.

    Returns "words" dictionary, the same as used in config.
    Raises Exception if file is missing or invalid.
    """
    words = []
    max_length = None
    for i, line in enumerate(stream, start=1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        # Is it an option line, e.g. 'max_length = 10'?
        if '=' in line:
            if words:
                raise ConfigurationError('Invalid assignment at wordlist {!r} line {}: {!r} '
                                         '(options must be defined before words)'
                                         .format(name, i, line))
            try:
                option, option_value = _parse_option(line)
            except ValueError as ex:
                raise ConfigurationError('Invalid assignment at wordlist {!r} line {}: {!r} '
                                         '({})'
                                         .format(name, i, line, ex))
            if option == 'max_length':
                max_length = option_value
            continue  # pragma: no cover
        # Parse words
        if not _WORD_REGEX.match(line):
            raise ConfigurationError('Invalid syntax at wordlist {!r} line {}: {!r}'
                                     .format(name, i, line))
        if max_length is not None and len(line) > max_length:
            raise ConfigurationError('Word is too long at wordlist {!r} line {}: {!r}'
                                     .format(name, i, line))
        words.append(line)
    result = {
        _CONF.FIELD.TYPE: _CONF.TYPE.WORDS,
        _CONF.FIELD.WORDS: words
    }
    if max_length is not None:
        result[_CONF.FIELD.MAX_LENGTH] = max_length
    return result
