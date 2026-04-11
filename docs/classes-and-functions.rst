=====================
Classes and functions
=====================

Default generator
=================

.. py:currentmodule:: coolname

.. autofunction:: generate
.. autofunction:: generate_slug
.. autofunction:: get_combinations_count
.. autofunction:: replace_random

Custom generators
=================

.. autoclass:: RandomGenerator
    :members:

.. autoclass:: InitializationError
.. autoclass:: ConfigurationError()

Configuration
=============

These functions are primarily intended for development.

.. autofunction:: coolname.loader.load_config

.. autofunction:: coolname.loader.filter_config

.. autofunction:: coolname.loader.save_config_as_module

Types and Protocols
===================

In advanced custom setup, you can use following protocols and types for typing:

.. py:currentmodule:: coolname.types

.. autodata:: CoolnameConfigT
.. autoclass:: RandomT
    :members:
.. autodata:: RandomSeedArgT
