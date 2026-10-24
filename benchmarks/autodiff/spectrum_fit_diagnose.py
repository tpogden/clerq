"""Why did Adam and L-BFGS fail in ``spectrum_fit.py``? Diagnostics on the stored fits.

(A) For every stored final point: chi2, gradient norm and the distance to the LM optimum along
    the Hessian eigenvectors, to tell a real local minimum from an unconverged descent.
(B) Longer / better-conditioned runs from one of the stored starts:
      adam_long   Adam, 250 steps, cosine learning rate 0.1 -> 0.003
      lbfgs_long  L-BFGS, up to 60 iterations, stops at |grad| < 1e-3
      adam_pre    Adam on z with theta = x0 + P z, P from the Gauss-Newton matrix at x0
      lbfgs_pre   L-BFGS on the same z
    The preconditioner is P = V diag(1/sqrt(max(lambda, 1))) V^T for J^T J / sigma^2 = V diag(lambda) V^T:
    directions the data cannot see (lambda < 1) are not amplified.

Needs ``results/spectrum_fit.json`` (seed 1) from ``spectrum_fit.py``. Writes
``results/spectrum_fit_diagnose_start<k>.json``.

    uv run --extra jax python benchmarks/autodiff/spectrum_fit_diagnose.py --start 0
"""

from __future__ import annotations

import argparse
import json
import os
import time

import jax
import numpy as np

jax.config.update("jax_enable_x64", True)

import jax.numpy as jnp  # noqa: E402
import optax  # noqa: E402

import spectrum_fit as sf  # noqa: E402

