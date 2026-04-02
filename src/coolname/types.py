import typing

__all__ = ['HashT', 'ListConfigT', 'ConfigT']


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
ListConfigT = dict[str, str | list[str] | list[tuple[str, ...]] | int]

# Whole configuration
ConfigT = dict[str, ListConfigT]

# random.randrange type
class RandRangeT(typing.Protocol):
    def __call__(self, start: int, stop: int | None = None, step: int = 1) -> int:
        ...
