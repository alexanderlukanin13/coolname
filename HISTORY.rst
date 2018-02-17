.. :changelog:

Release history
===============

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
