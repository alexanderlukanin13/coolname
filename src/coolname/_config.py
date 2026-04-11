import re
from typing import cast, Callable

from coolname.types import CoolnameConfigListT


class _CONF:
    """All strings related to config, to avoid hardcoding."""

    class TYPE:
        """Node type in configuration."""
        NESTED = 'nested'
        CARTESIAN = 'cartesian'
        WORDS = 'words'
        PHRASES = 'phrases'
        CONST = 'const'

    class FIELD:
        """Allowed fields."""
        TYPE = 'type'
        LISTS = 'lists'
        WORDS = 'words'
        PHRASES = 'phrases'
        NUMBER_OF_WORDS = 'number_of_words'
        VALUE = 'value'
        GENERATOR = 'generator'
        MAX_LENGTH = 'max_length'
        MAX_SLUG_LENGTH = 'max_slug_length'
        ENSURE_UNIQUE = 'ensure_unique'
        ENSURE_UNIQUE_PREFIX = 'ensure_unique_prefix'
        ALLOW_WHITESPACE = 'allow_whitespace'
        STRIP_WHITESPACE = 'strip_whitespace'
        SEPARATOR = 'separator'


class PhraseSplitterError(ValueError):
    """
    Error on initialization or call to phrase splitter.

    Subclasses ValueError to be used directly in validate_config
    without catching and re-raising.
    """


class PhraseSplitter:
    """Splits phrase (as a string) into list."""

    DEFAULT_SEPARATOR = r're:\s+'
    UNKNOWN_KEY = '<???>'

    _split: Callable[[str], list[str]]

    # Note: list_name is used solely for more user-friendly error messages
    def __init__(self, separator: str = DEFAULT_SEPARATOR, *,
                 strip_whitespace: bool = True, list_name: str = UNKNOWN_KEY):
        if separator.startswith('re:'):
            separator = separator[3:]
            try:
                self._split = re.compile(separator).split
            except re.error as ex:
                raise PhraseSplitterError(f'Config at key {list_name!r} has invalid {_CONF.FIELD.SEPARATOR!r}: {ex}')
        else:
            def split(s: str) -> list[str]:
                return s.split(separator)
            self._split = split
        self._strip_whitespace = strip_whitespace
        self._list_name = list_name

    @classmethod
    def from_config(cls, list_config: CoolnameConfigListT, *, list_name: str = UNKNOWN_KEY) -> 'PhraseSplitter':
        return PhraseSplitter(
            cast(str, list_config.get(_CONF.FIELD.SEPARATOR, cls.DEFAULT_SEPARATOR)),
            strip_whitespace=cast(bool, list_config.get(_CONF.FIELD.STRIP_WHITESPACE, True)),
            list_name=list_name
        )

    def __call__(self, s: str, /) -> list[str]:
        _s = s
        if not s:
            raise PhraseSplitterError(f'Config at key {self._list_name!r} has invalid {_CONF.FIELD.PHRASES!r}: '
                                      f'empty phrase not allowed')
        if self._strip_whitespace:
            s = s.strip()
            if not s:
                raise PhraseSplitterError(f'Config at key {self._list_name!r} has invalid {_CONF.FIELD.PHRASES!r}: '
                                          f'whitespace-only phrase not allowed')
        if self._strip_whitespace:
            items = [x.strip() for x in self._split(s)]
        else:
            items = self._split(s)
        if any(not x for x in items):
            raise PhraseSplitterError(f'Config at key {self._list_name!r} has invalid {_CONF.FIELD.PHRASES!r}: '
                                      f"can't split phrase {_s!r} nicely into words - refusing to guess")
        return items

    @classmethod
    def phrase_filter(cls, list_config: CoolnameConfigListT,
                      word_filter: Callable[[str], bool], *,
                      list_name: str = UNKNOWN_KEY) -> Callable[[str | list[str] | tuple[str, ...]], bool]:
        split = cls.from_config(list_config, list_name=list_name)

        def phrase_filter_(s: str | list[str] | tuple[str, ...]) -> bool:
            if isinstance(s, str):
                s = split(s)
            return all(word_filter(x) for x in s)

        return phrase_filter_
