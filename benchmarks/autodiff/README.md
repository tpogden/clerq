# clerq.autodiff benchmarks

A reproducible harness for the measurements on the docs page
[Autodiff performance and validation](../../docs/benchmarks.qmd). It is not run by CI.

| file | experiment |
|-|-|
| `e1_cost.py` | E1: the time of one gradient against the number of parameters N (forward, reverse, forward-mode, finite differences through JAX; finite differences through clerq are estimated from one `solve()`) |
| `e2_memory.py` | E2: peak memory of one gradient against the number of z steps and velocity classes, for strategies `s2`, `s3`, `s4` (one process per cell) |
| `e3_accuracy.py` | E3: gradient accuracy against fixed-step finite differences, forward against reverse mode, field error against `solve()` |
| `e4_compile.py` | E4: compile time and first-call against steady-state time (fresh process per system) |
| `e5_time_to_solution.py` | E5: a Doppler-broadened memory design problem, free-form autodiff design against a 5-parameter baseline |
| `spectrum_fit.py`, `spectrum_fit_diagnose.py` | a simulated-data spectrum fit (see below); not part of `run_tier2.sh` |
| `run_tier2.sh` | everything above, one after another (about 5 hours), plus E6: E1 on the commit before PR 361 and after it |
| `analyse.py` | tables (`results/tables.md`) and the figures in `docs/benchmarks-figures` |
| `results/` | the raw JSONL records (one per cell, with machine and version metadata) and the logs |

Run one experiment, for example:

```bash
uv sync --extra jax --extra plot
uv run python benchmarks/autodiff/e1_cost.py --systems lambda_eit --ns 2 10 50 --tag e1_try
uv run python benchmarks/autodiff/analyse.py --no-figures
```

For clean numbers keep the machine on AC power, awake (`caffeinate -i -s -w <pid>`) and otherwise idle; the
load average is stored with every record. `--quick` shrinks the grids for a smoke test and the output tag
`smoke_*` is ignored by `analyse.py`. To compare against an older source tree (E6), run the same script with
`PYTHONPATH=<checkout>/src` and a different `--tag`; the harness does not depend on newer API.

The benchmarks parametrise a free-form probe control as `omega0[0] = basis @ coefficients` and call the
private `AutodiffPropagation._propagate(..., adjoint=ForwardMode())` for forward mode, so they may need a
small update if those internals change.

## Spectrum fit on simulated data (`spectrum_fit.py`)

A transmitted-probe spectrum of a lambda-EIT medium (11 probe detunings, noise 0.01, optical depth about 10) is fitted for six
parameters: the coupling Rabi frequency and detuning, the optical depth, and three decay rates through `decay_rates`
(`gamma_01`, `gamma_21`, ground-state dephasing). The point of the script is the exact gradient and Hessian and the identifiability
analysis they give, not a comparison of optimisers. Everything is float64 on a CPU, with simulated data only.

- Detunings in a lambda system: clerq's `detunings` are level shifts, so the coupling entry is the two-photon detuning. A fixed
  laboratory coupling detuning `dc` and a scanned probe detuning `dp` need `detunings = [dp, dc - dp]`; passing `[dp, dc]` gives
  spectra that are not those of a lambda system.
- Hessian: forward-over-reverse fails with the default adjoint (`custom_vjp` does not take a JVP). The script uses forward-over-forward
  through the private `_propagate(adjoint=ForwardMode())`. It took about 60 s for 6 parameters and 11 detunings (about 8 gradients).
- Checks (seed 1): the gradient agrees with central finite differences to 9e-11 and the Hessian to 4e-8 (relative; fixed-step solver
  with `n_steps = 997`, 6 of the 11 detunings; 53 and 211 steps per slice gave NaN, cause not investigated). The fitted spectrum agrees
  with `PropagationSolver.solve()` to 4e-6 on 4 of the 11 detunings.

Identifiability over five noise realisations (same truth, `gamma_01 + gamma_21 = 2.0`, `delta_c = 0.4`):

| seed | chi2 of the noise alone | chi2 at the optimum | Hessian | `gamma_01 + gamma_21` | `gamma_deph` | `delta_c` |
|-|-|-|-|-|-|-|
| 1 | 4.5 | 3.34 | positive definite | 2.05 +- 0.24 | 0.06 +- 0.37 | 0.38 +- 0.06 |
| 2 | 13.0 | 10.33 | positive definite | 1.82 +- 0.24 | 0 (boundary) | 0.36 +- 0.02 |
| 3 | 27.4 | 19.08 | indefinite | 1.43 | 0.29 | about 0 |
| 4 | 9.5 | 6.69 | positive definite | 2.10 +- 0.30 | 0 (boundary) | 0.99 +- 0.12 |
| 5 | 8.2 | 4.84 | indefinite | 1.41 | 0.006 | 0.61 |

- `gamma_01 - gamma_21` is never determined: it is a soft or null Hessian direction in all five seeds, and in seed 1 the chi2 is
  flat to three decimals along the constant-sum curve.
- Ground-state dephasing is only weakly determined at this pulse length and noise: it runs to zero in two seeds and otherwise follows
  the noise.
- The optimum itself is not stable: seed 4 sits in a different minimum (`delta_c` 5 sigma from the truth, chi2 below that of the truth),
  and the optima of seeds 3 and 5 are far from the truth with an indefinite Hessian. Standard deviations are meaningful only where the
  Hessian is positive definite (seeds 1, 2, 4). Seed 3's noise alone has chi2 = 27.4 for 11 points (p about 0.004).

Optimisers (4 displaced starts, fixed iteration caps): Levenberg-Marquardt with the forward-mode Jacobian reached the best chi2 from 3
of 4 starts in about 6 min each. Adam (60 steps), L-BFGS (15 iterations) and Nelder-Mead (250 evaluations) all stopped unconverged
(gradient norms 4 to 140, against below 0.02 for LM). `spectrum_fit_diagnose.py` reran Adam and L-BFGS from two starts: L-BFGS with 60
iterations (47 min) or preconditioned with a Gauss-Newton scaling (29 min) reached the optimum from start 1; Adam with 250 steps did so
from start 1 only marginally and not from start 0, and preconditioned Adam did not.

Not verified: the L-BFGS runs from start 0 never finished (killed after about 1 h 48 min); only two starts were diagnosed, with
different budgets, so the optimiser comparison is suggestive only; the first Adam run from start 1 was unconstrained while the later
runs used a box on the log-parameters; seeds 3 and 5 have an indefinite Hessian; timings were taken under varying machine load (load
average 3 to 10, other jobs running); float32 and a real dataset were not tried. The grid is coarse (the spectrum differs from a
twice-finer, tighter-tolerance one by 4e-4 at the true parameters, against a noise of 1e-2).
