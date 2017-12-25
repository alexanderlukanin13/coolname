"""
Do not import anything directly from this module.
"""


import hashlib
import itertools
import os
import random
from random import randrange
import re

from .config import _CONF
from .exceptions import ConfigurationError, InitializationError


class AbstractNestedList(object):

    def __init__(self, lists):
        super(AbstractNestedList, self).__init__()
        self._lists = [WordList(x) if x.__class__ is list else x
                       for x in lists]
        # If this is set to True in a subclass,
        # then subclass yields sequences instead of single words.
        self.multiword = any(x.multiword for x in self._lists)

    def __len__(self):
        return self.length

    def __str__(self):
        return '{}({}, len={})'.format(self.__class__.__name__, len(self._lists), len(self))

    def __repr__(self):
        return self.__str__()

    def squash(self, hard, cache):
        if len(self._lists) == 1:
            return self._lists[0].squash(hard, cache)
        else:
            self._lists = [x.squash(hard, cache) for x in self._lists]
            return self

    def _dump(self, stream, indent='', object_ids=False):
        stream.write(indent + _unicode(self) +
                     (' [id={}]'.format(id(self)) if object_ids else '') +
                     '\n')
        indent += '  '
        for sublist in self._lists:
            sublist._dump(stream, indent, object_ids=object_ids)


# Poor man's `six`
try:
    _unicode = unicode
    _str_types = (str, _unicode)  # pragma: nocover
except NameError:
    _unicode = str
    _str_types = str


# Convert value to bytes, for hashing
# (used to calculate WordList or PhraseList hash)
def _to_bytes(value):
    if isinstance(value, _unicode):
        return value.encode('utf-8')
    elif isinstance(value, tuple):
        return str(value).encode('utf-8')
    else:
        return value


class _BasicList(list, AbstractNestedList):

    def __init__(self, sequence=None):
        list.__init__(self, sequence)
        AbstractNestedList.__init__(self, [])
        self.length = len(self)
        self.__hash = None

    def __str__(self):
        ls = [repr(x) for x in self[:4]]
        if len(ls) == 4:
            ls[3] = '...'
        return '{}([{}], len={})'.format(self.__class__.__name__, ', '.join(ls), len(self))

    def __repr__(self):
        return self.__str__()

    def squash(self, hard, cache):
        return self

    @property
    def _hash(self):
        if self.__hash is not None:
            return self.__hash
        md5 = hashlib.md5()
        md5.update(_to_bytes(str(len(self))))
        for x in self:
            md5.update(_to_bytes(x))
        self.__hash = md5.digest()
        return self.__hash


class WordList(_BasicList):
    """List of single words."""


class PhraseList(_BasicList):
    """List of phrases (sequences of one or more words)."""

    def __init__(self, sequence=None):
        super(PhraseList, self).__init__(tuple(_split_phrase(x)) for x in sequence)
        self.multiword = True


class WordAsPhraseWrapper(object):

    multiword = True

    def __init__(self, wordlist):
        self._list = wordlist
        self.length = len(wordlist)

    def __len__(self):
        return self.length

    def __getitem__(self, i):
        return (self._list[i], )

    def squash(self, hard, cache):
        return self

    def __str__(self):
        return '{}({})'.format(self.__class__.__name__, str(self._list))

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, repr(self._list))


class NestedList(AbstractNestedList):

    def __init__(self, lists):
        # If user mixes WordList and PhraseList in the same NestedList,
        # we need to make sure that __getitem__ always returns tuple.
        # For that, we wrap WordList instances.
        if any(isinstance(x, WordList) for x in lists) and any(x.multiword for x in lists):
            lists = [WordAsPhraseWrapper(x) if isinstance(x, WordList) else x for x in lists]
        super(NestedList, self).__init__(lists)
        # Fattest lists first (to reduce average __getitem__ time)
        self._lists.sort(key=lambda x: -len(x))
        self.length = sum(len(x) for x in lists)

    def __getitem__(self, i):
        # Retrieve item from appropriate list
        for sublist in self._lists:
            length = len(sublist)
            if i < length:
                return sublist[i]
            else:
                i -= length
        raise IndexError('list index out of range')

    def squash(self, hard, cache):
        # Cache is used to avoid data duplication.
        # If we have 4 branches which finally point to the same list of nouns,
        # why not using the same WordList instance for all 4 branches?
        # This optimization is also applied to PhraseLists, just in case.
        result = super(NestedList, self).squash(hard, cache)
        if result is self and hard:
            for cls in (WordList, PhraseList):
                if all(isinstance(x, cls) for x in self._lists):
                    # Creating combined WordList/PhraseList and then checking cache
                    # is a little wasteful, but it has no long-term consequences.
                    # And it's simple!
                    result = cls(sorted(set(itertools.chain.from_iterable(self._lists))))
                    if result._hash in cache:
                        result = cache.get(result._hash)
                    else:
                        cache[result._hash] = result
        return result


