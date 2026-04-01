"""
Do not import anything directly from this module.
"""
from collections.abc import Iterable
from functools import partial
import hashlib
import itertools
import os
import os.path as op
import random
from random import randrange, Random
import re
import typing
from typing import Mapping, Callable, Any, TextIO, cast, Protocol

from .config import _CONF
from .exceptions import ConfigurationError, InitializationError
from .loader import _ConfigT

if typing.TYPE_CHECKING:
    HashType = hashlib._Hash  # pragma: no cover
else:
    HashType = Any

# For new Python versions with (possible) OpenSSL FIPS support,
# we should pass usedforsecurity=False argument to md5().
_md5: Callable[[], HashType]
try:
    hashlib.md5(b'', usedforsecurity=False)  # noqa
    _md5 = partial(hashlib.md5, usedforsecurity=False)
except TypeError:  # pragma: no cover
    _md5 = hashlib.md5


class ListLike(Protocol):
    """Protocol for AbstractNestedList and WordAsPhraseWrapper"""

    length: int
    multiword: bool

    def __getitem__(self, item: int) -> str | list[str]:
        ...

    def squash(self, hard: bool, cache: dict[bytes, 'ListLike']) -> 'ListLike':
        ...

    def dump(self, stream: TextIO, indent: str = '', object_ids: bool = False) -> None:
        ...


class AbstractNestedList(ListLike):

    length: int  # pragma: no cover
    _lists: list[ListLike]

    def __init__(self, lists: Iterable[ListLike] | Iterable[list[str]]):
        super().__init__()
        # Note: we can't use isinstance() here because issubclass(WordList, list) == True
        self._lists = [WordList(x) if type(x) is list[str] else x for x in lists]
        # If this is set to True in a subclass,
        # then subclass yields sequences instead of single words.
        self.multiword = getattr(self.__class__, 'multiword', None) or any(x.multiword for x in self._lists)

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

    def dump(self, stream: TextIO, indent: str = '', object_ids: bool = False) -> None:
        stream.write(indent + str(self) +
                     (f' [id={id(self)}]' if object_ids else '') +
                     '\n')
        indent += '  '
        for sublist in self._lists:
            sublist.dump(stream, indent, object_ids=object_ids)  # noqa


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
class _BasicList(list[str | tuple[str, ...]], AbstractNestedList):

    length: int  # pragma: no cover

    def __init__(self, sequence: list[str] | list[tuple[str, ...]]):
        list.__init__(self, sequence)
        AbstractNestedList.__init__(self, [])
        self.length = len(self)
        self.__hash = None

    def __str__(self) -> str:
        ls = [repr(x) for x in self[:4]]
        if len(ls) == 4:
            ls[3] = '...'
        return f'{self.__class__.__name__}([{", ".join(ls)}], len={len(self)})'

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

    def __init__(self, lst: list[str]):
        _BasicList.__init__(self, lst)


class PhraseList(_BasicList):
    """List of phrases (sequences of one or more words)."""

    multiword = True

    def __init__(self, lst: list[str] | list[tuple[str, ...]]):
        if any(isinstance(x, str) for x in lst):
            lst = [_split_phrase(x) if isinstance(x, str) else x for x in lst]
        _BasicList.__init__(self, lst)


class WordAsPhraseWrapper(ListLike):

    length: int  # pragma: no cover
    multiword = True

    _list: ListLike

    def __init__(self, wordlist: WordList):
        self._list = wordlist
        self.length = len(wordlist)

    def __len__(self) -> int:
        return self.length

    def __getitem__(self, i: int) -> str | list[str]:
        return [cast(str, self._list[i])]

    def squash(self, hard: bool, cache: dict[bytes, ListLike]) -> ListLike:  # noqa
        return self

    def dump(self, stream: TextIO, indent: str = '', object_ids: bool = False) -> None:
        stream.write(f"{indent}{self}{f' [id={id(self)}]' if object_ids else ''}\n")
        indent += '  '
        self._list.dump(stream, indent, object_ids)

    def __str__(self) -> str:
        return f'{self.__class__.__name__}({self._list})'

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self._list!r})'


