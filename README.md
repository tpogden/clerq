# clerq

[![Build Status](https://github.com/tpogden/clerq/actions/workflows/ci.yml/badge.svg)](https://github.com/tpogden/clerq/actions/workflows/ci.yml)
[![Documentation](https://img.shields.io/badge/docs-clerq.org-blue)](https://clerq.org)
[![PyPI](https://img.shields.io/pypi/v/clerq)](https://pypi.org/project/clerq/)

clerq is a Python package for solving the coupled Maxwell-Bloch
equations describing the nonlinear propagation of near-resonant light through
thermal quantised systems such as atomic vapours.

> **Renamed from `maxwellbloch`.** This package was previously published as
> `maxwellbloch`. Install `clerq` and change `import maxwellbloch` to
> `import clerq`. The old name will keep working through a transitional release
> that re-exports `clerq` with a `DeprecationWarning`. The API is otherwise
> unchanged.

![](example.gif)

Above is an [example solution][4pi] for the propagation of a 4π pulse through a
dense atomic vapour. The pulse immediately breaks up on entering the medium and
the resultant pulses form two optical solitons each with a pulse
area of 2π.

[4pi]: https://github.com/tpogden/notebooks-maxwellbloch/blob/master/examples/mb-solve-two-sech-4pi.ipynb


## Documentation

Docs for the project are at [clerq.org][docs].

## Install

The recommended way to install is via [uv](https://docs.astral.sh/uv/):

```sh
uv pip install clerq
```

Or using pip:

```sh
pip install clerq
```

If you prefer Conda, you can create and activate an environment with the
required dependencies with
```sh
conda create --name mb -c conda-forge python=3.11 qutip
conda activate mb
pip install clerq
```

More detailed installation instructions can be found in the [docs][docs] along with many example problems.

## Attribution

If you use clerq for research, please cite the original package, which was
published as MaxwellBloch:
```
@misc{ogden2020maxwellbloch,
  author = {Ogden, Thomas P.},
  title = {{MaxwellBloch}: a Python package for solving the coupled 
    Maxwell-Bloch equations describing the nonlinear propagation of 
    near-resonant light through thermal quantised systems such as atomic 
    vapors.},
  year = {2020},
  publisher = {GitHub},
  journal = {GitHub repository},
  howpublished = {\url{https://github.com/tpogden/clerq}}
}
```
A citation for clerq itself, with its own DOI, will be added with the first
release under the new name.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

MIT License. See [LICENSE.txt](LICENSE.txt).

[docs]: https://clerq.org/
