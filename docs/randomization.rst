.. _randomization:

.. py:currentmodule:: coolname

=============
Randomization
=============

Re-seeding
----------

As a source of randomness :mod:`coolname` uses standard :py:mod:`random` module,
specifically :py:func:`random.randrange` function.

To re-seed the default generator, simply call :py:func:`random.seed`:

.. code-block:: python

    import os, random
    random.seed(os.urandom(128))

:mod:`coolname` itself never calls :py:func:`random.seed`.

Replacing the random number generator
-------------------------------------

By default, all instances of :class:`RandomGenerator` share the same random number generator.

To replace it for a custom generator:

.. code-block:: python

    from coolname import RandomGenerator
    import random, os
    seed = os.urandom(128)
    generator = RandomGenerator(config, random=random.Random(seed))

To replace it for :func:`coolname.generate` and :func:`coolname.generate_slug`:

.. code-block:: python

    import coolname
    import random, os
    seed = os.urandom(128)
    coolname.replace_random(random.Random(seed))

How randomization works
-----------------------

In this section we dive into details of how :mod:`coolname` generates random sequences.

Let's say we have following config:

.. code-block:: python

    config = {
        'all': {
            'type': 'cartesian',
            'lists': ['price', 'color', 'object']
        },
        # 2 items
        'price': {
            'type': 'words',
            'words': ['cheap', 'expensive']
        },
        # 3 items
        'color': {
            'type': 'words',
            'words': ['black', 'white', 'red']
        },
        # 5 + 6 = 11 items
        'object': {
            'type': 'nested',
            'lists': ['footwear', 'hat']
        },
        # 5 items
        'footwear': {
            'type': 'words',
            'words': ['shoes', 'boots', 'sandals', 'sneakers', 'socks']
        },
        # 6 items
        'hat': {
            'type': 'phrases',
            'phrases': ['top hat', 'fedora', 'beret', 'cricket cap', 'panama', 'sombrero']
        }
    }
    import coolname
    generator = coolname.RandomGenerator(config)

The overall number of combinations is 2 × 3 × (5 + 6) = 66.

You can imagine a space of possible combinations as a virtual N-dimensional array.
In this example, it's 3-dimensional, with sides equal to 2, 3 and 11.

When user calls :meth:`RandomGenerator.generate_slug`,
a random integer is generated via ``randrange(66)``.
Then, the integer is used to pick an element from 3-dimensional array.

.. table:: Possible combinations
    :widths: auto

    =============================  =========================================
    :func:`randrange` returns      :func:`generate_slug` returns
    =============================  =========================================
    0                              cheap-black-top-hat
    1                              cheap-black-fedora
    2                              cheap-black-beret
    3                              cheap-black-cricket-cap
    4                              cheap-black-panama
    5                              cheap-black-sombrero
    6                              cheap-black-shoes
    7                              cheap-black-boots
    8                              cheap-black-sandals
    9                              cheap-black-sneakers
    10                             cheap-black-socks
    11                             cheap-white-top-hat
    12                             cheap-white-fedora
    ...                            ...
    63                             expensive-red-sandals
    64                             expensive-red-sneakers
    65                             expensive-red-socks
    =============================  =========================================

.. note::
   Actual order of combinations is an implementation detail, you should not rely on it.
