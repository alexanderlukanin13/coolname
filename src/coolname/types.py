import typing

__all__ = [
    'HashT', 'CoolnameConfigListT', 'CoolnameConfigT',
    'ListLike', 'CoolnameConfigT', 'CoolnameConfigListT',
    'RandRangeT', 'RandomT'
]

from abc import ABC, abstractmethod

# For new Python versions with (possible) OpenSSL FIPS support,
# we should pass usedforsecurity=False argument to md5().
if typing.TYPE_CHECKING:
    import hashlib
    HashT = hashlib._Hash  # pragma: no cover
else:
    HashT = typing.Any

# Top-level values of config dict, for example:
# {"comment": "adjective-adjective-noun",
#  "type": "cartesian",
#  "lists": ["adj_far", "adj_near", "subj"]}
CoolnameConfigListT = dict[str, str | list[str] | list[tuple[str, ...]] | int]

# Whole configuration
CoolnameConfigT = dict[str, CoolnameConfigListT]

# random.randrange type
class RandRangeT(typing.Protocol):
    """Protocol for randrange function."""
    def __call__(self,
                 start: int,
                 stop: int | None = None,
                 step: int = 1,
                 /) -> int:
        ...

RandomSeedArgT = None | int | float | str | bytes | bytearray

class RandomT(typing.Protocol):
    """Protocol for random module. We only require seed() and randrange()."""

    def seed(self, a: RandomSeedArgT = None, version: int = 2) -> None:
        ...

    def randrange(self,
                  start: int,
                  stop: int | None = None,
                  step: int = 1,
                  /) -> int:  # position-only arguments as per docs
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
              max_items: int = 4, object_ids: bool = False,
              ) -> None:
        ...

    # Default implementation ignores max_items, and is a synonym for __str__
    def render(self, *, max_items: int = 4) -> str:
        return self.__str__()