class TopLevelMultiWrapper(WordAsPhraseWrapper):
    """
    For abnormal but possible cases when there's no multiword list at the top generator level.
    """

    def __init__(self, any_list: AbstractNestedList):  # noqa
        # Note that call to base class is omitted deliberately
        self._list = any_list
        self.length = any_list.length

    def dump(self, stream, indent='', object_ids=False):
        return self._list.dump(stream, indent, object_ids)


class NestedList(AbstractNestedList):

    length: int  # pragma: no cover
    _lists: list[AbstractNestedList]  # pragma: no cover

    def __init__(self, lists: list[AbstractNestedList]):
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
                    result = cls(sorted(set(itertools.chain.from_iterable(self._lists))))
                    if result._hash in cache:  # noqa
                        result = cache.get(result._hash)  # noqa
                    else:
                        cache[result._hash] = result  # noqa
        return result


class CartesianList(AbstractNestedList):

    length: int  # pragma: no cover

    def __init__(self, lists: list[AbstractNestedList]):
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
        self.multiword = True

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


class Scalar(AbstractNestedList):

    length: int  # pragma: no cover
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


class RandRange(Protocol):
    def __call__(self, start: int, stop: int | None = None, step: int = 1) -> int:
        ...


class RandomGenerator:
    """
    This class provides random name generation interface.

    Create an instance of this class if you want to create custom
    configuration.
    If default implementation is enough, just use `generate`,
    `generate_slug` and other exported functions.
    """

    # Structure that does the generation
    _lists: dict[str | int | None, ListLike]  # pragma: no cover
    # Custom random (if any)
    _random: Random | None  # pragma: no cover
    _randrange: RandRange  # pragma: no cover
    # ENSURE_UNIQUE_PREFIX - don't output combinations with two words having N same first letters
    _check_prefix: int | None  # pragma: no cover
    # MAX_SLUG_LENGTH - don't output slugs with more than N characters, including hyphens
    _max_slug_length: int | None  # pragma: no cover

    def __init__(self, config: _ConfigT, rand: Random | None = None):
        self.random = rand  # sets _random and _randrange. Note that we assign via property setter.
        config = dict(config)
        _validate_config(config)
        lists: dict[str, AbstractNestedList] = {}
        _create_lists(config, lists, 'all', [])
        self._lists = {}
        for key, list_config in config.items():
            # Other generators independent of 'all'
            if list_config.get(_CONF.FIELD.GENERATOR) and key not in lists:
                _create_lists(config, lists, key, [])
            if key == 'all' or key.isdigit() or list_config.get(_CONF.FIELD.GENERATOR):
                pattern: str | int | None
                if key.isdigit():
                    pattern = int(key)
                elif key == 'all':
                    pattern = None
                else:
                    pattern = key
                gen_list = lists[key]
                # Abnormal but possible configuration - top list is not multiword.
                # This requires a wrapper so that we avoid dealing with str instead of list in generate().
                # See also test_degen_* in test_impl.py
                if not lists[key].multiword:
                    gen_list = TopLevelMultiWrapper(lists[key])  # type: ignore
                self._lists[pattern] = gen_list
        self._lists[None] = self._lists[None].squash(True, {})
        # Should we avoid duplicates?
        try:
            ensure_unique = config['all'][_CONF.FIELD.ENSURE_UNIQUE]
            if not isinstance(ensure_unique, bool):
                raise ValueError(f'expected boolean, got {ensure_unique!r}')
            self._ensure_unique = ensure_unique
        except KeyError:
            self._ensure_unique = False
        except ValueError as ex:
            raise ConfigurationError(f'Invalid {_CONF.FIELD.ENSURE_UNIQUE} value: {ex}')
        # Should we avoid duplicating prefixes?
        try:
            self._check_prefix = int(config['all'][_CONF.FIELD.ENSURE_UNIQUE_PREFIX])  # type: ignore[arg-type]
            if self._check_prefix <= 0:
                raise ValueError(f'expected a positive integer, got {self._check_prefix!r}')
        except KeyError:
            self._check_prefix = None
        except ValueError as ex:
            raise ConfigurationError(f'Invalid {_CONF.FIELD.ENSURE_UNIQUE_PREFIX} value: {ex}')
        # Get max slug length
        try:
            self._max_slug_length = int(config['all'][_CONF.FIELD.MAX_SLUG_LENGTH])  # type: ignore[arg-type]
        except KeyError:
            self._max_slug_length = None
        except ValueError as ex:
            raise ConfigurationError(f'Invalid {_CONF.FIELD.MAX_SLUG_LENGTH} value: {ex}')
        # Make sure that generate() does not go into long loop.
        # Default generator is a special case, we don't need check.
        if (not config['all'].get('__nocheck') and
                self._ensure_unique or self._check_prefix or self._max_slug_length):
            self._check_not_hanging()
        # Fire it up
        assert self.generate_slug()

    @property
    def random(self) -> Random | None:
        return self._random

    @random.setter
    def random(self, rand: Random | None) -> None:
        if rand:
            self._random = rand
            self._randrange = rand.randrange
        else:
            self._random = random  # type: ignore
            self._randrange = random.randrange

    def generate(self, pattern: str | int | None = None) -> list[str]:
        """
        Generates and returns random name as a list of strings.
        """
        lst = self._lists[pattern]
        while True:
            result = lst[self._randrange(lst.length)]
            # 1. Check that there are no duplicates
            # 2. Check that there are no duplicate prefixes
            # 3. Check max slug length
            n = len(result)
            if (self._ensure_unique and len(set(result)) != n or
                    self._check_prefix and len(set(x[:self._check_prefix] for x in result)) != n or
                    self._max_slug_length and sum(len(x) for x in result) + n - 1 > self._max_slug_length):
                continue
            # Most of the time it returns at first attempt, without repeating the loop.
            # Note about typing: technically its List[str] | str, but we know it's always List[str] at this point.
            return result  # type: ignore

    def generate_slug(self, pattern: str | int | None = None) -> str:
        """
        Generates and returns random name as a slug.
        """
        return '-'.join(self.generate(pattern))

    def get_combinations_count(self, pattern: str | int | None = None) -> int:
        """
        Returns total number of unique combinations
        for the given pattern.
        """
        lst = self._lists[pattern]
        return lst.length

    def _dump(self, stream: TextIO, pattern: str | int | None = None, object_ids: bool = False) -> None:
        """Dumps current tree into a text stream."""
        self._lists[pattern].dump(stream, '', object_ids=object_ids)  # noqa

    def _check_not_hanging(self) -> None:
        """
        Rough check that generate() will not hang or be very slow.

        Raises ConfigurationError if generate() spends too much time in retry loop.
        Issues a warning.warn() if there is a risk of slowdown.
        """
        # (field_name, predicate, warning_msg, exception_msg)
        # predicate(g) is a function that returns True if generated combination g must be rejected,
        # see checks in generate()
        checks: list[tuple[str, Any, Callable[[Any], bool], str, str]] = []
        # ensure_unique can lead to infinite loops for some tiny erroneous configs
        if self._ensure_unique:
            checks.append((
                _CONF.FIELD.ENSURE_UNIQUE,
                self._ensure_unique,
                lambda g: len(set(g)) != len(g),
                '{generate} may be slow because a significant fraction of combinations contain repeating words and {field_name} is set',  # noqa
                'Impossible to generate with {field_name}'
            ))
        #
        # max_slug_length can easily slow down or block generation if set too small
        if self._max_slug_length:
            checks.append((
                _CONF.FIELD.MAX_SLUG_LENGTH,
                self._max_slug_length,
                lambda g: sum(len(x) for x in g) + len(g) - 1 > self._max_slug_length,  # type: ignore
                '{generate} may be slow because a significant fraction of combinations exceed {field_name}={field_value}',  # noqa
                'Impossible to generate with {field_name}={field_value}'
            ))
        # Perform the relevant checks for all generators, starting from 'all'
        n = 100
        warning_threshold = 20  # fail probability: 0.04 for 2 attempts, 0.008 for 3 attempts, etc.
        for lst_id, lst in sorted(self._lists.items(), key=lambda x: '' if x is None else str(x)):
            context = {'generate': f'coolname.generate({"" if lst_id is None else repr(lst_id)})'}
            # For each generator, perform checks
            for field_name, field_value, predicate, warning_msg, exception_msg in checks:
                context.update({'field_name': field_name, 'field_value': field_value})
                bad_count = 0
                for _ in range(n):
                    if predicate(lst[randrange(lst.length)]):
                        bad_count += 1
                if bad_count >= n:
                    raise ConfigurationError(exception_msg.format(**context))
                elif bad_count >= warning_threshold:
                    import warnings
                    warnings.warn(warning_msg.format(**context))


