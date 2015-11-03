==============================
Random Name and Slug Generator
==============================

.. image:: https://img.shields.io/travis/alexanderlukanin13/coolname.svg
        :target: https://travis-ci.org/alexanderlukanin13/coolname

.. image:: https://img.shields.io/pypi/v/coolname.svg
        :target: https://pypi.python.org/pypi/coolname


Do you want some human-readable strings to identify things in user interface and URLs?

Or do you just like funny randomness?

    >>> from coolname import generate_slug
    >>> generate_slug()
    'big-maize-lori-of-renovation'
    >>> generate_slug()
    'tunneling-amaranth-rhino-of-holiness'
    >>> generate_slug()
    'soft-cuddly-shrew-of-expertise'

**MOAR!!!111**

    >>> print('\n'.join(generate_slug() for x in range(10)))
    small-daffodil-ermine-of-might
    pumpkin-lemur-of-luxury
    flashy-cryptic-quokka-of-enterprise
    zippy-lurking-gibbon-of-excellence
    swinging-glittering-quetzal-of-tornado
    wise-rainbow-sponge-of-faith
    glistening-wolverine-of-unmatched-wholeness
    abiding-toucanet-of-wonderful-agility
    frisky-pelican-of-astonishing-inspiration
    terrestrial-goat-of-marvelous-refinement

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
    33130312740

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

To use custom words and rules, create an instance of
``coolname.RandomNameGenerator`` and call its methods.
::

    generator = RandomNameGenerator(config)
    generator.generate()
    generator.generate_slug()
    generator.randomize()  # re-seeding, similar to random.seed

You can create configuration in Python code - it's just a dictionary -
or you can define it as a set of files (more convenient for larger configs).

* From a single json file
  ::

      from coolname.loader import load_config
      config = load_config('config.json')

* From a directory
  ::

      from coolname.loader import load_config
      config = load_config('config_dir')


Directory must contain ``config.json`` file, with the same structure as config dict,
except that you may omit ``"type": "words"`` rules. For such rules, add plain
``*.txt`` files - they will be automatically added to the resulting config by ``load_config``.

Configuration rules
~~~~~~~~~~~~~~~~~~~

Configuration is a simple flat dictionary of rules:
::

    {
        '<rule_id>': {
            'comment': 'Some info about this rule. Not mandatory.',
            'type': '<nested|cartesian|words|const>',
            # additional fields, depending on type
        },
        ...
    }

``<rule_id>`` is the identifier of rule. Root rule must be named ``'all'`` - that's what you use
when you call ``generate()`` or ``generate_slug()`` without arguments.

There are four types of configuration rules.

* Word list.

  A ground-level building block. Chooses a random word from a list,
  with equal probability.
  ::

      # This will produce random color
      'color': {
          'type': 'words',
          'words': ['red', 'green', 'yellow']
      },
      # This will produce random taste
      'taste': {
          'type': 'words',
          'words': ['sweet', 'sour']
      },
      # This will produce random fruit
      'fruit': {
          'type': 'words',
          'words': ['apple', 'banana']
      },

  Length of word list is a number of words.

* Nested list.

  Chooses a random word from any of the child lists.
  Probability is proportional to child list length.
  ::

      # This will produce random adjective: color or taste
      'adjective': {
          'type': 'nested',
          'lists': ['color', 'taste']
      },

  Child lists can be of any type.

  Number of child lists is not limited.

  Length of nested list is combined length of all child lists.

* Constant.

  It's just a word. Useful for prepositions.
  ::

      'of': {
          'type': 'const',
          'value': 'of'
      },

* Cartesian_ list.

  This element works like a slot machine, and produces a list of length N
  by choosing one random word from N child lists.
  ::

      # This will produce a random list of 4 words,
      # for example: ['my', 'banana', 'is', 'sweet']
      'all': {
          'type': 'cartesian',
          'lists': ['my', 'fruit', 'is', 'adjective']
      },
      # Additional const definitions
      'is': {
          'type': 'const',
          'value': 'is'
      },
      'my': {
          'type': 'const',
          'value': 'my'
      },

  *NOTE: You can have many nested lists, but you should never
  put one Cartesian list inside another.*

  Length of Cartesian list is a product of lengths of child lists.

Let's try the config defined above:
::

    >>> from coolname import RandomNameGenerator
    >>> generator = RandomNameGenerator(config)
    >>> for i in range(3):
    ...     print(generator.generate_slug())
    ...
    my-banana-is-sweet
    my-apple-is-green
    my-apple-is-sour

.. _Cartesian: https://en.wikipedia.org/wiki/Cartesian_product
