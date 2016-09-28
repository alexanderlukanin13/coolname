==============================
Random Name and Slug Generator
==============================

.. image:: https://img.shields.io/travis/alexanderlukanin13/coolname.svg
        :target: https://travis-ci.org/alexanderlukanin13/coolname

.. image:: https://img.shields.io/pypi/v/coolname.svg
        :target: https://pypi.python.org/pypi/coolname

.. image:: https://coveralls.io/repos/alexanderlukanin13/coolname/badge.svg?branch=master&service=github
        :target: https://coveralls.io/github/alexanderlukanin13/coolname?branch=master


Do you want random human-readable strings to identify things in user interface and URLs?

    >>> from coolname import generate_slug
    >>> generate_slug()
    'big-maize-lori-of-renovation'
    >>> generate_slug()
    'tunneling-amaranth-rhino-of-holiness'
    >>> generate_slug()
    'soft-cuddly-shrew-of-expertise'

Features
--------

* Generate slugs, ready to use, Django-compatible.

    >>> from coolname import generate_slug
    >>> generate_slug()
    'qualified-agama-of-absolute-kindness'

* Generate names as sequences and do whatever you want with them.

    >>> from coolname import generate
    >>> generate()
    ['beneficial', 'bronze', 'bee', 'of', 'glee']
    >>> ' '.join(generate())
    'limber transparent toad of luck'
    >>> ''.join(x.capitalize() for x in generate())
    'CalmRefreshingTerrierOfAttraction'

* Generate names of specific length: 2, 3 or 4 words.

    >>> generate_slug(2)
    'mottled-crab'
    >>> generate_slug(3)
    'fantastic-acoustic-whale'
    >>> generate_slug(4)
    'military-diamond-tuatara-of-endeavor'

    *Note: without argument, it returns a random length, but probability of 4-word name is much higher.*

* Over 10\ :sup:`10`\  random names.

    ===== ============== =======================================
    Words Combinations   Example
    ===== ============== =======================================
    4     10\ :sup:`10`\ ``talented-enigmatic-bee-of-hurricane``
    3     10\ :sup:`8`\  ``ambitious-turaco-of-joviality``
    2     10\ :sup:`5`\  ``prudent-armadillo``
    ===== ============== =======================================

    >>> from coolname import get_combinations_count
    >>> get_combinations_count(4)
    51560093424

* Hand-picked vocabulary. ``sexy`` and ``demonic`` are about the most "offensive" words here -
  but there is only a pinch of them, for spice. Most words are either neutral, such as ``red``, or positive,
  such as ``brave``. And subject is always some animal, bird, fish, or insect - you can't be more neutral than
  Mother Nature.

* Easy customization. Create your own rules!

    >>> from coolname import RandomNameGenerator
    >>> generator = RandomNameGenerator({
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

Alternatives
------------

For random human names, addresses and more, check out
`Faker <https://pypi.python.org/pypi/fake-factory/>`_
(or `Gimei <https://pypi.python.org/pypi/gimei/>`_ if you want Japanese data).

Customization
-------------

You can create custom config to generate word sequences of any kind:

http://coolname.readthedocs.io/en/latest/customization.html
