from __future__ import annotations
import os
import os.path as op
import random
from io import StringIO
from random import randrange
import typing
from typing import Any

from ._version import __version__, __version_tuple__

# Hint: set COOLNAME_DATA_DIR and/or COOLNAME_DATA_MODULE
# before `import coolname` to change the default generator.

from ._config import _CONF
from .exceptions import InitializationError, ConfigurationError
from . import _impl
from . import types
from .types import CoolnameConfigT, CoolnameConfigListT, RandomT, RandomSeedArgT

__all__ = [
    'generate', 'generate_slug', 'get_combinations_count', 'replace_random',
    'RandomGenerator',
    'InitializationError', 'ConfigurationError',
    'CoolnameConfigT', 'CoolnameConfigListT', 'RandomT', 'RandomSeedArgT'
]


class RandomGenerator:
    """
    This class provides random name generation interface.

    Create an instance of this class if you want to create custom
    configuration. Config dictionary is described by type alias
    :py:class:`~coolname.types.CoolnameConfigT`.
    """

    # Structure that does the generation
    _lists: dict[str | int | None, types.ListLike]
    # Custom random (if any)
    _random: RandomT | None
    _randrange: types.RandRangeT
    # ENSURE_UNIQUE_PREFIX - don't output combinations with two words having N same first letters
    _check_prefix: int | None
    # MAX_SLUG_LENGTH - don't output slugs with more than N characters, including hyphens
    _max_slug_length: int | None

    def __init__(self, config: CoolnameConfigT, rand: RandomT | None = None):
        self.random = rand  # sets _random and _randrange. Note that we assign via property setter.
        _impl.validate_and_normalize_config(config)
        lists: dict[str, types.ListLike] = {}
        _impl.create_lists(config, lists, 'all', [])
        self._lists = {}
        for key, list_config in config.items():
            # Other generators independent of 'all'
            if list_config.get(_CONF.FIELD.GENERATOR) and key not in lists:
                _impl.create_lists(config, lists, key, [])
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
                    gen_list = _impl.TopLevelMultiWrapper(lists[key])
                self._lists[pattern] = gen_list
        self._lists[None] = self._lists[None].squash(True, {})
        # Should we avoid duplicates?
        try:
            ensure_unique = config['all'][_CONF.FIELD.ENSURE_UNIQUE]
            if not isinstance(ensure_unique, bool):
                raise ValueError(f'expected boolean, got {ensure_unique!r}')
            self._ensure_unique = ensure_unique
        except KeyError:
            self._ensure_unique = True
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
    def random(self) -> RandomT | None:
        """
        :py:class:`~random.Random`-like random number generator (RNG)
        to be used by this instance.

        By default, the default RNG is used. You can also use something else,
        as long as it supports :class:`~coolname.types.RandomT` protocol.
        """
        return self._random

    @random.setter
    def random(self, rand: types.RandomT | None) -> None:
        if rand:
            self._random = rand
            self._randrange = rand.randrange
        else:
            self._random = random
            self._randrange = random.randrange

    def generate(self, pattern: str | int | None = None) -> list[str]:
        """
        Generates and returns random name as a list of strings.

        :param pattern: In the default generator, can be 2, 3, 4.
            In a custom generator, can be any list with ``"generator": true``.
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

        :param pattern: In the default generator, can be 2, 3, 4.
            In a custom generator, can be any list with ``"generator": true``.
        """
        return '-'.join(self.generate(pattern))

    def get_combinations_count(self, pattern: str | int | None = None) -> int:
        """
        Returns the total theoretical number of unique combinations.

        Actual number is a bit smaller, because some combinations
        are rejected and never generated.
        Examples: ``good-good-dog``, ``swift-swift``.

        :param pattern: Return the number of combinations for the given
            pattern only.
        """
        lst = self._lists[pattern]
        return lst.length

    def write(self,
              stream: typing.TextIO,
              pattern: str | int | None = None, *,
              indent: str | int = 2,
              max_items: int = 4,
              ids: bool = False,
              ) -> None:
        """
        Writes the generator's tree-like structure into a text stream.
        This is mostly for debugging purposes.

        Text representation is the same as in :py:meth:`render`.
        Arguments are also the same.

        **WARNING:** text representation format itself is not part of the API,
        and may be changed without notice in future versions.

        :arg stream: Output stream to write into
        :arg pattern: Optional - meaning the same as in :meth:`generate`
        :arg indent: Single indentation: any number of spaces, a tab,
            or anything you want. If :py:class:`int`, a number of spaces.
        :arg max_items: Maximum number of words or phrases to display.
            If there are more, the remaining items are replaced with ellipsis.
        :arg ids: If True, display Python :py:func:`id` for each object.
            Could be useful to check which word/phrase lists are reused
            in more than one place in the tree.
        """
        if isinstance(indent, int):
            indent = ' ' * indent
        stream.write(f'{self.__class__.__qualname__}\n')
        self._lists[pattern].write(stream, indent=indent, base_indent=indent,
                                   max_items=max_items, ids=ids)  # noqa

    def render(self,
               pattern: str | int | None = None, *,
               indent: str | int = 2,
               max_items: int = 4,
               ids: bool = False
               ) -> str:
        """
        Returns the generator's tree-like structure as text.
        This is mostly for debugging purposes.

        Text representation is the same as in :py:meth:`write`.
        Arguments are also the same.

        **WARNING:** text representation format itself is not part of the API,
        and may be changed without notice in future versions.
        """
        s = StringIO()
        self.write(s, pattern, indent=indent, max_items=max_items, ids=ids)
        return s.getvalue()

    def _check_not_hanging(self) -> None:
        """
        Rough check that generate() will not hang or be very slow.

        Raises ConfigurationError if generate() spends too much time in retry loop.
        Issues a warning.warn() if there is a risk of slowdown.
        """
        # (field_name, predicate, warning_msg, exception_msg)
        # predicate(g) is a function that returns True if generated combination g must be rejected,
        # see checks in generate()
        checks: list[tuple[str, Any, typing.Callable[[Any], bool], str, str]] = []
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


def replace_random(rand: RandomT | None = None) -> None:
    """
    Replaces random number generator (RNG) for the default
    :class:`~coolname.RandomGenerator` instance.
    See :attr:`~coolname.RandomGenerator.random` property.
    """
    _default.random = rand