class CartesianList(AbstractNestedList):

    def __init__(self, lists):
        super(CartesianList, self).__init__(lists)
        self.length = 1
        for x in lists:
            self.length *= len(x)
        # Let's say list lengths are 5, 7, 11, 13.
        # divs = [7*11*13, 11*13, 13, 1]
        divs = [1]
        prod = 1
        for x in reversed(lists[1:]):
            prod *= len(x)
            divs.append(prod)
        self._list_divs = tuple(zip(self._lists, reversed(divs)))
        self.multiword = True

    def __getitem__(self, i):
        result = []
        for sublist, n in self._list_divs:
            x = sublist[i // n]
            if sublist.multiword:
                result.extend(x)
            else:
                result.append(x)
            i %= n
        return result


class Scalar(AbstractNestedList):

    def __init__(self, value):
        super(Scalar, self).__init__([])
        self.value = value
        self.length = 1

    def __getitem__(self, i):
        return self.value

    def __str__(self):
        return '{}(value={!r})'.format(self.__class__.__name__, self.value)

    def random(self):
        return self.value


class RandomGenerator(object):
    """
    This class provides random name generation interface.

    Create an instance of this class if you want to create custom
    configuration.
    If default implementation is enough, just use `generate`,
    `generate_slug` and other exported functions.
    """

    def __init__(self, config, rand=None):
        self.random = rand  # sets _random and _randrange
        config = dict(config)
        _validate_config(config)
        lists = {}
        _create_lists(config, lists, 'all', [])
        self._lists = {}
        for key, listdef in config.items():
            # Other generators independent from 'all'
            if listdef.get(_CONF.FIELD.GENERATOR) and key not in lists:
                _create_lists(config, lists, key, [])
            if (key == 'all' or key.isdigit() or listdef.get(_CONF.FIELD.GENERATOR)):
                if key.isdigit():
                    pattern = int(key)
                elif key == 'all':
                    pattern = None
                else:
                    pattern = key
                self._lists[pattern] = lists[key]
        self._lists[None] = self._lists[None].squash(True, {})
        # Should we avoid duplicating prefixes?
        try:
            self._check_prefix = int(config['all'][_CONF.FIELD.ENSURE_UNIQUE_PREFIX])
            if self._check_prefix <= 0:
                raise ValueError('must be a positive integer')
        except KeyError:
            self._check_prefix = None
        except ValueError as ex:
            raise ConfigurationError('Invalid {} value: {}'
                                     .format(_CONF.FIELD.ENSURE_UNIQUE_PREFIX, ex))
        # Get max slug length
        try:
            self._max_slug_length = int(config['all'][_CONF.FIELD.MAX_SLUG_LENGTH])
        except KeyError:
            self._max_slug_length = None
        except ValueError as ex:
            raise ConfigurationError('Invalid {} value: {}'
                                     .format(_CONF.FIELD.MAX_SLUG_LENGTH, ex))
        # If there is max slug length, use slower version of generate() with check
        # Also make sure that generate() does not go into long loop
        if self._max_slug_length is not None:
            self.generate = self._generate_m
            if not config['all'].get('__nocheck'):
                _check_max_slug_length(self._max_slug_length, self._lists[None])
        # Fire it up
        assert self.generate_slug()

    @property
    def random(self):
        return self._random

    @random.setter
    def random(self, rand):
        if rand:
            self._random = rand
        else:
            self._random = random
        self._randrange = self._random.randrange

    def generate(self, pattern=None):
        """
        Generates and returns random name as a list of strings.
        """
        lst = self._lists[pattern]
        while True:
            result = lst[self._randrange(lst.length)]
            # Make sure there are no duplicates or related words
            # (with identical 4-letter prefix).
            if self._check_prefix and len(set(x[:self._check_prefix] for x in result)) != len(result):
                continue
            return result

    def _generate_m(self, pattern=None):
        """
        Slower version of generate(), with max_slug_length check.
        """
        lst = self._lists[pattern]
        while True:
            result = lst[self._randrange(lst.length)]
            # In addition to duplicates check, also check slug length
            n = len(result)
            if (self._check_prefix and len(set(x[:self._check_prefix] for x in result)) != len(result) or
                sum(len(x) for x in result) + n - 1 > self._max_slug_length):
                print(result)  # TODO
                continue
            return result

    def generate_slug(self, pattern=None):
        """
        Generates and returns random name as a slug.
        """
        return '-'.join(self.generate(pattern))

    def get_combinations_count(self, pattern=None):
        """
        Returns total number of unique combinations
        for the given pattern.
        """
        lst = self._lists[pattern]
        return len(lst)

    def _dump(self, stream, pattern=None, object_ids=False):
        """Dumps current tree into a text stream."""
        return self._lists[pattern]._dump(stream, '', object_ids=object_ids)


def _is_str(value):
    return value.__class__.__name__ in ('str', 'unicode')


# Translate phrases defined as strings to tuples
def _split_phrase(x):
    if isinstance(x, _str_types):
        return re.split(_unicode(r'\s+'), x.strip())
    else:
        return x


def _validate_config(config):
    """
    A big and ugly method for config validation.
    It would be nice to use cerberus, but we don't
    want to introduce dependencies just for that.
    """
    try:
        referenced_sublists = set()
        for key, listdef in list(config.items()):
            # Check if section is a list
            if not isinstance(listdef, dict):
                raise ValueError('Value at key {!r} is not a dict'
                                 .format(key))
            # Check if it has correct type
            if _CONF.FIELD.TYPE not in listdef:
                raise ValueError('Config at key {!r} has no {!r}'
                                 .format(key, _CONF.FIELD.TYPE))
            # Nested or Cartesian
            if listdef[_CONF.FIELD.TYPE] in (_CONF.TYPE.NESTED, _CONF.TYPE.CARTESIAN):
                sublists = listdef.get(_CONF.FIELD.LISTS)
                if sublists is None:
                    raise ValueError('Config at key {!r} has no {!r}'
                                     .format(key, _CONF.FIELD.LISTS))
                if (not isinstance(sublists, list) or not sublists or
                        not all(_is_str(x) for x in sublists)):
                    raise ValueError('Config at key {!r} has invalid {!r}'
                                     .format(key, _CONF.FIELD.LISTS))
                referenced_sublists.update(sublists)
            # Const
            elif listdef[_CONF.FIELD.TYPE] == _CONF.TYPE.CONST:
                try:
                    value = listdef[_CONF.FIELD.VALUE]
                except KeyError:
                    raise ValueError('Config at key {!r} has no {!r}'
                                     .format(key, _CONF.FIELD.VALUE))
                if not _is_str(value):
                    raise ValueError('Config at key {!r} has invalid {!r}'
                                     .format(key, _CONF.FIELD.VALUE))
            # Words
            elif listdef[_CONF.FIELD.TYPE] == _CONF.TYPE.WORDS:
                try:
                    words = listdef[_CONF.FIELD.WORDS]
                except KeyError:
                    raise ValueError('Config at key {!r} has no {!r}'
                                     .format(key, _CONF.FIELD.WORDS))
                if not isinstance(words, list) or not words:
                    raise ValueError('Config at key {!r} has invalid {!r}'
                                     .format(key, _CONF.FIELD.WORDS))
                # Validate word length
                try:
                    max_length = int(listdef[_CONF.FIELD.MAX_LENGTH])
                except KeyError:
                    max_length = None
                if max_length is not None:
                    for word in words:
                        if len(word) > max_length:
                            raise ValueError('Config at key {!r} has invalid word {!r} '
                                             '(longer than {} characters)'
                                             .format(key, word, max_length))
            # Phrases (sequences of one or more words)
            elif listdef[_CONF.FIELD.TYPE] == _CONF.TYPE.PHRASES:
                try:
                    phrases = listdef[_CONF.FIELD.PHRASES]
                except KeyError:
                    raise ValueError('Config at key {!r} has no {!r}'
                                     .format(key, _CONF.FIELD.PHRASES))
                if not isinstance(phrases, list) or not phrases:
                    raise ValueError('Config at key {!r} has invalid {!r}'
                                     .format(key, _CONF.FIELD.PHRASES))
                # Validate multi-word and max length
                try:
                    number_of_words = int(listdef[_CONF.FIELD.NUMBER_OF_WORDS])
                except KeyError:
                    number_of_words = None
                try:
                    max_length = int(listdef[_CONF.FIELD.MAX_LENGTH])
                except KeyError:
                    max_length = None
                for phrase in phrases:
                    phrase = _split_phrase(phrase)  # str -> sequence, if necessary
                    if not isinstance(phrase, (tuple, list)) or not all(isinstance(x, _str_types) for x in phrase):
                        raise ValueError('Config at key {!r} has invalid {!r}: '
                                         'must be all string/tuple/list'
                                         .format(key, _CONF.FIELD.PHRASES))
                    if number_of_words is not None and len(phrase) != number_of_words:
                        raise ValueError('Config at key {!r} has invalid phrase {!r} '
                                         '({} word(s) but {}={})'
                                         .format(key, ' '.join(phrase),
                                                 len(phrase), _CONF.FIELD.NUMBER_OF_WORDS, number_of_words))
                    if max_length is not None and sum(len(word) for word in phrase) > max_length:
                        raise ValueError('Config at key {!r} has invalid phrase {!r} '
                                         '(longer than {} characters)'
                                         .format(key, ' '.join(phrase), max_length))
            else:
                raise ValueError('Config at key {!r} has invalid {!r}'
                                 .format(key, _CONF.FIELD.TYPE))
        # Check that all sublists are defined
        diff = referenced_sublists.difference(config.keys())
        if diff:
            raise ValueError('Lists are referenced but not defined: {}'
                             .format(', '.join(sorted(diff)[:10])))
    except (KeyError, ValueError) as ex:
        raise ConfigurationError(str(ex))


def _create_lists(config, results, current, stack, inside_cartesian=None):
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
        raise ConfigurationError('Rule {!r} is recursive: {!r}'.format(stack[0], stack))
    if len(stack) > 99:
        raise ConfigurationError('Rule {!r} is too deep'.format(stack[0]))
    # Track recursion depth
    stack.append(current)
    try:
        # Check what kind of list we have
        listdef = config[current]
        list_type = listdef[_CONF.FIELD.TYPE]
        # 1. List of words
        if list_type == _CONF.TYPE.WORDS:
            results[current] = WordList(listdef['words'])
        # List of phrases
        elif list_type == _CONF.TYPE.PHRASES:
            results[current] = PhraseList(listdef['phrases'])
        # 2. Simple list of lists
        elif list_type == _CONF.TYPE.NESTED:
            results[current] = NestedList([_create_lists(config, results, x, stack,
                                                         inside_cartesian=inside_cartesian)
                                           for x in listdef[_CONF.FIELD.LISTS]])

        # 3. Cartesian list of lists
        elif list_type == _CONF.TYPE.CARTESIAN:
            if inside_cartesian is not None:
                raise ConfigurationError("Cartesian list {!r} contains another Cartesian list "
                                         "{!r}. Nested Cartesian lists are not allowed."
                                         .format(inside_cartesian, current))
            results[current] = CartesianList([_create_lists(config, results, x, stack,
                                                            inside_cartesian=current)
                                              for x in listdef[_CONF.FIELD.LISTS]])
        # 4. Scalar
        elif list_type == _CONF.TYPE.CONST:
            results[current] = Scalar(listdef[_CONF.FIELD.VALUE])
        # Unknown type
        else:
            raise InitializationError("Unknown list type: {!r}".format(list_type))
        # Return the result
        return results[current]
    finally:
        stack.pop()


def _check_max_slug_length(max_slug_length, all_list):
    """
    Rough check for max_slug_length being to small.

    Raises ConfigurationError if generate() would spend too much time in retry loop.
    Issues a warning using warning.warn() if there is a risk of slowdown.
    """
    # Make sure max length is not too small (to avoid slowdown and infinite loops)
    n = 100
    warning_treshold = 20  # fail probability: 0.04 for 2 attempts, 0.008 for 3 attempts, etc.
    bad_count = 0
    for i in range(0, n):
        r = all_list[randrange(all_list.length)]
        if sum(len(x) for x in r) + len(r) - 1 > max_slug_length:
            bad_count += 1
    if bad_count >= n:
        raise ConfigurationError('Impossible to generate with {}={}'
                                 .format(_CONF.FIELD.MAX_SLUG_LENGTH,
                                         max_slug_length))
    elif bad_count >= warning_treshold:
        import warnings
        warnings.warn('coolname.generate() may be slow because a significant fraction '
                      'of combinations exceed {}={}'
                      .format(_CONF.FIELD.MAX_SLUG_LENGTH, max_slug_length))


def _create_default_generator():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    if os.path.isdir(data_dir):
        from coolname.loader import load_config
        config = load_config(data_dir)
    else:
        from coolname.data import config
    config['all']['__nocheck'] = True
    return RandomGenerator(config)


# Default generator is a global object
_default = _create_default_generator()

# Global functions are actually methods of the default generator.
# (most users don't care about creating generator instances)
generate = _default.generate
generate_slug = _default.generate_slug
get_combinations_count = _default.get_combinations_count


def replace_random(rand):
    """Replaces random number generator for the default RandomGenerator instance."""
    _default.random = rand
