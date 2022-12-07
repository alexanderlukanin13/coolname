==============================
Random Name and Slug Generator
==============================

|pypi| |build| |coverage| |docs|

Do you want random human-readable strings?

.. code-block:: python

    >>> from coolname import generate_slug
    >>> generate_slug()
    'big-maize-lori-of-renovation'
    >>> generate_slug()
    'tunneling-amaranth-rhino-of-holiness'
    >>> generate_slug()
    'soft-cuddly-shrew-of-expertise'

Features
========

* Generate slugs, ready to use, Django-compatible.

    .. code-block:: python

        >>> from coolname import generate_slug
        >>> generate_slug()
        'qualified-agama-of-absolute-kindness'

* Generate names as sequences and do whatever you want with them.

    .. code-block:: python

        >>> from coolname import generate
        >>> generate()
        ['beneficial', 'bronze', 'bee', 'of', 'glee']
        >>> ' '.join(generate())
        'limber transparent toad of luck'
        >>> ''.join(x.capitalize() for x in generate())
        'CalmRefreshingTerrierOfAttraction'

* Generate names of specific length: 2, 3 or 4 words.

    .. code-block:: python

        >>> generate_slug(2)
        'mottled-crab'
        >>> generate_slug(3)
        'fantastic-acoustic-whale'
        >>> generate_slug(4)
        'military-diamond-tuatara-of-endeavor'

    *Note: without argument, it returns a random length, but probability of 4‑word name is much higher.*
    *Prepositions and articles (of, from, the) are not counted as words.*

* Use in command line:

    .. code-block:: bash

        $ coolname
        prophetic-tireless-bullfrog-of-novelty
        $ coolname 3 -n 2 -s '_'
        wildebeest_of_original_champagne
        ara_of_imminent_luck

* Over 10\ :sup:`10`\  random names.

    ===== ============== =======================================
    Words Combinations   Example
    ===== ============== =======================================
    4     10\ :sup:`10`\ ``talented-enigmatic-bee-of-hurricane``
    3     10\ :sup:`8`\  ``ambitious-turaco-of-joviality``
    2     10\ :sup:`5`\  ``prudent-armadillo``
    ===== ============== =======================================

    .. code-block:: python

        >>> from coolname import get_combinations_count
        >>> get_combinations_count(4)
        61032399092

* Hand-picked vocabulary. ``sexy`` and ``demonic`` are about the most "offensive" words here -
  but there is only a pinch of them, for spice. Most words are either neutral, such as ``red``, or positive,
  such as ``brave``. And subject is always some animal, bird, fish, or insect - you can't be more neutral than
  Mother Nature.

* `Easy customization <http://coolname.readthedocs.io/en/latest/customization.html>`_. Create your own rules!

    .. code-block:: python

        >>> from coolname import RandomGenerator
        >>> generator = RandomGenerator({
        ...   'all': {
        ...     'type': 'cartesian',
        ...     'lists': ['first_name', 'last_name']
        ...   },
        ...   'first_name': {
        ...     'type': 'words',
        ...     'words': ['james', 'john']
        ...   },
        ...   'last_name': {
        ...     'type': 'words',
        ...     'words': ['smith', 'brown']
        ...   }
        ... })
        >>> generator.generate_slug()
        'james-brown'

Installation
============

.. code-block:: bash

    pip install coolname

**coolname** is written in pure Python and has no dependencies. It works on any modern Python version (3.6+), including PyPy.


.. |pypi| image:: https://img.shields.io/pypi/v/coolname.svg
    :target: https://pypi.python.org/pypi/coolname
    :alt: pypi

.. |build| image:: https://api.travis-ci.org/alexanderlukanin13/coolname.svg?branch=master
    :target: https://travis-ci.org/alexanderlukanin13/coolname?branch=master
    :alt: build status

.. |coverage| image:: https://coveralls.io/repos/alexanderlukanin13/coolname/badge.svg?branch=master&service=github
    :target: https://coveralls.io/github/alexanderlukanin13/coolname?branch=master
    :alt: coverage

.. |docs| image:: https://img.shields.io/readthedocs/coolname.svg
    :target: http://coolname.readthedocs.io/en/latest/
    :alt: documentation
