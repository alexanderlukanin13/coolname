from __future__ import annotations
import json
import re
from datetime import datetime
from pathlib import Path
from typing import cast, TextIO, Callable

from ._config import _CONF, PhraseSplitter
from .exceptions import InitializationError, ConfigurationError
from .types import CoolnameConfigT, CoolnameConfigListT

__all__ = ['load_config', 'filter_config', 'save_config_as_module']


def load_config(path: str | Path) -> CoolnameConfigT:
    """
    Loads configuration from a path,
    returns :py:class:`~coolname.types.CoolnameConfigT`.

    :param path: standalone JSON file, or a directory containing
        ``config.json`` and zero or more ``*.txt`` files
        with word lists or phrase lists.

    Raises :py:class:`InitializationError` if something goes wrong.
    """
    path = Path(path)
    if path.is_dir():
        config, wordlists = _load_data(path)
    elif path.is_file():
        config = _load_config(path)
        wordlists = {}
    else:
        raise InitializationError(f'File or directory not found: {path}')
    for name, wordlist in wordlists.items():
        if name in config:
            raise InitializationError(f"Conflict: list {name!r} is defined both in config.json and in {name}.txt "
                                      f"file. If it's a {_CONF.TYPE.WORDS!r} or {_CONF.TYPE.PHRASES!r} list, "
                                      f"you should remove it from config.json - {name}.txt file is enough.")
        config[name] = wordlist
    return config


def filter_config(config: CoolnameConfigT, word_filter: Callable[[str], bool]) -> None:
    """
    Filter words and phrases according to predicate.

    It can be used in customized :py:class:`RandomGenerator` initialization,
    but mostly it's for config manipulation at development time.

    How it works:

    * Keep only words with ``word_filter(x) == True``.
    * Keep only phrases with ``all(word_filter(x) for x in phrase)``.
    * Types and values are *not* checked - assuming config is valid.
    * Any list becoming empty after filtering is considered an error.

     Raises :py:class:`InitializationError` if something goes wrong.
     Unexpected exceptions or silent errors may occur if config is invalid.
    """
    for list_name, list_config in config.items():
        match list_config[_CONF.FIELD.TYPE]:
            case _CONF.TYPE.WORDS:
                list_config[_CONF.FIELD.WORDS] = [x for x in cast(list[str], list_config[_CONF.FIELD.WORDS])
                                                  if word_filter(x)]
                if not list_config[_CONF.FIELD.WORDS]:
                    raise InitializationError(f'word_filter returned empty list for words list {list_name!r}')
            case _CONF.TYPE.PHRASES:
                try:
                    phrase_filter = PhraseSplitter.phrase_filter(list_config, word_filter, list_name=list_name)
                    list_config[_CONF.FIELD.PHRASES] = [
                        x for x in cast(list[list[str]],  # this cast is a lie to shut up mypy :-(
                                        list_config[_CONF.FIELD.PHRASES]) if phrase_filter(x)
                    ]
                except Exception as ex:
                    raise InitializationError(f'word_filter failed for phrase list {list_name!r}: {ex}')
                if not list_config[_CONF.FIELD.PHRASES]:
                    raise InitializationError(f'word_filter returned empty list for phrase list {list_name!r}')


def save_config_as_module(config: CoolnameConfigT, filename: str | Path) -> None:
    """
    Save configuration dictionary as Python module (``*.py`` file).
    """
    with open(filename, 'w', encoding='utf-8', newline='') as file:
        file.write(f"# THIS FILE IS AUTO-GENERATED, DO NOT EDIT\n"
                   f"# {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S%:z')}\n"
                   f"config = {config!r}\n")


def _load_data(path: Path) -> tuple[CoolnameConfigT, dict[str, CoolnameConfigListT]]:
    """
    Loads data from a directory.
    Returns tuple (config_dict, wordlists).
    Raises Exception on failure (e.g. if data is corrupted).
    """
    path = path.absolute()
    if not path.is_dir():
        raise InitializationError(f'Directory not found: {path}')
    wordlists = {}
    for file_path in path.glob('*.txt'):
        try:
            with open(file_path, encoding='utf-8') as file:
                wordlists[file_path.stem] = _load_wordlist(file_path.stem, file)
        except (OSError, FileNotFoundError) as ex:
            raise InitializationError(f'Failed to read {file_path}: {ex}')
    return _load_config(path / 'config.json'), wordlists


def _load_config(config_file_path: Path) -> CoolnameConfigT:
    try:
        with open(config_file_path, encoding='utf-8') as file:
            return cast(CoolnameConfigT, json.load(file))
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


def _load_wordlist(name: str, stream: TextIO) -> CoolnameConfigListT:
    """
    Loads list of words or phrases from *.txt file.

    Returns "words" or "phrases" dictionary, the same as used in config.
    Raises Exception if file is missing or invalid.
    """
    words: list[str] = []
    phrases: list[list[str]] = []
    max_length: int | None = None
    multiword = False
    number_of_words: int | None = None
    for i, line in enumerate(stream, start=1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        # Is it an option line, e.g. 'max_length = 10'?
        if '=' in line:
            if words or phrases:
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
            continue
        # Parse words
        if not multiword and _WORD_REGEX.match(line):
            if max_length is not None and len(line) > max_length:
                raise ConfigurationError(f'Word is too long at list {name!r} line {i}: {line!r}')
            words.append(line)
        elif _PHRASE_REGEX.match(line):
            if not multiword:
                multiword = True
            phrase = line.split(' ')
            if number_of_words is not None and len(phrase) != number_of_words:
                raise ConfigurationError(f'Phrase has {len(phrase)} word(s) (while number_of_words={number_of_words}) '
                                         f'at list {name!r} line {i}: {line!r}')
            if max_length is not None and sum(len(x) for x in phrase) > max_length:
                raise ConfigurationError(f'Phrase is too long at list {name!r} line {i}: {line!r}')
            phrases.append(phrase)
        else:
            raise ConfigurationError(f'Invalid syntax at list {name!r} line {i}: {line!r}')
    result: CoolnameConfigListT
    if multiword:
        # If in phrase mode, push all words we encountered before the first phrase into phrases
        result = {
            _CONF.FIELD.TYPE: _CONF.TYPE.PHRASES,
            _CONF.FIELD.PHRASES: [[x] for x in words] + phrases
        }
        if number_of_words is not None:
            result[_CONF.FIELD.NUMBER_OF_WORDS] = number_of_words
    else:
        result = {
            _CONF.FIELD.TYPE: _CONF.TYPE.WORDS,
            _CONF.FIELD.WORDS: words
        }
    if max_length is not None:
        result[_CONF.FIELD.MAX_LENGTH] = max_length
    return result
