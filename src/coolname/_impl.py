import re
from copy import deepcopy
from functools import partial
import hashlib
import itertools
import typing
from typing import Callable, cast, ClassVar, Iterable

from ._config import _CONF, PhraseSplitter
from .exceptions import ConfigurationError, InitializationError
from .types import HashT, CoolnameConfigT, ListLike


# For new Python versions with (possible) OpenSSL FIPS support,
# we should pass usedforsecurity=False argument to md5().
_md5: Callable[[], HashT]
try:
    hashlib.md5(b'', usedforsecurity=False)  # noqa
    _md5 = partial(hashlib.md5, usedforsecurity=False)
except TypeError:  # pragma: no cover
    _md5 = hashlib.md5


class AbstractNestedList(ListLike):

    length: int
    multiword: bool

    _lists: list[ListLike]

    MULTIWORD: ClassVar[bool] = False

    def __init__(self, lists: list[ListLike] | list[list[str]]):
        super().__init__()
        # Note: we can't use isinstance() here because issubclass(WordList, list) == True
        self._lists = [WordList(x) if type(x) is list else cast(ListLike, x) for x in lists]
        # If this is set to True in a subclass,
        # then subclass yields sequences instead of single words.
        self.multiword = any(x.multiword for x in self._lists) or self.MULTIWORD  # order matters

    def __str__(self) -> str:
        return f'{self.__class__.__name__}({len(self._lists)}, len={self.length})'

    def __repr__(self) -> str:
        return self.__str__()

    def __getitem__(self, item: int) -> str | list[str]:
        raise NotImplementedError  # pragma: no cover

    def squash(self, hard: bool, cache: dict[bytes, ListLike]) -> ListLike:
        if len(self._lists) == 1:
            return self._lists[0].squash(hard, cache)
        else:
            self._lists = [x.squash(hard, cache) for x in self._lists]
            return self

    def write(self, stream: typing.TextIO, *,
              indent: str = '  ', base_indent: str = '',
              max_items: int = 4, ids: bool = False
              ) -> None:
        stream.write(f"{base_indent}{self.render(max_items=max_items)}" +
                     (f'  # id={id(self)}' if ids else '') + '\n')
        base_indent += indent
        for sublist in self._lists:
            sublist.write(stream, indent=indent, max_items=max_items,
                          base_indent=base_indent, ids=ids)  # noqa


# Convert value to bytes, for hashing
# (used to calculate WordList or PhraseList hash)
def _to_bytes(value: str | tuple[str, ...] | bytes) -> bytes:
    if isinstance(value, str):
        return value.encode('utf-8')
    elif isinstance(value, tuple):
        return str(value).encode('utf-8')
    else:
        return value


# Base class for WordList and PhraseList
class _BasicList(list[typing.Any], AbstractNestedList):

    length: int

    __hash: bytes | None

    def __init__(self, sequence: list[str] | list[tuple[str, ...]]):
        list.__init__(self, sequence)
        AbstractNestedList.__init__(self, [])
        self.length = len(self)
        self.__hash = None

    def render(self, *, max_items: int = 4) -> str:
        it: Iterable[str] = (repr(x) for x in itertools.islice(self, max_items))
        if self.length > max_items:
            it = itertools.chain(it, ['...'])
        return f'{self.__class__.__name__}([{", ".join(it)}], len={len(self)})'

    def __str__(self) -> str:
        return self.render()

    def __repr__(self) -> str:
        return self.__str__()

    def squash(self, hard: bool, cache: dict[bytes, ListLike]) -> ListLike:
        return self

    @property
    def _hash(self) -> bytes:
        if self.__hash is not None:
            return self.__hash
        md5 = _md5()
        md5.update(_to_bytes(str(len(self))))
        for x in self:  # noqa
            md5.update(_to_bytes(x))
        self.__hash = md5.digest()
        return self.__hash


class WordList(_BasicList):
    """List of single words."""