NAMES = sf.NAMES
TOL = 1.0  # success: chi2 < chi2_opt + TOL


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument(
        "--only", default="", help="comma-separated subset of the runs in (B)"
    )
    args = ap.parse_args()

    stored = json.loads((sf.RESULTS / "spectrum_fit.json").read_text())
    dps = jnp.asarray(stored["spectrum"]["dps"])
    data = jnp.asarray(stored["spectrum"]["data"])
    x_star = np.asarray(stored["x_opt"])
    chi2_opt = stored["chi2_opt"]
    V = np.asarray(stored["eigvecs"])
    lam = np.asarray(stored["eigvals"])

    ad = sf.make_solver().to_autodiff(**sf.FIT_OPTS)
    spec = sf.make_model(ad)
    spec_f = sf.make_model(ad, forward=True)

    # Line searches and Adam overshoot into corners (rates or optical depth e^3 away) where the adaptive
    # solver exceeds max_steps and the call raises; keep the log-parameters in a box around the truth.
    lo, hi = jnp.asarray(sf.TRUTH) - 3.0, jnp.asarray(sf.TRUTH) + 2.0

    def nll(th):
        return 0.5 * jnp.sum(((spec(jnp.clip(th, lo, hi), dps) - data) / sf.SIGMA) ** 2)

    vg = jax.jit(jax.value_and_grad(nll))

    # ---- (A) where did the stored fits stop? -------------------------------------
    report = {"chi2_opt": chi2_opt, "eigvals": lam.tolist(), "A": {}}
    print(
        f"LM optimum chi2 {chi2_opt:.3f}; Hessian eigenvalues {np.array2string(lam, precision=2)}"
    )
    for m, lst in stored["fits"].items():
        rows = []
        for i, f in enumerate(lst):
            x = np.asarray(f["x"])
            v, g = vg(jnp.asarray(x))
            g = np.asarray(g)
            dist = V.T @ (
                x - x_star
            )  # displacement from the optimum along each eigenvector
            rows.append(
                {
                    "start": i,
                    "chi2": 2 * float(v),
                    "grad_norm": float(np.linalg.norm(g)),
                    "grad_along_eigvecs": (V.T @ g).tolist(),
                    "dist_along_eigvecs": dist.tolist(),
                }
            )
            print(
                f"  {m:12s} start {i}: chi2 {2 * float(v):8.2f}  |grad| {np.linalg.norm(g):9.3g}  "
                f"|dtheta|={np.linalg.norm(x - x_star):.2f}  dist along eigvecs {np.array2string(dist, precision=2)}"
            )
        report["A"][m] = rows

    # ---- (B) better-conditioned / longer runs -------------------------------------
    x0 = np.asarray(stored["starts"][args.start])
    jac = jax.jit(jax.jacfwd(lambda t: spec_f(t, dps)))
    Jm = np.asarray(jac(jnp.asarray(x0))) / sf.SIGMA
    w, Vp = np.linalg.eigh(Jm.T @ Jm)
    P = jnp.asarray(Vp @ np.diag(1.0 / np.sqrt(np.maximum(w, 1.0))) @ Vp.T)
    report["gauss_newton_eigs_at_start"] = w.tolist()
    print("Gauss-Newton eigenvalues at the start:", np.array2string(w, precision=2))
    x0j = jnp.asarray(x0)

    def adam(fn_vg, z0, steps, lr0, lr1):
        sched = optax.cosine_decay_schedule(lr0, steps, alpha=lr1 / lr0)
        opt = optax.adam(sched)
        z, st = z0, opt.init(z0)
        trace = []
        for k in range(steps):
            v, g = fn_vg(z)
            u, st = opt.update(g, st)
            z = optax.apply_updates(z, u)
            if k % 10 == 0:
                trace.append((k, 2 * float(v), float(jnp.linalg.norm(g))))
        return z, trace

    def lbfgs(fn, z0, iters, gtol=1e-3):
        opt = optax.lbfgs()
        z, st = z0, opt.init(z0)

        @jax.jit
        def step(z, st):
            v, g = jax.value_and_grad(fn)(z)
            u, st = opt.update(g, st, z, value=v, grad=g, value_fn=fn)
            return optax.apply_updates(z, u), st, v, jnp.linalg.norm(g)

        trace = []
        for k in range(iters):
            z, st, v, gn = step(z, st)
            trace.append((k, 2 * float(v), float(gn)))
            if float(gn) < gtol:
                break
        return z, trace

    nll_z = lambda z: nll(x0j + P @ z)  # noqa: E731
    vg_z = jax.jit(jax.value_and_grad(nll_z))
    z0 = jnp.zeros_like(x0j)

    runs = {
        "adam_long": lambda: (lambda r: (x0j * 0 + r[0], r[1]))(
            adam(vg, x0j, 250, 0.1, 0.003)
        ),
        "lbfgs_long": lambda: lbfgs(nll, x0j, 60),
        "adam_pre": lambda: (lambda r: (x0j + P @ r[0], r[1]))(
            adam(vg_z, z0, 150, 0.1, 0.003)
        ),
        "lbfgs_pre": lambda: (lambda r: (x0j + P @ r[0], r[1]))(lbfgs(nll_z, z0, 40)),
    }
    only = [r for r in args.only.split(",") if r]
    out_path = sf.RESULTS / f"spectrum_fit_diagnose_start{args.start}.json"
    prev = json.loads(out_path.read_text()) if out_path.exists() else {}
    report["B"] = prev.get("B", {})
    for name, fn in runs.items():
        if only and name not in only:
            continue
        t = time.perf_counter()
        x, trace = fn()
        dt = time.perf_counter() - t
        x = np.asarray(x)
        v, g = vg(jnp.asarray(x))
        c, gn = 2 * float(v), float(jnp.linalg.norm(g))
        report["B"][name] = {
            "chi2": c,
            "grad_norm": gn,
            "time_s": dt,
            "n": len(trace),
            "success": c < chi2_opt + TOL,
            "trace": trace,
            "x": x.tolist(),
            "load_avg": os.getloadavg()[0],
        }
        print(
            f"B {name:11s} start {args.start}: chi2 {c:8.3f} |grad| {gn:9.3g} time {dt:6.0f}s  "
            f"success={c < chi2_opt + TOL}  (load {os.getloadavg()[0]:.1f})",
            flush=True,
        )
        (sf.RESULTS / f"spectrum_fit_diagnose_start{args.start}.json").write_text(
            json.dumps(report, indent=1)
        )
    (sf.RESULTS / f"spectrum_fit_diagnose_start{args.start}.json").write_text(
        json.dumps(report, indent=1)
    )


if __name__ == "__main__":
    main()
