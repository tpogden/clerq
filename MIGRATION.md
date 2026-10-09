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

## Phase 2: Notebook reproducibility audit 🤖

**Blocked on the factor-of-2 fix.** `fix/maxwell-propagation-factor-of-2` (`9b02515`) is not merged
into `next`/`master`. It changes `mb_solve.py` and `spectral.py`, so every `.qu` cache and every
frozen output made before it lands is wrong. Merge it first, then do the steps below.

Findings from the first static pass and a trial `quarto render --execute` (5 min, no errors):

- 15 of 20 notebooks have **no stored outputs** (Sphinx executed them at build time), so the
  site only shows figures after an execute-render; `_freeze/` is therefore required, not optional.
- No notebook uses random numbers or seeds. Timing noise is limited to `%time` cells in 4 notebooks.
- Most notebooks call `mbsolve(recalc=False)`, so they **load committed `.qu` caches instead of solving**.
  Stale caches are the main reproducibility risk. 20 caches changed on a trial run.
- Rendering a notebook with `--execute` writes outputs back into the source `.ipynb`; the render
  step must restore them (or the policy must change to store outputs in the notebooks).

- [ ] 2.1 Inventory nondeterminism in each notebook (seeds, `%time`, timing output, plot rendering)
- [ ] 2.2 Fix and pin: seeds, strip timing cells, pin matplotlib/plotly/kaleido for the docs env
- [ ] 2.3 Re-execute all notebooks twice in a clean env; diff outputs
- [ ] 2.4 Commit `docs/_freeze/`
- [ ] Gate: `quarto render` from a clean checkout matches the local build

Per notebook (tick when executed twice with matching output):

- [ ] usage/two-level
- [ ] usage/three-level
- [ ] usage/structure
- [ ] usage/spectral-analysis
- [ ] usage/velocity-classes
- [ ] usage/counter-propagating
- [ ] usage/plotting
- [ ] usage/built-in-time-functions
- [ ] examples/mbs-linear-absorption
- [ ] examples/mbs-sit-area-theorem
- [ ] examples/mbs-two-photon-echo
- [ ] examples/mbs-lambda-eit-slow-light
- [ ] examples/mbs-lambda-cpt
- [ ] examples/mbs-lambda-adiabatons
- [ ] examples/mbs-vee-simultons
- [ ] examples/mbs-ladder-weak-pulse-coupling-decay
- [ ] examples/mbs-ladder-autler-townes
- [ ] examples/mbs-Rb87_5s12_5p12_F11_q1-weak-pulse-decay
- [ ] examples/mbs-Rb87_5s12_5p12_F11_q1-sech-2pi
- [ ] examples/mbs-Rb87_5s12_5p32_F23_q1-weak-pulse-decay

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
