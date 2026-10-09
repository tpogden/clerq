# clerq migration: progress

Tracks the `maxwellbloch` → `clerq` rename and the Sphinx → Quarto docs move.
Source plan: `clerq-migration-plan.md`. Tick boxes as work lands. Delete this
file at cutover (Phase 4), or move it to `docs/news/`.

**Branch:** `claude/clerq-spike-migration-plan-efba93` (long-lived; PRs target `next`)
**Last updated:** 2026-10-09

Legend: `[x]` done · `[ ]` to do · 👤 you must do it (external or credentialed) · 🤖 Claude can do it

---

## Phase 0: Pre-work

- [x] 0.1 Reserve `clerq` on PyPI 👤: `clerq 0.0.0` live, verified 2026-10-09
- [x] 0.2 Decisions locked (see plan): continue `0.x.y`, rename in place, `freeze: auto`, shim, new Zenodo DOI
- [ ] 0.3 Confirm `clerq.org` DNS points at GitHub Pages 👤 (A records `185.199.108–111.153`)
- [ ] 0.4 Revoke the account-wide PyPI token used for the stub; create a `clerq`-scoped token for Phase 4 👤
- [ ] 0.5 Decide whether to batch a small API cleanup into the rename release (open question in plan)

## Phase 1: Quarto build (local)

- [x] `docs/_quarto.yml`, `index.qmd`, `installation.qmd`, `examples/index.qmd`
- [x] YAML frontmatter cell on 12 example + 8 usage notebooks (`ef80153`)
- [x] `quarto render` clean: 25 pages, no broken internal links, Plotly renders
- [x] `_site/` gitignored

**Phase 1 complete** apart from the README badge, which moves to Phase 3.
- [x] Draft `mbs-ladder-rydberg-eit-counter.ipynb` stays excluded from the build (same as under Sphinx); finishing it is separate work
- [x] API reference: quartodoc (28 generated pages, committed; CI checks they are up to date)
- [x] Sphinx-only content ported (figure caption, gallery); no `:doc:`/`:ref:` left in notebooks; navbar uses one sidebar per section
- [x] Sphinx removed: `conf.py`, `*.rst`, `make.bat`, `.readthedocs.yml`, `custom.css`; `docs` extra, Makefile targets and CI `docs` job now use Quarto
- [ ] readthedocs badge in README (handled in Phase 3 README rebrand)

Notes: kept the existing `mbs-*` notebook names. The plan's `a0`–`a12` naming does
not exist in this repo.

## Phase 2: Notebook reproducibility audit ✅

Done 2026-10-09 (`95a0e96`). Factor-of-2 fix (PR #289) was merged into `next` first and is in this branch.

- [x] 2.1 Inventory: no random numbers or seeds anywhere; nondeterminism came from `%time` (3 notebooks),
      tqdm progress rates, plotly random div ids, and random nbformat cell ids
- [x] 2.2 Fixed: `%time` removed; `docs/.ipython/.../00-docs-determinism.py` silences tqdm and makes `uuid4`
      deterministic (used only by `docs/execute.sh`); frontmatter cells given a fixed `id`
- [x] 2.3 Two from-scratch executions (no `.qu`, no freeze) give a byte-identical `_freeze/` (7 min each)
- [x] 2.4 `docs/_freeze/` committed (15 MB, 20 notebooks); committed `.qu` caches deleted and `*.qu` ignored everywhere
- [x] Gate: clean clone + plain `quarto render` takes 23 s, starts no kernel, no warnings, 0 broken links, all 20 pages show outputs

How to refresh after changing code or a notebook: `make docs_execute` (runs `docs/execute.sh --fresh`, ~7 min),
review the `_freeze/` diff, commit. Never run `quarto render --execute` directly: it rewrites the source notebooks
with outputs and, without the startup script, produces non-reproducible output.

Things learned:

- 15 of 20 notebooks had no stored outputs (Sphinx executed them at build time), so the Phase 1 site had empty
  pages until now.
- Notebooks used `recalc=False` against committed `.qu` caches, so they never re-solved. Those caches are gone.
- The `mbs-ladder-rydberg-eit-counter` draft is excluded and has no freeze.

## Phase 3: Code rename 🤖 (one discrete commit)

Use `git mv` and a reviewed search-and-replace. The plan's `sed -i` needs `-i ''` on
macOS, and a blanket replace would also touch `uv.lock` and the changelog prose.

- [ ] `git mv src/maxwellbloch src/clerq`
- [ ] Imports in `src/`, `tests/`, `bin/`, and notebook code cells
- [ ] `pyproject.toml`: name, urls, `dev` extra self-reference, description, version stays `0.12.0`
- [ ] Plotly template name `"maxwellbloch"` in `plot/` and the notebooks that use it
- [ ] `.gitignore` (`maxwellbloch/version.py`, `_version.py`), `Makefile`, `MANIFEST.in`
- [ ] `bin/` scripts (`mbsolve`, `obsolve`, movie scripts)
- [ ] README: rename notice, install command, citation block, badges (CI, PyPI, coveralls; drop readthedocs)
- [ ] CI workflows (`ci.yml`, `publish.yml`) and badge URLs
- [ ] `CHANGELOG.md`: add a "Renamed to clerq" entry; do not rewrite history
- [ ] `CLAUDE.md` and memory notes that mention `maxwellbloch`
- [ ] `docs/` pages and notebooks (`install`, `troubleshooting`, import lines)
- [ ] Gate: `uv run pytest -n auto` passes; `uv pip install -e .` gives a working `import clerq`
- [ ] Gate: `uv run ruff check .` and `ruff format --check` clean

## Phase 4: Cutover (single session)

Pre-flight 👤

- [ ] Branch passes CI
- [ ] `quarto render` clean from the `_freeze/` cache
- [ ] PyPI `clerq`-scoped token ready
- [ ] DNS verified
- [ ] Tag the last `maxwellbloch` state (`v-final-maxwellbloch`)

Steps

- [ ] 4.2 Rename the GitHub repo `maxwellbloch` → `clerq` 👤
- [ ] 4.3 PR branch → `next`, then release merge `next` → `master` (per `CLAUDE.md`) 👤/🤖
- [ ] 4.4 Publish `clerq 0.12.0` (or the chosen version) to PyPI 👤
- [ ] 4.5 Build and publish the `maxwellbloch` deprecation shim 🤖 prepares / 👤 uploads
- [ ] 4.6 `publish.yml` Quarto deploy workflow; Pages source `gh-pages`, domain `clerq.org`, enforce HTTPS 👤
- [ ] 4.7 Verification checklist (live site, repo redirect, `pip install clerq`, shim warning, one notebook renders)

## Phase 5: Post-cutover

- [ ] Rename announcement (`docs/news/rename.qmd` + README banner)
- [ ] New Zenodo DOI; add to README citation block alongside the old one 👤
- [ ] Archive `notebooks-maxwellbloch` with a pointer to `clerq.org` 👤
- [ ] External references sweep (personal site, CV, papers, Scholar) 👤

---

## Open issues and risks

- `next` is level with `master`, so the plan's `main` maps to `next` for PRs and to `master` for the release.
- The `.qu` cache files are committed under `docs/` (`!docs/examples/*.qu`). Decide whether `_freeze/` replaces them or they stay.
- The spike's counter-propagation exclusion vs the `usage/counter-propagating` notebook: the notebook documents existing behaviour, so it migrates as is.
- The `pip install clerq` command in `installation.qmd` only works after the Phase 4.4 release.