class PhraseList(_BasicList):
    """List of phrases (sequences of one or more words)."""

    MULTIWORD: ClassVar[bool] = True

    def __init__(self, lst: list[tuple[str, ...] | list[str]]):
        # Accept mixed input, ensure that we store only tuple[str, ...]
        _BasicList.__init__(self, [tuple(x) for x in lst])


class WordAsPhraseWrapper(ListLike):

    MULTIWORD: ClassVar[bool] = True

    length: int

    _list: ListLike

    def __init__(self, wordlist: WordList):
        self._list = wordlist
        self.length = len(wordlist)
        self.multiword = True

    def __len__(self) -> int:
        return self.length

    def __getitem__(self, i: int) -> str | list[str]:
        return [cast(str, self._list[i])]

    def squash(self, hard: bool, cache: dict[bytes, ListLike]) -> ListLike:  # noqa
        return self

    def write(self, stream: typing.TextIO, *,
              indent: str = '  ', base_indent: str = '',
              max_items: int = 4, ids: bool = False
              ) -> None:
        stream.write(f"{base_indent}{self.__class__.__name__}{f'  # id={id(self)}' if ids else ''}\n")
        base_indent += indent
        self._list.write(stream, indent=indent, base_indent=base_indent,
                         max_items=max_items, ids=ids)

    def __str__(self) -> str:
        return f'{self.__class__.__name__}({self._list})'

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self._list!r})'


class TopLevelMultiWrapper(WordAsPhraseWrapper):
    """
    For abnormal but possible cases when there's no multiword list at the top generator level.
    """

    def __init__(self, lst: ListLike):  # noqa
        # Note that call to base class is omitted deliberately
        self._list = lst
        self.length = lst.length
        self.multiword = True


class NestedList(AbstractNestedList):

    def __init__(self, lists: list[ListLike] | list[list[str]]):
        super().__init__(lists)
        # If user mixes WordList and PhraseList in the same NestedList,
        # we need to make sure that __getitem__ always returns tuple.
        # For that, we wrap WordList instances.
        # Note that such mixing decreases performance somewhat, and it is avoided in default config.
        if any(isinstance(x, WordList) for x in self._lists) and any(x.multiword for x in self._lists):
            self._lists = [WordAsPhraseWrapper(x) if isinstance(x, WordList) else x for x in self._lists]
        # Fattest lists first (to reduce average __getitem__ time)
        self._lists.sort(key=lambda x: -x.length)
        self.length = sum(x.length for x in self._lists)

    def __getitem__(self, i: int) -> str | list[str]:
        # Retrieve item from appropriate list
        for x in self._lists:
            n = x.length
            if i < n:
                return x[i]
            else:
                i -= n
        raise IndexError('list index out of range')

    def squash(self, hard: bool, cache: dict[bytes, ListLike]) -> ListLike:
        # Cache is used to avoid data duplication.
        # If we have 4 branches which finally point to the same list of nouns,
        # why not using the same WordList instance for all 4 branches?
        # This optimization is also applied to PhraseLists, just in case.
        result = super().squash(hard, cache)
        if result is self and hard:
            for cls in (WordList, PhraseList):
                if all(isinstance(x, cls) for x in self._lists):
                    # Creating combined WordList/PhraseList and then checking cache
                    # is a little wasteful, but it has no long-term consequences.
                    # And it's simple!
                    result = cls(sorted(set(itertools.chain.from_iterable(cast(list[_BasicList], self._lists)))))
                    try:
                        result = cache[cast(_BasicList, result)._hash]
                    except KeyError:
                        cache[cast(_BasicList, result)._hash] = result
                    break
        return result


