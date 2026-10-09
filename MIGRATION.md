# clerq migration: progress

Tracks the `maxwellbloch` → `clerq` rename and the Sphinx → Quarto docs move.
Source plan: `clerq-migration-plan.md`. Tick boxes as work lands. Delete this
file at cutover (Phase 4), or move it to `docs/news/`.

**Branch:** `claude/clerq-spike-migration-plan-efba93` (long-lived; PRs target `next`)
**Last updated:** 2026-10-09 (cutover complete)

Legend: `[x]` done · `[ ]` to do · 👤 you must do it (external or credentialed) · 🤖 Claude can do it

---

## Phase 0: Pre-work

- [x] 0.1 Reserve `clerq` on PyPI 👤: `clerq 0.0.0` live, verified 2026-10-09
- [x] 0.2 Decisions locked (see plan): continue `0.x.y`, rename in place, `freeze: auto`, shim, new Zenodo DOI
- [x] 0.3 `clerq.org` DNS points at GitHub Pages 👤: apex A records `185.199.108–111.153` and `www` CNAME to `tpogden.github.io`, verified 2026-10-09 (MX left as Hover mail forwarding)
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

## Phase 3: Code rename ✅

Done 2026-10-09 (`61d85d4` rename, `aa6a2b0` regenerated docs). Version stays `0.12.0`.

- [x] `git mv src/maxwellbloch src/clerq`; imports in `src/`, `tests/`, `bin/` and notebook code cells
- [x] `pyproject.toml` name, URL, `dev` extra self-reference; `uv.lock` re-locked
- [x] Plotly template `"maxwellbloch"` → `"clerq"`; `.qu` metadata key now `clerq` (old savefiles still load)
- [x] `.gitignore`, `bin/` scripts, `CLAUDE.md`, Makefile
- [x] README: rename notice, install, `clerq.org`, citation (original MaxwellBloch citation kept; clerq DOI pending); coveralls badge dropped (not used in CI)
- [x] `CHANGELOG.md`: `[Unreleased]` entry for the rename and docs move
- [x] CI: no `maxwellbloch` strings in the workflows (docs job already switched to Quarto in Phase 1)
- [x] Gate: 208 tests pass; `ruff check` and `ruff format --check` clean
- [x] Gate: wheel builds as `clerq-0.12.0`, installs in a clean venv, `import clerq` works, `import maxwellbloch` fails, `mbsolve`/`obsolve`/movie scripts installed
- [x] Gate: re-executed freeze is byte-identical to the pre-rename freeze once the name is normalised, so the rename changes no numerics
- [x] Gate: clean-clone `quarto render` 24 s, 0 broken links, all pages have outputs

Changed on purpose vs the plan: the site description in `_quarto.yml` says "Maxwell–Bloch solver", not
"Differentiable Maxwell–Lindblad solver", because nothing is differentiable until the spike passes. The plan's
pyproject description was left as the original.

Deferred to Phase 4/5 (needs the repo rename, PyPI or you):

- PyPI trusted publishing (`publish.yml`, environment `pypi`) is registered for project `MaxwellBloch`;
  register `clerq` as a trusted publisher (or use a project token) before tagging 👤
- GitHub URLs in README, `pyproject.toml` and `_quarto.yml` point at `tpogden/clerq`, which only exists after
  the repo rename (Phase 4.2)
- Zenodo DOI and clerq citation
- Existing bug found in passing, unrelated to the rename: `mbsolve --help` crashes under Python 3.14 (unescaped `%`
  in an argparse help string)

## Phase 4: Cutover (single session)

### Prepared (🤖, done 2026-10-09)

- [x] `maxwellbloch` shim built and tested, **not uploaded**: `.../scratchpad/maxwellbloch-shim` (`dist/maxwellbloch-0.12.1*`,
      `twine check` passes). Unlike the plan's `from clerq import *`, it aliases submodules, so `from maxwellbloch import mb_solve`,
      `from maxwellbloch.field import Field` and `maxwellbloch.plot` return the same objects as `clerq`; it warns with
      `DeprecationWarning`; and it keeps the `[plot]`, `[test]`, `[docs]`, `[dev]` extras. It requires `clerq>=0.13.0`.
- [x] `.github/workflows/docs.yml`: publishes the Quarto site to `gh-pages` on push to `master` (and manually). Verified that a
      clean clone renders with no Jupyter installed, from `docs/_freeze`
- [x] `docs/CNAME` (`clerq.org`), included in the site via `resources`
- [x] Existing `publish.yml` (tag `v*` → tests → build → PyPI via OIDC → GitHub release) needs no code change

### Version decision (agreed 2026-10-09: clerq 0.13.0, shim 0.12.1)

Last `maxwellbloch` on PyPI is **0.12.0**. The first clerq release contains the factor-of-2 physics fix (a breaking change to
results), so I recommend **`clerq 0.13.0`** via `uv run bump-my-version bump minor`, and the shim as `maxwellbloch 0.12.1`
(above 0.12.0, so pip picks it, and pinned `==0.12.0` users are untouched). The stub `clerq 0.0.0` is already on PyPI.

### Order of operations (each step depends on the one before)

Pre-flight 👤

- [ ] This branch's PR (to `next`) is green on CI
- [x] DNS for `clerq.org` verified (2026-10-09)
- [x] Tagged the last pre-rename release as `final-maxwellbloch` (on the `v0.12.0` commit `baa79e2`), 2026-10-09. Not named `v-final-…`: `publish.yml` runs on any `v*` tag and would have tried to republish to PyPI

Steps

1. [x] 👤 **Rename the GitHub repo** `maxwellbloch` → `clerq` (Settings → General). Then update local remotes:
       `git remote set-url origin git@github.com:tpogden/clerq.git`
