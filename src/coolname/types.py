from __future__ import annotations
from abc import ABC, abstractmethod
import typing
from typing import TypeAlias

__all__ = ['CoolnameConfigT', 'CoolnameConfigListT', 'RandomT', 'RandomSeedArgT']

# For new Python versions with (possible) OpenSSL FIPS support,
# we should pass usedforsecurity=False argument to md5().
if typing.TYPE_CHECKING:
    import hashlib
    HashT: TypeAlias = hashlib._Hash
else:
    HashT: TypeAlias = typing.Any

#: Top-level values of config dict - that is, list configurations. For example:
#:
#: .. code-block:: python
#:
#:     {
#:         "comment": "adjective-adjective-noun",
#:         "type": "cartesian",
#:         "lists": ["adj_far", "adj_near", "subj"]
#:     }
CoolnameConfigListT: TypeAlias = dict[str, str | int | bool | list[str] | list[list[str]] | list[tuple[str, ...]]]

#: Whole configuration as a dictionary that is passed
#: to :py:class:`~coolname.RandomGenerator` constructor.
CoolnameConfigT: TypeAlias = dict[str, CoolnameConfigListT]

# random.randrange type
class RandRangeT(typing.Protocol):
    """Protocol for randrange function."""
    def __call__(self,
                 start: int,
                 stop: int | None = None,
                 step: int = 1,
                 /) -> int:
        ...

#: Type alias used by :meth:`~coolname.types.RandomT.seed`.
RandomSeedArgT: TypeAlias = None | int | float | str | bytes | bytearray

class RandomT(typing.Protocol):
    """
    Protocol for random module, used in :class:`~coolname.RandomGenerator`
    constructor and in :attr:`RandomGenerator.random` property.

    Similar to :py:class:`random.Random`, but only requires two methods:
    :py:meth:`~random.Random.seed` and :py:func:`~random.randrange`.

    You may need this in your code if you are using a Random object
    *and* it's not a standard :py:class:`random.Random` instance.
    """

    def seed(self, a: RandomSeedArgT = None, version: int = 2) -> None:
        """
        Re-seed the random number generator.

        See documentation for :py:meth:`~random.Random.seed`.
        """
        ...

    def randrange(self,
                  start: int,
                  stop: int | None = None,
                  step: int = 1,
                  /) -> int:  # position-only arguments as per docs
        """
        Return a randomly selected element from ``range(start, stop, step)``.

        See documentation for :py:func:`~random.randrange`.
        """
        ...


class ListLike(ABC):
    """Unified interface for AbstractNestedList and WordWrapper"""

    length: int
    multiword: bool

    @abstractmethod
    def __getitem__(self, item: int) -> str | list[str]:
        ...

    @abstractmethod
    def squash(self, hard: bool, cache: dict[bytes, 'ListLike']) -> 'ListLike':
        ...

    @abstractmethod
    def write(self, stream: typing.TextIO, *,
              indent: str = '  ', base_indent: str = '',
              max_items: int = 4, ids: bool = False,
              ) -> None:
        ...

    # Default implementation ignores max_items, and is a synonym for __str__
    def render(self, *, max_items: int = 4) -> str:
        return self.__str__()
