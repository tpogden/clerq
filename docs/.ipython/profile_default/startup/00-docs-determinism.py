"""Make executed docs notebooks reproducible. Loaded via IPYTHONDIR by execute.sh.

- tqdm progress bars print wall-clock rates, so they differ on every run.
- Plotly names each figure <div> with a random uuid4.

Wrapped in a function because IPython does not keep startup-script globals.
"""


def _make_docs_deterministic():
    import itertools
    import uuid

    import tqdm.std

    orig_init = tqdm.std.tqdm.__init__

    def quiet_init(self, *args, **kwargs):
        kwargs["disable"] = True
        orig_init(self, *args, **kwargs)

    tqdm.std.tqdm.__init__ = quiet_init

    counter = itertools.count(1)
    uuid.uuid4 = lambda: uuid.UUID(int=next(counter))


_make_docs_deterministic()
