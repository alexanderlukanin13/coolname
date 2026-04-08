==================
Is it thread-safe?
==================

:mod:`coolname` is thread-safe and virtually stateless.
The only shared state is the global :class:`random.Random` instance,
which is thread-safe according to documentation.
You can re-seed or even completely override it, see :ref:`randomization`.

:mod:`coolname` should work in `free-threaded python <https://docs.python.org/3/howto/free-threading-python.html>`_ too,
but this is not tested yet (volunteers welcome!).
