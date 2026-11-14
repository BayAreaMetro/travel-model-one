"""One run of one scenario: what it does, and where it happens.

- :mod:`tm1.run.iterations` -- which steps run, in which round, and which of them
  this invocation wants. Pure: config in, ordered list out.
- :mod:`tm1.run.model` -- :func:`~tm1.run.model.run_model`, which walks that list,
  calls each step and logs what happened. The successor to ``RunModel.bat``.

``tm1.status`` reads :mod:`~tm1.run.iterations` to say what a run *would* do. It
never imports :mod:`~tm1.run.model`: watching a run must not depend on the code
that runs one.
"""