class CartesianList(AbstractNestedList):

    MULTIWORD: ClassVar[bool] = True

    length: int

    def __init__(self, lists: list[ListLike] | list[list[str]]):
        super().__init__(lists)
        self.length = 1
        for x in self._lists:
            self.length *= x.length
        # Let's say list lengths are 5, 7, 11, 13.
        # divs = [7*11*13, 11*13, 13, 1]
        divs = [1]
        prod = 1
        for x in reversed(self._lists[1:]):
            prod *= x.length
            divs.append(prod)
        self._list_divs = tuple(zip(self._lists, reversed(divs)))

    def __getitem__(self, i: int) -> str | list[str]:
        result: list[str] = []
        for sublist, n in self._list_divs:
            x = sublist[i // n]
            if sublist.multiword:
                result.extend(cast(list[str], x))
            else:
                result.append(cast(str, x))
            i %= n
        return result


class Constant(AbstractNestedList):

    length: int
    value: str

    def __init__(self, value: str):
        super().__init__([])
        self.value = value
        self.length = 1

    def __getitem__(self, i: int) -> str:
        return self.value

    def __str__(self) -> str:
        return f'{self.__class__.__name__}(value={self.value!r})'

    def random(self) -> str:
        return self.value


class Number(ListLike):

    length: int
    multiword: bool

    def __init__(self, digits: int):
        super().__init__()
        self.digits = digits
        self.length = 10 ** digits - 1
        self.multiword = False

    def __getitem__(self, item: int) -> str:
        return str(item + 1)

    def squash(self, hard: bool, cache: dict[bytes, 'ListLike']) -> 'ListLike':
        return self

    def write(self, stream: typing.TextIO, *,
              indent: str = '  ', base_indent: str = '',
              max_items: int = 4, ids: bool = False,
              ) -> None:
        stream.write(f'{base_indent}Number(digits={self.digits!r})\n')


_remove_whitespace = partial(re.compile(r'\s+').sub, '')

class MatchWordIgnoreWhitespace:

    def __init__(self, match_word: Callable[[str], re.Match[str] | None]):
        self.match_word = match_word

    def __call__(self, s: str) -> re.Match[str] | None:
        return self.match_word(_remove_whitespace(s))


def validate_and_normalize_config(config: CoolnameConfigT) -> None:
    """
    A big and ugly function for config validation.
    It would be nice to use something like cerberus,
    but we don't want to introduce dependencies just for that.

    Also, this function normalizes words and phrases
    (strip whitespace, use custom separators, etc.).
    """
    _space = re.compile(r'\s+').search
    try:
        # Validate 'all' dict
        if not isinstance(config, dict):
            raise ValueError(f'Expected config dict, got {config.__class__.__qualname__}')
        try:
            all_list = config['all']
        except KeyError:
            raise ValueError("Config must have 'all' key")
        if not isinstance(all_list, dict):
            raise ValueError("Config at key 'all' is not a dict")

        referenced_sublists: set[str] = set()
        for key, listdef in list(config.items()):
            # Check if section is a dict
            if not isinstance(listdef, dict):
                raise ValueError(f'Value at key {key!r} is not a dict')
            # Check if it has correct type
            if _CONF.FIELD.TYPE not in listdef:
                raise ValueError(f'Config at key {key!r} has no {_CONF.FIELD.TYPE!r}')
            # Get parameters
            strip_spaces = _CONF.get_parameter_bool(config, key, _CONF.FIELD.STRIP_WHITESPACE, default=True)
            allow_spaces = _CONF.get_parameter_bool(config, key, _CONF.FIELD.ALLOW_WHITESPACE, default=False)
            word_regex = _CONF.get_parameter_str(config, key, _CONF.FIELD.WORD_REGEX, _CONF.WORD_REGEX_DEFAULT)
            match_word = _CONF.get_parameter_match(config, key, _CONF.FIELD.WORD_REGEX, _CONF.WORD_REGEX_DEFAULT)
            if match_word and allow_spaces:
                match_word = MatchWordIgnoreWhitespace(match_word)
            # Nested or Cartesian
            if listdef[_CONF.FIELD.TYPE] in (_CONF.TYPE.NESTED, _CONF.TYPE.CARTESIAN):
                sublists = listdef.get(_CONF.FIELD.LISTS)
                if sublists is None:
                    raise ValueError(f'Config at key {key!r} has no {_CONF.FIELD.LISTS!r}')
                if (not isinstance(sublists, list) or not sublists or
                        not all(isinstance(x, str) for x in sublists)):
                    raise ValueError(f'Config at key {key!r} has invalid {_CONF.FIELD.LISTS!r}')
                referenced_sublists.update(cast(list[str], sublists))
            # Const
            elif listdef[_CONF.FIELD.TYPE] == _CONF.TYPE.CONST:
                try:
                    value = listdef[_CONF.FIELD.VALUE]
                except KeyError:
                    raise ValueError(f'Config at key {key!r} has no {_CONF.FIELD.VALUE!r}')
                if not isinstance(value, str):
                    raise ValueError(f'Config at key {key!r} has invalid {_CONF.FIELD.VALUE!r} (must be a string)')
                if match_word is not None and not match_word(value):
                    raise ValueError(f"Config at key {key!r} has invalid {_CONF.FIELD.VALUE!r} "
                                     f"(doesn't match {_CONF.FIELD.WORD_REGEX}={word_regex!r})")
            # Words
            elif listdef[_CONF.FIELD.TYPE] == _CONF.TYPE.WORDS:
                try:
                    words = listdef[_CONF.FIELD.WORDS]
                except KeyError:
                    raise ValueError(f'Config at key {key!r} has no {_CONF.FIELD.WORDS!r}')
                if not isinstance(words, list):
                    raise ValueError(f'Config at key {key!r} has invalid {_CONF.FIELD.WORDS!r}: '
                                     f'expected list[str], got {words.__class__.__qualname__}')
                if not words:
                    raise ValueError(f'Config at key {key!r} has invalid {_CONF.FIELD.WORDS!r}: list is empty')
                # Validate word length
                try:
                    max_length = int(listdef[_CONF.FIELD.MAX_LENGTH])  # type: ignore[arg-type]
                except KeyError:
                    max_length = None
                for i, word in enumerate(words):
                    _word = word
                    if not isinstance(word, str):
                        raise ValueError(f'Config at key {key!r} has invalid {_CONF.FIELD.WORDS!r}: '
                                         f'expected all words to be str, got {_word!r}')
                    if not word:
                        raise ValueError(f'Config at key {key!r} has invalid {_CONF.FIELD.WORDS!r}: '
                                         f'empty word is not allowed')
                    if strip_spaces:
                        word = word.strip()
                        if not word:
                            raise ValueError(f'Config at key {key!r} has invalid {_CONF.FIELD.WORDS!r}: '
                                             f'whitespace-only word {_word!r} is not allowed')
                    if not allow_spaces and _space(word) is not None:
                        raise ValueError(f'Config at key {key!r} has invalid {_CONF.FIELD.WORDS!r}: '
                                         f'word {_word!r} contains whitespace while '
                                         f'{_CONF.FIELD.STRIP_WHITESPACE}={strip_spaces!r}, '
                                         f'{_CONF.FIELD.ALLOW_WHITESPACE}={allow_spaces!r}')
                    if match_word is not None and not match_word(word):
                        raise ValueError(f"Config at key {key!r} has invalid {_CONF.FIELD.WORDS!r}: "
                                         f"word {_word!r} doesn't match "
                                         f"{_CONF.FIELD.WORD_REGEX}={word_regex!r}")
                    if max_length is not None and len(word) > max_length:
                        raise ValueError(f'Config at key {key!r} has invalid word {_word!r} '
                                         f'(longer than {max_length} characters)')
                    if word != _word:
                        words[i] = word  # type: ignore
            # Phrases (sequences of one or more words)
            elif listdef[_CONF.FIELD.TYPE] == _CONF.TYPE.PHRASES:
                try:
                    phrases = listdef[_CONF.FIELD.PHRASES]
                except KeyError:
                    raise ValueError(f'Config at key {key!r} has no {_CONF.FIELD.PHRASES!r}')
                if not isinstance(phrases, list):
                    raise ValueError(f'Config at key {key!r} has invalid {_CONF.FIELD.PHRASES!r}: '
                                     f'expected list[str] | list[list[str]] | list[tuple[str, ...]], '
                                     f'got {phrases.__class__.__qualname__}')
                if not phrases:
                    raise ValueError(f'Config at key {key!r} has invalid {_CONF.FIELD.PHRASES!r}: list is empty')
                # Validate multi-word and max length
                try:
                    number_of_words = int(listdef[_CONF.FIELD.NUMBER_OF_WORDS])  # type: ignore[arg-type]
                except KeyError:
                    number_of_words = None
                try:
                    max_length = int(listdef[_CONF.FIELD.MAX_LENGTH])  # type: ignore[arg-type]
                except KeyError:
                    max_length = None
                # Note: PhraseSplitter raises errors compatible with standard ValueError format,
                # so we don't wrap it in try-except
                split = PhraseSplitter.from_config(listdef, list_name=key)
                for i, phrase in enumerate(phrases):
                    _phrase = deepcopy(phrase)  # for accurate error reporting, since list[list]
                    if not phrase:  # empty list or string - same message
                        raise ValueError(f'Config at key {key!r} has invalid {_CONF.FIELD.PHRASES!r}: '
                                         f'empty phrase is not allowed')
                    if isinstance(phrase, str):
                        phrase = split(phrase)  # str -> sequence, if necessary
                    if not isinstance(phrase, (tuple, list)) or not all(isinstance(x, str) for x in phrase):
                        raise ValueError(f'Config at key {key!r} has invalid {_CONF.FIELD.PHRASES!r}: '
                                         f'expected all phrases to be str | list[str] | tuple[str, ...], '
                                         f'got {_phrase!r}')
                    if not all(phrase):
                        raise ValueError(f'Config at key {key!r} has invalid {_CONF.FIELD.PHRASES!r}: '
                                         f'empty word within phrase {_phrase!r} is not allowed')
                    if strip_spaces:
                        phrase = [x.strip() for x in phrase]
                        if not all(phrase):
                            raise ValueError(f'Config at key {key!r} has invalid {_CONF.FIELD.PHRASES!r}: '
                                             f'whitespace-only word within phrase {_phrase!r} is not allowed '
                                             f'while {_CONF.FIELD.STRIP_WHITESPACE}={strip_spaces!r}')
                        if not allow_spaces and any(_space(x) is not None for x in phrase):
                            raise ValueError(f'Config at key {key!r} has invalid {_CONF.FIELD.PHRASES!r}: '
                                             f'word within phrase {_phrase!r} contains whitespace while '
                                             f'{_CONF.FIELD.STRIP_WHITESPACE}={strip_spaces!r}, '
                                             f'{_CONF.FIELD.ALLOW_WHITESPACE}={allow_spaces!r}')
                    if match_word is not None and not all(match_word(x) for x in phrase):
                        raise ValueError(f"Config at key {key!r} has invalid {_CONF.FIELD.PHRASES!r}: "
                                         f"word within phrase {_phrase!r} doesn't match "
                                         f"{_CONF.FIELD.WORD_REGEX}={word_regex!r}")
                    if number_of_words is not None and len(phrase) != number_of_words:
                        raise ValueError(f'Config at key {key!r} has invalid phrase {_phrase!r} '
                                         f'({len(phrase)} word(s) but '
                                         f'{_CONF.FIELD.NUMBER_OF_WORDS}={number_of_words})')
                    if max_length is not None and sum(len(word) for word in phrase) > max_length:
                        raise ValueError(f'Config at key {key!r} has invalid phrase {_phrase} '
                                         f'(longer than {max_length} characters)')
                    if phrase != _phrase:
                        phrases[i] = phrase    # type: ignore
            elif listdef[_CONF.FIELD.TYPE] == _CONF.TYPE.NUMBER:
                number_digits = int(listdef.get(_CONF.FIELD.NUMBER_DIGITS, _CONF.NUMBER_DIGITS_DEFAULT))  # type:ignore
                if not (0 < number_digits <= _CONF.NUMBER_DIGITS_MAX):
                    raise ValueError(f"Config at key {key!r} has invalid {_CONF.FIELD.NUMBER_DIGITS!r}: "
                                     f"must be between 1 and {_CONF.NUMBER_DIGITS_MAX}")
            else:
                raise ValueError(f'Config at key {key!r} has invalid {_CONF.FIELD.TYPE!r}')
        # Check that all sublists are defined
        diff = referenced_sublists.difference(config.keys())
        if diff:
            raise ValueError(f'Lists are referenced but not defined: {", ".join(sorted(diff)[:10])}')
    except (KeyError, ValueError) as ex:
        raise ConfigurationError(str(ex))


def create_lists(
        config: CoolnameConfigT,
        results: dict[str, ListLike],
        current: str,
        stack: list[str],
        inside_cartesian: str | None = None
) -> ListLike:
    """
    An ugly recursive method to transform config dict
    into a tree of AbstractNestedList.
    """
    # Have we done it already?
    try:
        return results[current]
    except KeyError:
        pass
    # Check recursion depth and detect loops
    if current in stack:
        raise ConfigurationError(f'Rule {stack[0]!r} is recursive: {stack!r}')
    if len(stack) > 99:
        raise ConfigurationError(f'Rule {stack[0]!r} is too deep')
    # Track recursion depth
    stack.append(current)
    try:
        # Check what kind of list we have
        list_config = config[current]
        list_type = list_config[_CONF.FIELD.TYPE]
        # 1. List of words
        if list_type == _CONF.TYPE.WORDS:
            _ = list_config[_CONF.FIELD.WORDS]
            assert isinstance(_, list)
            results[current] = WordList(_)
        # List of phrases
        elif list_type == _CONF.TYPE.PHRASES:
            _ = list_config[_CONF.FIELD.PHRASES]
            assert isinstance(_, list)
            results[current] = PhraseList(_)
        # 2. Simple list of lists
        elif list_type == _CONF.TYPE.NESTED:
            _ = list_config[_CONF.FIELD.LISTS]
            assert isinstance(_, list)
            results[current] = NestedList([create_lists(config, results, x, stack,
                                                        inside_cartesian=inside_cartesian)
                                           for x in _])
        # 3. Cartesian list of lists
        elif list_type == _CONF.TYPE.CARTESIAN:
            if inside_cartesian is not None:
                raise ConfigurationError(f"Cartesian list {inside_cartesian!r} contains another Cartesian list "
                                         f"{current!r}. Nested Cartesian lists are not allowed.")
            _ = list_config[_CONF.FIELD.LISTS]
            assert isinstance(_, list)
            results[current] = CartesianList([create_lists(config, results, x, stack,
                                                           inside_cartesian=current)
                                              for x in _])
        # 4. Scalar
        elif list_type == _CONF.TYPE.CONST:
            _ = list_config[_CONF.FIELD.VALUE]
            assert isinstance(_, str)
            results[current] = Constant(_)
        # 5. Number
        elif list_type == _CONF.TYPE.NUMBER:
            number_digits = int(list_config.get(_CONF.FIELD.NUMBER_DIGITS, _CONF.NUMBER_DIGITS_DEFAULT))  # type:ignore
            results[current] = Number(number_digits)
        # Unknown type
        else:
            raise InitializationError(f"Unknown list type: {list_type!r}")
        # Return the result
        return results[current]
    finally:
        stack.pop()
