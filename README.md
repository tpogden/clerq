# clerq

[![Build Status](https://github.com/tpogden/clerq/actions/workflows/ci.yml/badge.svg)](https://github.com/tpogden/clerq/actions/workflows/ci.yml)
[![Documentation](https://img.shields.io/badge/docs-clerq.org-blue)](https://clerq.org)
[![PyPI](https://img.shields.io/pypi/v/clerq)](https://pypi.org/project/clerq/)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23269881.svg)](https://doi.org/10.5281/zenodo.23269881)

clerq solves the propagation of classical electromagnetic fields through media
of open quantum systems, using Maxwell's equations coupled to the Lindblad
master equation. It is used for near-resonant light in thermal atomic vapours,
with two-, three- and many-level atoms, spontaneous decay, dephasing and
Doppler broadening.

> **Renamed from `maxwellbloch`.** This package was previously published as
> `maxwellbloch`. Install `clerq` and change `import maxwellbloch` to
> `import clerq`. The old name keeps working through a transitional release
> that re-exports `clerq` with a `DeprecationWarning`. Version 0.13.0 also
> fixes a factor-of-2 error in the propagation equation, so results from
> earlier versions change. See the
> [announcement](https://clerq.org/news/rename.html).

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

If you use clerq for research, please cite it. The DOI below is the concept DOI,
which covers all versions and always resolves to the latest; Zenodo also gives
each release its own version DOI.

```
@software{ogden_clerq,
  author = {Ogden, Thomas P.},
  title = {clerq},
  year = {2026},
  publisher = {Zenodo},
  doi = {10.5281/zenodo.23269881},
  url = {https://doi.org/10.5281/zenodo.23269881}
}
```

Work that used earlier versions, published as MaxwellBloch, can also cite the
original package:
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
A `CITATION.cff` is included too (GitHub's "Cite this repository" button reads it).

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

MIT License. See [LICENSE.txt](LICENSE.txt).

[docs]: https://clerq.org/
