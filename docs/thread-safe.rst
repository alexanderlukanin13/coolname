==================
Is it thread-safe?
==================

:mod:`coolname` is thread-safe and virtually stateless.
The only shared state is the global :class:`random.Random` instance, which is also thread-safe.
You can re-seed or even completely override it, see :ref:`randomization`.