2. [x] 👤 **Register PyPI trusted publishers** (PyPI → project `clerq` → Publishing): owner `tpogden`, repo `clerq`,
       workflow `publish.yml`, environment `pypi`. The old one is registered for `MaxwellBloch` and will not work for `clerq`.
       Check the GitHub environment `pypi` still exists after the rename
3. [x] 🤖/👤 PR #301 merged into `next` (merge commit `af73bc2`)
4. [x] 🤖 `next` bumped to 0.13.0 (`3347b6e`, tag `v0.13.0`). `uv.lock` records the project version and `bump-my-version` does not update it, so: `bump-my-version bump minor --no-commit --no-tag`, `uv lock`, then commit and tag by hand
5. [x] 👤 Release merge (done 2026-10-09, `master` at `efaf96d`; the `pypi` environment has a required reviewer, so approve the run in the Actions UI): `git checkout master && git merge --no-ff next && git push && git push --tags`; the tag runs
       `publish.yml`, which uploads `clerq 0.13.0` to PyPI and makes the GitHub release. The push to `master` also runs `docs.yml`
6. [x] 👤 Pages (HTTPS enforced). **First run needs a `gh-pages` branch to exist**: `quarto publish` cannot create it, so the first `docs.yml` run failed until an empty orphan `gh-pages` branch was pushed and the workflow re-run. GitHub then configured Pages itself from the branch and `CNAME`: Settings → Pages → source branch `gh-pages`, custom domain `clerq.org`, enforce HTTPS (certificate can take ~1 h)
7. [x] 👤 Shim `maxwellbloch 0.12.1` uploaded. Upload the shim (after `clerq 0.13.0` is live, since it depends on it):
       `cd <scratchpad>/maxwellbloch-shim && uvx twine upload dist/*` (use a `maxwellbloch`-scoped token)
8. [x] 🤖 Verification checklist below

Verification

- [x] `https://clerq.org` loads; one example notebook shows plots
- [x] `https://github.com/tpogden/maxwellbloch` redirects to `clerq`
- [x] Fresh venv: `pip install clerq` and `import clerq` work; `clerq.__version__ == "0.13.0"`
- [x] Fresh venv: `pip install maxwellbloch` installs the shim and clerq; `from maxwellbloch import mb_solve` works and warns
- [x] `pip install --no-cache-dir` if PyPI metadata lags (it did, briefly: the `/pypi/<name>/json` summary endpoint showed 0.12.0 for a few minutes after the shim upload while the simple index already had 0.12.1)

Verified 2026-10-09: `clerq 0.13.0` and `maxwellbloch 0.12.1` on PyPI; fresh-venv installs of both; `maxwellbloch==0.12.0` pin
still installs the old release alone; shim solve output is identical to clerq; `https://clerq.org` (and `www`, and http) serve
the site over HTTPS; GitHub URLs redirect; release `v0.13.0` published; CI green on `master`.

### Rollback notes

- PyPI releases cannot be re-uploaded or deleted usefully; if `clerq 0.13.0` is broken, yank it and release `0.13.1`
- Do the shim upload last so a bad clerq release does not leave `maxwellbloch` users pointed at it
- The repo rename is reversible (rename back), but do not create a new `maxwellbloch` repo; that would break the redirect

## Phase 5: Post-cutover

- [x] Rename announcement: `docs/news/rename.qmd`, banner on the site home page and README (includes the factor-of-2 results change)
- [ ] New Zenodo DOI; add to README citation block alongside the old one 👤
- [x] Archived `notebooks-maxwellbloch` 2026-10-09 with a README pointer to `clerq.org`, repo description and homepage updated, issue #32 closed 👤
- [ ] External references sweep (personal site, CV, papers, Scholar) 👤

---

## Follow-ups after the cutover

- [ ] PR #278 (A5 stimulated echo, targets `next`) still imports `maxwellbloch`: merge `next` into it and rename imports
      (`perl -pi -e 's/maxwellbloch/clerq/g'` on its files) before it merges; its notebook needs a `docs/_freeze` refresh (`make docs_execute`)
- [ ] Dependabot PRs #297–#300 target `master`; they should rebase cleanly, otherwise `@dependabot rebase`
- [ ] `mbsolve --help` crashes on Python 3.14 (unescaped `%` in a help string; `-p/--pbarchunksize` may be dead). Branch
      `fix/mbsolve-help-percent` exists from a separate session; deliberately not included in 0.13.0, ships in 0.13.1
- [ ] Quarto API page titles come out lowercased (`mb_solve.mbsolve`); cosmetic
- [ ] Release workflow attaches `default.gitignore` (uv writes `dist/.gitignore`); cosmetic: use `dist/*.whl dist/*.tar.gz` in `publish.yml`
- [ ] quartodoc prints ~14 docstring warnings (parameters documented but not in the signature) in `ob_atom.py`, `hyperfine.py`, `spectral.py`
- [ ] CHANGELOG has no entries between 0.9.0 and 0.12.0
- [x] CI `bench` gate was flaky (50% tolerance vs measured run-to-run variance of up to +127% on identical code); widened to 200% in #306

## Open issues and risks

- `next` is level with `master`, so the plan's `main` maps to `next` for PRs and to `master` for the release.
- The `.qu` cache files are committed under `docs/` (`!docs/examples/*.qu`). Decide whether `_freeze/` replaces them or they stay.
- The spike's counter-propagation exclusion vs the `usage/counter-propagating` notebook: the notebook documents existing behaviour, so it migrates as is.
- The `pip install clerq` command in `installation.qmd` only works after the Phase 4.4 release.
