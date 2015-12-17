"""
Do not import anything directly from this module.
"""


import hashlib
import itertools
import os
import random
from random import randrange

from .config import _CONF
from .exceptions import ConfigurationError, InitializationError


class AbstractNestedList(object):

    def __init__(self, lists):
        super(AbstractNestedList, self).__init__()
        self._lists = [WordList(x) if isinstance(x, list) else x
                       for x in lists]

    def __len__(self):
        return self._length

    def __str__(self):
        return '{}({}, len={})'.format(self.__class__.__name__, len(self._lists), len(self))

    def random(self):
        return self[randrange(len(self))]

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
except NameError:
    _unicode = str


def _encode(value):
    if isinstance(value, _unicode):
        return value.encode('utf-8')
    else:
        return value


class WordList(list, AbstractNestedList):

    def __init__(self, sequence=None):
        list.__init__(self, sequence)
        AbstractNestedList.__init__(self, [])
        self._length = len(self)
        self.__hash = None

    def __str__(self):
        ls = [repr(x) for x in self[:4]]
        if len(ls) == 4:
            ls[3] = '...'
        return '{}([{}], len={})'.format(self.__class__.__name__, ', '.join(ls), len(self))

    def squash(self, hard, cache):
        return self

    @property
    def _hash(self):
        if self.__hash is not None:
            return self.__hash
        md5 = hashlib.md5()
        md5.update(_encode(str(len(self))))
        for x in self:
            md5.update(_encode(x))
        self.__hash = md5.digest()
        return self.__hash


class NestedList(AbstractNestedList):

    def __init__(self, lists):
        super(NestedList, self).__init__(lists)
        # Fattest lists first (to reduce average __getitem__ time)
        self._lists.sort(key=lambda x: -len(x))
        self._length = sum(len(x) for x in lists)

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
        result = super(NestedList, self).squash(hard, cache)
        if result is self and hard:
            if all(isinstance(x, WordList) for x in self._lists):
                # Creating combined wordlist and then checking cache
                # is a little wasteful, but it has no long-term consequences.
                # And it's simple!
                result = WordList(sorted(set(itertools.chain.from_iterable(self._lists))))
                if result._hash in cache:
                    result = cache.get(result._hash)
                else:
                    cache[result._hash] = result
        return result


class CartesianList(AbstractNestedList):

    def __init__(self, lists):
        super(CartesianList, self).__init__(lists)
        self._length = 1
        for x in lists:
            self._length *= len(x)

    def __getitem__(self, i):
        # Retrieve item from appropriate list
        result = []
        for sublist in reversed(self._lists):
            length = len(sublist)
            result.append(sublist[i % length])
            i = i // length
        result.reverse()
        return result


class Scalar(AbstractNestedList):

    def __init__(self, value):
        super(Scalar, self).__init__([])
        self.value = value

    def __getitem__(self, i):
        return self.value

    def __len__(self):
        return 1

    def __str__(self):
        return '{}(value={!r})'.format(self.__class__.__name__, self.value)

    def random(self):
        return self.value


class RandomNameGenerator(object):
    """
    This class provides random name generation interface.

    Create an instance of this class if you want to create custom
    configuration.
    If default implementation is enough, just use `generate`,
    `generate_slug` and other exported functions.
    """

    def __init__(self, config):
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
        # Fire it up
        self.randomize()
        assert self.generate_slug()

    def randomize(self):
        """
        Re-seeds random number generator.

        Call this method if you are getting too many already known values
        in a sequence (say, more than 10).

        NOTE: re-seeding has global effect.
        """
        random.seed()

    def generate(self, pattern=None):
        """
        Generates and returns random name as a list of strings.
        """
        lst = self._lists[pattern]
        while True:
            result = lst.random()
            # Make sure there are no duplicates or related words
            # (with identical 4-letter prefix).
            if len(set(x[:4] for x in result)) == len(result):
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


def _create_default_generator():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    if os.path.isdir(data_dir):
        from coolname.loader import load_config
        config = load_config(data_dir)
    else:
        from coolname.data import config
    return RandomNameGenerator(config)


# Default generator is a global object
_default = _create_default_generator()

# Global functions are actually methods of the default generator.
# (most users don't care about creating generator instances)
generate = _default.generate
generate_slug = _default.generate_slug
get_combinations_count = _default.get_combinations_count
randomize = _default.randomize
