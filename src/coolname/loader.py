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
    config = _load_config(path / 'config.json')
    try:
        separator_all = cast(str, _CONF.get_parameter_str(config, 'all',
                                                          _CONF.FIELD.SEPARATOR, PhraseSplitter.DEFAULT_SEPARATOR))
        strip_whitespace_all = cast(bool, _CONF.get_parameter_bool(config, 'all',
                                                                   _CONF.FIELD.STRIP_WHITESPACE, True))
    except ValueError as ex:
        raise ConfigurationError(str(ex))
    wordlists = {}
    for file_path in path.glob('*.txt'):
        try:
            with open(file_path, encoding='utf-8') as file:
                wordlists[file_path.stem] = _load_wordlist(file_path.stem, file,
                                                           separator=separator_all,
                                                           strip_whitespace=strip_whitespace_all)
        except (OSError, FileNotFoundError) as ex:
            raise InitializationError(f'Failed to read {file_path}: {ex}')
    return config, wordlists


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
# Value can be int, bool or an arbitrary string surrounded by zero or more spaces
_match_option = re.compile(r'\s*([a-z_]+)\s*=\s*(\S.*?)\s*').fullmatch
_INT_OPTIONS: list[str] = [
    _CONF.FIELD.MAX_LENGTH,
    _CONF.FIELD.NUMBER_OF_WORDS,
]
_BOOL_OPTIONS: list[str] = [
    _CONF.FIELD.ALLOW_WHITESPACE,
    _CONF.FIELD.STRIP_WHITESPACE,
    _CONF.FIELD.GENERATOR,  # doesn't make practical sense, but we allow it for consistency
]
_STRING_OPTIONS: list[str] = [
    _CONF.FIELD.SEPARATOR,
    _CONF.FIELD.WORD_REGEX
]


def _parse_option(line: str) -> tuple[str, int | bool | str]:
    """
    Parses option line.
    Returns (name, value).
    Raises ValueError on invalid syntax or unknown option.
    """
    m = _match_option(line)
    if not m:
        raise ValueError('Invalid syntax')
    name = m.group(1)
    if name in _INT_OPTIONS:
        return name, int(m.group(2))
    elif name in _BOOL_OPTIONS:
        match m.group(2).lower():
            case '0' | 'false' | 'no':
                return name, False
            case '1' | 'true' | 'yes':
                return name, True
            case _:
                raise ValueError('Parameter must be a valid boolean')
    elif name in _STRING_OPTIONS:
        return name, m.group(2).strip()
    elif name in _CONF.all_fields():
        raise ValueError(f'Parameter {name} is not allowed in *.txt files')
    else:
        raise ValueError('Unknown parameter')


def _load_wordlist(name: str, stream: TextIO,
                   separator: str = PhraseSplitter.DEFAULT_SEPARATOR,
                   strip_whitespace: bool = True) -> CoolnameConfigListT:
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
    split = PhraseSplitter(separator, strip_whitespace=strip_whitespace, list_name=name)
    extra_options = {}
    for i, line in enumerate(stream, start=1):
        if '#' in line:
            line = line.split('#')[0]
        line = line.strip()
        if not line:
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
            match option:
                case _CONF.FIELD.MAX_LENGTH:
                    max_length = cast(int, option_value)
                case _CONF.FIELD.NUMBER_OF_WORDS:
                    number_of_words = cast(int, option_value)
                    if number_of_words > 1:
                        multiword = True
                case _CONF.FIELD.STRIP_WHITESPACE:
                    strip_whitespace = cast(bool, option_value)
                    split = PhraseSplitter(separator, strip_whitespace=strip_whitespace, list_name=name)
                case _CONF.FIELD.SEPARATOR:
                    separator = cast(str, option_value)
                    split = PhraseSplitter(separator, strip_whitespace=strip_whitespace, list_name=name)
                case _CONF.FIELD.ALLOW_WHITESPACE | _CONF.FIELD.GENERATOR | _CONF.FIELD.WORD_REGEX:
                    pass
                case _:  # pragma: no cover
                    # This should never happen unless we add parameter to _parse_option and forget to add it here too
                    raise ConfigurationError(f'Invalid assignment at list {name!r} line {i}: {line!r} '
                                             f'(unexpected option)')
            extra_options[option] = option_value
            continue
        # Parse words
        items = split(line)
        # It's a word?
        if not multiword:
            if len(items) == 1:
                word = items[0]
                if max_length is not None and len(word) > max_length:
                    raise ConfigurationError(f'Word is too long at list {name!r} line {i}: {word!r}')
                words.append(word)
                continue
            else:  # switch to multiword (phrase) mode
                multiword = True
        # It's a phrase?
        if number_of_words is not None and len(items) != number_of_words:
            raise ConfigurationError(f'Phrase has {len(items)} word(s) (while number_of_words={number_of_words}) '
                                     f'at list {name!r} line {i}: {line!r}')
        if max_length is not None and sum(len(x) for x in items) > max_length:
            raise ConfigurationError(f'Phrase is too long at list {name!r} line {i}: {line!r}')
        phrases.append(items)

    result: CoolnameConfigListT
    if multiword:
        # If in phrase mode, push all words we encountered before the first phrase into phrases
        result = {
            _CONF.FIELD.TYPE: _CONF.TYPE.PHRASES,
            _CONF.FIELD.PHRASES: [[x] for x in words] + phrases
        }
    else:
        result = {
            _CONF.FIELD.TYPE: _CONF.TYPE.WORDS,
            _CONF.FIELD.WORDS: words
        }
    result.update(extra_options)
    return result
