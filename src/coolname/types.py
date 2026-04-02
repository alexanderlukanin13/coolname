import typing

__all__ = [
    'HashT', 'CoolnameConfigListT', 'CoolnameConfigT',
    'ListLike', 'CoolnameConfigT', 'CoolnameConfigListT',
    'RandRangeT', 'RandomT'
]


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


class ListLike(typing.Protocol):
    """Unified Protocol for AbstractNestedList and WordWrapper"""

    length: int
    multiword: bool

    def __getitem__(self, item: int) -> str | list[str]:
        ...

    def squash(self, hard: bool, cache: dict[bytes, 'ListLike']) -> 'ListLike':
        ...

    def write(self, stream: typing.TextIO, *, indent: str = '', object_ids: bool = False) -> None:
        ...
