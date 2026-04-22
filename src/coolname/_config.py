import re
from typing import cast, Callable

from coolname.types import CoolnameConfigListT, CoolnameConfigT


class _CONF:
    """All strings related to config, to avoid hardcoding."""

    class TYPE:
        """Node type in configuration."""
        NESTED = 'nested'
        CARTESIAN = 'cartesian'
        WORDS = 'words'
        PHRASES = 'phrases'
        CONST = 'const'
        NUMBER = 'number'

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
        WORD_REGEX = 'word_regex'
        NUMBER_DIGITS = 'digits'

    NUMBER_DIGITS_DEFAULT = 3
    NUMBER_DIGITS_MAX = 7

    @classmethod
    def all_fields(cls) -> list[str]:
        return [getattr(cls.FIELD, x) for x in dir(cls.FIELD) if x.isupper()]

    WORD_REGEX_DEFAULT = r'\w+'  # any Unicode letters, numbers and underscores

    @staticmethod
    def get_parameter(config: CoolnameConfigT, key: str, parameter: str) -> int | bool | str | None:
        """
        Get configuration parameter from a list named ``key``, if defined;
        fall back to same parameter in 'all', if defined.

        Raises ValueError if something is wrong with the config.
        """
        if key != 'all':
            key_list = config[key]
            value = key_list.get(parameter)
            if value is not None:
                return cast(int | bool | str, value)
        try:
            all_list = config['all']
        except KeyError:
            raise ValueError("Config must have 'all' key")
        if not isinstance(all_list, dict):
            raise ValueError("Config at key 'all' is not a dict")
        return cast(int | bool | str | None, all_list.get(parameter))

    @classmethod
    def get_parameter_str(cls, config: CoolnameConfigT, key: str, parameter: str, default: str) -> str | None:
        value = cls.get_parameter(config, key, parameter)
        if value is None:
            return default
        if not isinstance(value, str):
            raise ValueError(f"Config at key 'all' has invalid {parameter}: must be a string")
        return value

    @classmethod
    def get_parameter_bool(cls, config: CoolnameConfigT, key: str, parameter: str, default: bool) -> bool | None:
        value = cls.get_parameter(config, key, parameter)
        if value is None:
            return default
        if not isinstance(value, bool):
            raise ValueError(f"Config at key 'all' has invalid {parameter}: must be a boolean")
        return value

    @classmethod
    def get_parameter_match(cls, config: CoolnameConfigT, key: str, parameter: str,
                            default: str) -> Callable[[str], re.Match[str] | None] | None:
        value = cls.get_parameter_str(config, key, parameter, default)
        if value is None:  # pragma: no cover
            return None
        try:
            return re.compile(value).fullmatch
        except re.error as ex:
            raise ValueError(f"Config at key 'all' has invalid {_CONF.FIELD.WORD_REGEX}: {ex}")


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
        self._separator = separator
        if separator.startswith('re:'):
            separator = separator[3:]
            try:
                self._split = re.compile(separator).split
            except re.error as ex:
                raise PhraseSplitterError(f'Config at key {list_name!r} has invalid '
                                          f'{_CONF.FIELD.SEPARATOR} {self._separator!r}: {ex}')
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
                                      f'empty phrase is not allowed')
        if self._strip_whitespace:
            s = s.strip()
            if not s:
                raise PhraseSplitterError(f'Config at key {self._list_name!r} has invalid {_CONF.FIELD.PHRASES!r}: '
                                          f'whitespace-only phrase is not allowed '
                                          f'with {_CONF.FIELD.STRIP_WHITESPACE}=True')
        if self._strip_whitespace:
            items = [x.strip() for x in self._split(s)]
        else:
            items = self._split(s)
        if any(not x for x in items):
            raise PhraseSplitterError(f'Config at key {self._list_name!r} has invalid {_CONF.FIELD.PHRASES!r}: '
                                      f"can't split phrase {_s!r} nicely into words using separator "
                                      f"{self._separator!r} - refusing to guess")
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
