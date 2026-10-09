#!/usr/bin/env bash
# Re-execute every notebook and refresh docs/_freeze.
#
# Rendering with --execute writes outputs back into the source .ipynb files.
# We keep sources output-free (outputs live in _freeze), so back them up first
# and restore them afterwards. Pass --fresh to also discard cached solver
# results (*.qu) and the previous freeze so everything is solved from scratch.
set -euo pipefail
cd "$(dirname "$0")"

if [[ "${1:-}" == "--fresh" ]]; then
  rm -rf _freeze
  find examples usage -name '*.qu' -delete
fi

backup=$(mktemp -d)
trap 'cp -p "$backup"/examples/*.ipynb examples/; cp -p "$backup"/usage/*.ipynb usage/; rm -rf "$backup"' EXIT
mkdir -p "$backup/examples" "$backup/usage"
cp -p examples/*.ipynb "$backup/examples/"
cp -p usage/*.ipynb "$backup/usage/"

# The startup script silences progress bars and makes plotly ids deterministic.
IPYTHONDIR="$PWD/.ipython" quarto render --execute