# Translate phrases defined as strings to tuples
def _split_phrase(x: str) -> tuple[str, ...]:
    return tuple(re.split(r'\s+', x.strip()))


def _validate_config(config: _ConfigT) -> None:
    """
    A big and ugly method for config validation.
    It would be nice to use cerberus, but we don't
    want to introduce dependencies just for that.
    """
    try:
        referenced_sublists: set[str] = set()
        for key, listdef in list(config.items()):
            # Check if section is a list
            if not isinstance(listdef, dict):
                raise ValueError(f'Value at key {key!r} is not a dict')
            # Check if it has correct type
            if _CONF.FIELD.TYPE not in listdef:
                raise ValueError(f'Config at key {key!r} has no {_CONF.FIELD.TYPE!r}')
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
                    raise ValueError(f'Config at key {key!r} has invalid {_CONF.FIELD.VALUE!r}')
            # Words
            elif listdef[_CONF.FIELD.TYPE] == _CONF.TYPE.WORDS:
                try:
                    words = listdef[_CONF.FIELD.WORDS]
                except KeyError:
                    raise ValueError(f'Config at key {key!r} has no {_CONF.FIELD.WORDS!r}')
                if not isinstance(words, list) or not words:
                    raise ValueError(f'Config at key {key!r} has invalid {_CONF.FIELD.WORDS!r}')
                # Validate word length
                try:
                    max_length = int(listdef[_CONF.FIELD.MAX_LENGTH])  # type: ignore[arg-type]
                except KeyError:
                    max_length = None
                if max_length is not None:
                    for word in words:
                        if len(word) > max_length:
                            raise ValueError(f'Config at key {key!r} has invalid word {word!r} '
                                             f'(longer than {max_length} characters)')
            # Phrases (sequences of one or more words)
            elif listdef[_CONF.FIELD.TYPE] == _CONF.TYPE.PHRASES:
                try:
                    phrases = listdef[_CONF.FIELD.PHRASES]
                except KeyError:
                    raise ValueError(f'Config at key {key!r} has no {_CONF.FIELD.PHRASES!r}')
                if not isinstance(phrases, list) or not phrases:
                    raise ValueError(f'Config at key {key!r} has invalid {_CONF.FIELD.PHRASES!r}')
                # Validate multi-word and max length
                try:
                    number_of_words = int(listdef[_CONF.FIELD.NUMBER_OF_WORDS])  # type: ignore[arg-type]
                except KeyError:
                    number_of_words = None
                try:
                    max_length = int(listdef[_CONF.FIELD.MAX_LENGTH])  # type: ignore[arg-type]
                except KeyError:
                    max_length = None
                for phrase in phrases:
                    if isinstance(phrase, str):
                        phrase = _split_phrase(phrase)  # str -> sequence, if necessary
                    if not isinstance(phrase, (tuple, list)) or not all(isinstance(x, str) for x in phrase):
                        raise ValueError(f'Config at key {key!r} has invalid {_CONF.FIELD.PHRASES!r}: '
                                         f'must be all string/tuple/list')
                    if number_of_words is not None and len(phrase) != number_of_words:
                        raise ValueError(f'Config at key {key!r} has invalid phrase {" ".join(phrase)!r} '
                                         f'({len(phrase)} word(s) but '
                                         f'{_CONF.FIELD.NUMBER_OF_WORDS}={number_of_words})')
                    if max_length is not None and sum(len(word) for word in phrase) > max_length:
                        raise ValueError(f'Config at key {key!r} has invalid phrase {" ".join(phrase)!r} '
                                         f'(longer than {max_length} characters)')
            else:
                raise ValueError(f'Config at key {key!r} has invalid {_CONF.FIELD.TYPE!r}')
        # Check that all sublists are defined
        diff = referenced_sublists.difference(config.keys())
        if diff:
            raise ValueError(f'Lists are referenced but not defined: {", ".join(sorted(diff)[:10])}')
    except (KeyError, ValueError) as ex:
        raise ConfigurationError(str(ex))


