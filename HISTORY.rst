.. :changelog:

Release history
===============

5.0.0 (2026-04-20)
------------------

This major release has new features and significant internal changes, but it is compatible with 4.x in any normal usage
as described in documentation, and you can upgrade from 4.x with minimal unit test coverage.

There are implementation changes that *technically* can break user code in undocumented scenarios.
Even if it breaks, most likely, it will take a minute to fix.

* Complete typing support, tested with mypy ``strict = True``.

* Default parameter value changed: ``ensure_unique=True``. Custom generators can forget about it
  and still generate sequences without repeating words.
  Consider also using ``ensure_unique_prefix`` (disabled by default).

* :doc:`New parameters <parameters-table>` for advanced words/phrases lists:
  ``strip_whitespace``, ``allow_whitespace``, ``separator``.

* What is considered a valid word? It's now controlled by ``word_regex`` parameter, ``\w+`` by default.

* Stricter config validation for custom generators, with more helpful error messages.

* Custom generator can be rendered into text representation via
  :py:meth:`~coolname.RandomGenerator.render` and :py:meth:`~coolname.RandomGenerator.write`.
  Useful in debugging and logging.

* New public API for manipulating configuration files:
    - :py:func:`~coolname.loader.load_config`
    - :py:func:`~coolname.loader.filter_config`
    - :py:func:`~coolname.loader.save_config_as_module`

* Type :py:class:`~coolname.types.CoolnameConfigT` formally describes config dict.

* Added a few more words, and fixed one spelling mistake.

.. collapse:: Boring technical details

    * ``RandomGenerator`` and global methods now live in the top-level ``coolname`` namespace.
      It won't affect your code if you've been importing directly from ``coolname`` as per documentation.

      Basically, instead of this:

      .. code-block:: python

        >>> from coolname import generate_slug, RandomGenerator
        >>> generate_slug
        <bound method RandomGenerator.generate_slug of <coolname.impl.RandomGenerator object at 0x7a7cb248d6a0>>
        >>> RandomGenerator
        <class 'coolname.impl.RandomGenerator'>

      You will see this (notice no ``impl``):

      .. code-block:: python

        >>> generate_slug
        <bound method RandomGenerator.generate_slug of <coolname.RandomGenerator object at 0x75038bacde80>>
        >>> RandomGenerator
        <class 'coolname.RandomGenerator'>

    * Using arbitrary types (such as int) is word/phrase lists is now *strictly forbidden*,
      not just "undocumented and fails in most circumstances".

      For example, the following invalid configuration always raises an exception:

      .. code-block:: python

        {
          "all": {
            "type": "phrases",
            "phrases": [[1,2], [3,4]]}  # don't do this
        }

    * ``RandomGenerator`` does not accept :py:class:`collections.abc.Mapping` as config anymore,
      only plain ``dict`` as described by type ``coolname.types.CoolnameConfigT``.

4.2.0 (2026-04-11)
------------------

* Backported changes in word lists from 5.0.0

* Better mypy support

4.1.0 (2026-03-17)
------------------

* Added a few words

4.0.0 (2026-02-22)
------------------

* **Breaking change:** Python 3.10+ is required (because of packaging - see below).
  Tests cover Python 3.10-3.14 and PyPy 3.10-3.11.

* Switched to modern packaging with ``pyproject.toml``. This should not affect user experience.
  Support for egg files is officially dropped, but the package is still pure Python and should work in bundles
  (such as PyInstaller - see documentation).

* Added a lot of adjectives

* Minor optimizations

3.0.0 (2026-01-29)
------------------

* **Breaking change:** Python 3.6 is not supported anymore. Tests cover Python 3.7-3.14 and PyPy 3.7-3.11.

* Better type hints (now checked with mypy)

* Minor bug fixed, concerning abnormal configs (most likely didn't affect anyone)

* More mythical animals + one mistake fixed + few other words

2.2.0 (2023-01-09)
------------------

* More dogs, cats and cows!

2.1.0 (2022-12-07)
------------------

* Support OpenSSL FIPS by using ``hashlib.md5(..., usedforsecurity=False)``

2.0.0 (2022-10-24)
------------------

* Support for old Python versions (<3.5) is dropped, because it's 2022

* Command line usage and pipx support.

* With additional owls and bitterns

1.1.0 (2018-08-02)
------------------

* 32-bit Python is supported.

1.0.4 (2018-02-17)
------------------

* **Breaking changes:**

    - Renamed :class:`RandomNameGenerator` to :class:`RandomGenerator`.

    - :func:`randomize` was removed, because it was just an alias to :func:`random.seed`.

* `Phrase lists <https://coolname.readthedocs.io/en/latest/customization.html#phrases-list>`_
  give you even more freedom when creating custom generators.

* You can seed or even replace the underlying :class:`random.Random` instance, see
  `Randomization <https://coolname.readthedocs.io/en/latest/randomization.html>`_.

* Change the default generator using ``COOLNAME_DATA_DIR`` and ``COOLNAME_DATA_MODULE``. This also saves memory!

* Total number of combinations = 60 billions.

0.2.0 (2016-09-28)
------------------

* More flexible configuration: ``max_length`` and ``max_slug_length`` constraints.
  See `documentation <http://coolname.readthedocs.io/en/latest/customization.html#length-limits>`_.

* Total number of combinations increased from 43 to 51 billions.

0.1.1 (2015-12-17)
------------------

* Consistent behavior in Python 2/3: output is always unicode.

* Provide ``from coolname.loader import load_config`` as a public API for loading custom configuration.

* More strict configuration validation.

* Total number of combinations increased from 33 to 43 billions.

0.1.0 (2015-11-03)
------------------

* First release on PyPI.
