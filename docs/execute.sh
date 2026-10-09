#!/usr/bin/env bash
# Re-execute every notebook and store the outputs in the .ipynb files.
#
# Quarto does not execute .ipynb files on a plain `quarto render`; it shows the
# outputs stored in the notebook. So the executed notebooks are the source of
# truth for the site, and `quarto render --execute` writes the fresh outputs
# back into them. Review the notebook diff and commit it.
#
# Solver results (*.qu) are build artifacts; they are deleted first so every
# problem is solved from scratch. The startup script in .ipython silences
# progress bars and makes plotly div ids deterministic, so two runs give
# identical notebooks.
set -euo pipefail
cd "$(dirname "$0")"

find examples usage -name '*.qu' -delete

IPYTHONDIR="$PWD/.ipython" quarto render --execute