def _create_lists(
        config: _ConfigT,
        results: dict[str, AbstractNestedList],
        current: str,
        stack: list[str],
        inside_cartesian: str | None = None
) -> AbstractNestedList:
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
            _ = list_config['words']
            assert isinstance(_, list)
            results[current] = WordList(_)
        # List of phrases
        elif list_type == _CONF.TYPE.PHRASES:
            _ = list_config['phrases']
            assert isinstance(_, list)
            results[current] = PhraseList(_)
        # 2. Simple list of lists
        elif list_type == _CONF.TYPE.NESTED:
            _ = list_config[_CONF.FIELD.LISTS]
            assert isinstance(_, list)
            results[current] = NestedList([_create_lists(config, results, x, stack,
                                                         inside_cartesian=inside_cartesian)
                                           for x in _])
        # 3. Cartesian list of lists
        elif list_type == _CONF.TYPE.CARTESIAN:
            if inside_cartesian is not None:
                raise ConfigurationError(f"Cartesian list {inside_cartesian!r} contains another Cartesian list "
                                         f"{current!r}. Nested Cartesian lists are not allowed.")
            _ = list_config[_CONF.FIELD.LISTS]
            assert isinstance(_, list)
            results[current] = CartesianList([_create_lists(config, results, x, stack,
                                                            inside_cartesian=current)
                                              for x in _])
        # 4. Scalar
        elif list_type == _CONF.TYPE.CONST:
            _ = list_config[_CONF.FIELD.VALUE]
            assert isinstance(_, str)
            results[current] = Scalar(_)
        # Unknown type
        else:
            raise InitializationError(f"Unknown list type: {list_type!r}")
        # Return the result
        return results[current]
    finally:
        stack.pop()


