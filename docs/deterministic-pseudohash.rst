==================================
Deterministic strings (pseudohash)
==================================

.. py:currentmodule:: coolname

Typically, if you want to generate per-entity slug and store it persistently, :func:`generate_slug` is sufficient - just don't
forget to check for duplicates, and retry if necessary. Use ``UNIQUE`` constraint on the DB column.

If you need deterministic results, returning the same slug for the same entity every time without storing it somewhere,
consider the separate lightweight package `coolname-hash <https://pypi.org/project/coolname-hash/>`_.

.. code-block:: python

    >>> from coolname_hash import pseudohash_slug
    >>> pseudohash_slug(123)
    'hissing-sage-buzzard-of-faith'
    >>> pseudohash_slug('qwerty')
    'jumping-kickass-bumblebee-of-chaos'
    >>> pseudohash_slug('\x00\x01\xFF')
    'smooth-offbeat-hummingbird-from-avalon'

Note that, just like random generation, it can produce duplicates even for a small number of items.