# Default generator is a global object
def _create_default_generator() -> RandomGenerator:
    data_dir = os.getenv('COOLNAME_DATA_DIR')
    data_module = os.getenv('COOLNAME_DATA_MODULE')
    if not data_dir and not data_module:
        data_dir = op.join(op.dirname(op.abspath(__file__)), 'data')
        data_module = 'coolname.data'  # used when imported from egg; consumes more memory
    if data_dir and op.isdir(data_dir):
        from coolname.loader import load_config
        config = load_config(data_dir)
    elif data_module:  # pragma: no cover (actually tested via subprocess - see test_coolname_env.py)
        import importlib
        config = importlib.import_module(data_module).config
    else:  # pragma: no cover
        raise ImportError('Configure valid COOLNAME_DATA_DIR and/or COOLNAME_DATA_MODULE')
    config['all']['__nocheck'] = True
    return RandomGenerator(config)


# Default generator is a global object
_default: RandomGenerator = _create_default_generator()

# Global functions are actually methods of the default generator.
# (most users don't care about creating generator instances)
generate = _default.generate
generate_slug = _default.generate_slug
get_combinations_count = _default.get_combinations_count


def replace_random(rand: Random | None = None) -> None:
    """Replaces random number generator for the default RandomGenerator instance."""
    _default.random = rand
