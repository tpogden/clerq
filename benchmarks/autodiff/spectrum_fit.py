"""Spectrum fit on simulated data: a transmitted-probe spectrum of a Lambda-EIT medium.

A weak, long probe pulse is scanned across the one-photon resonance and the transmitted
energy fraction ``T(Delta_p)`` is recorded, with Gaussian noise. We then

1. fit the physical parameters (coupling Rabi frequency, coupling detuning, optical depth
   and three decay rates) from a displaced start with gradient methods (Adam, L-BFGS, both
   with the autodiff gradient) and with Nelder-Mead, comparing time and basin of attraction;
2. compute the exact Hessian (forward-over-forward; forward-over-reverse does not work, see make_model) at the optimum, the covariance, and
   show which combinations of the parameters the data do not determine;
3. check the gradient against fixed-step central differences (``n_steps`` not commensurate
   with the time grid) and the fitted spectrum against ``PropagationSolver.solve()``.

Convention note (this matters for every Lambda fit): clerq's ``detunings`` are shifts of the
*upper level* of each field's transition in the rotating frame. In the Lambda here
(probe 0-1, coupling 1-2, ``detuning_positive=False`` on the coupling) the level energies are
``E1 = -Delta_p`` and ``E2 = detunings[1]``, so ``detunings[1]`` is the two-photon detuning.
For a coupling field at fixed *laboratory* detuning ``delta_c`` and a probe scanned over
``Delta_p``, pass ``detunings = [Delta_p, delta_c - Delta_p]``. EIT then sits at
``Delta_p = delta_c``.

Run (a few minutes on a laptop CPU)::

    uv run python benchmarks/autodiff/spectrum_fit.py [--quick] [--no-figure]

Results go to ``results/spectrum_fit.json`` and ``results/spectrum_fit.png``.
"""

from __future__ import annotations

import argparse
import copy
import json
import time
from pathlib import Path

import diffrax as dfx
import jax
import numpy as np

jax.config.update("jax_enable_x64", True)

import jax.numpy as jnp  # noqa: E402
import scipy.optimize as sopt  # noqa: E402

from clerq import PropagationSolver  # noqa: E402

RESULTS = Path(__file__).parent / "results"

NAMES = ["Omega_c", "delta_c", "g", "gamma_01", "gamma_21", "gamma_deph"]
# theta = [log Omega_c, delta_c, log g, log gamma_01, log gamma_21, log gamma_deph]
TRUTH = np.array(
    [np.log(1.2), 0.40, np.log(5.0), np.log(0.6), np.log(1.4), np.log(0.05)]
)
SIGMA = 0.01  # noise on the transmission
OMEGA_P = 1e-3  # weak probe, cyclic Rabi frequency (units of the decay rate scale)

# Fixed settings of the model (everything not fitted)
CFG = {
    "system": {
        "num_states": 3,
        "decays": [
            {"rate": 0.6, "channels": [[0, 1]]},  # excited -> ground 0
            {"rate": 1.4, "channels": [[2, 1]]},  # excited -> ground 2
            {"rate": 0.05, "channels": [[2, 2]]},  # ground-state dephasing
        ],
        "fields": [
            {
                "coupled_levels": [[0, 1]],
                "detuning": 0.0,
                "rabi_freq": OMEGA_P,
                "rabi_freq_t_func": "gaussian",
                "rabi_freq_t_args": {"ampl": 1.0, "centre": 0.0, "fwhm": 6.0},
            },
            {
                "coupled_levels": [[1, 2]],
                "detuning": 0.0,
                "detuning_positive": False,
                "rabi_freq": 1.2,
                "rabi_freq_t_func": "square",
                "rabi_freq_t_args": {"ampl": 1.0, "on": -1000.0, "off": 1000.0},
            },
        ],
    },
    "t_min": -15.0,
    "t_max": 60.0,
    "t_steps": 75,
    "z_min": 0.0,
    "z_max": 1.0,
    "z_steps": 20,
    "z_steps_inner": 2,
    "interaction_strengths": [5.0, 5.0],
}


def make_solver(cfg=CFG):
    return PropagationSolver.from_json_str(json.dumps(cfg))


# Fit-grade tolerances: the spectrum differs from the tight-tolerance, 2x finer-grid one by 4e-4,
# against a noise of 1e-2 (checked offline; see the notes in the results summary).
FIT_OPTS = {"rtol": 1e-6, "atol": 1e-9}


def params_of(theta, dp):
    """The ``to_autodiff`` parameter pytree for log-parametrised ``theta`` at probe detuning ``dp``."""
    om_c, dc, g = jnp.exp(theta[0]), theta[1], jnp.exp(theta[2])
    return {
        "rabi_freq": jnp.stack([jnp.asarray(OMEGA_P, theta.dtype), om_c]),
        "detunings": jnp.stack([dp, dc - dp]),  # see the module docstring
        "interaction_strengths": jnp.stack([g, g]),
        "decay_rates": jnp.exp(theta[3:6]),
    }


def make_model(ad, forward=False):
    """``spectrum(theta, dps)``: transmitted energy fraction at each probe detuning.

    ``forward=True`` uses diffrax's ``ForwardMode`` adjoint (private ``_propagate``), the only
    one that can be differentiated twice: ``jax.jacfwd(jax.grad(...))`` through the default
    (recursive-checkpoint) adjoint raises "can't apply forward-mode autodiff (jvp) to a
    custom_vjp function".
    """

    def one(theta, dp):
        if forward:
            f = ad._propagate(params_of(theta, dp), adjoint=dfx.ForwardMode())
        else:
            f = ad.propagate(params_of(theta, dp))
        inten = jnp.sum(jnp.abs(f[0]) ** 2, axis=-1)
        return inten[-1] / inten[0]

    def spectrum(theta, dps):
        return jax.vmap(lambda d: one(theta, d))(dps)

    return spectrum


def cfg_for(theta, dp):
    """The equivalent JSON problem for ``PropagationSolver.solve()``."""
    th = np.asarray(theta)
    c = copy.deepcopy(CFG)
    s = c["system"]
    s["fields"][1]["rabi_freq"] = float(np.exp(th[0]))
    s["fields"][0]["detuning"] = float(dp)
    s["fields"][1]["detuning"] = float(th[1] - dp)
    c["interaction_strengths"] = [float(np.exp(th[2]))] * 2
    for d, r in zip(s["decays"], np.exp(th[3:6]), strict=True):
        d["rate"] = float(r)
    return c


def solve_T(theta, dp):
    ps = PropagationSolver.from_json_str(json.dumps(cfg_for(theta, dp)))
    ps.solve(recalc=True, progress=False)
    f = np.asarray(ps.rabi_freqs_zt)[0]
    inten = (np.abs(f) ** 2).sum(-1)
    return inten[-1] / inten[0]


def tm(fn, repeat=1):
    t = time.perf_counter()
    for _ in range(repeat):
        out = jax.block_until_ready(fn())
    return out, (time.perf_counter() - t) / repeat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--quick", action="store_true", help="fewer starts and steps (smoke test)"
    )
    ap.add_argument("--no-figure", action="store_true")
    ap.add_argument(
        "--reuse",
        action="store_true",
        help="reuse the Adam/L-BFGS/Nelder-Mead fits stored in results/spectrum_fit.json, add the LM fits, then the analysis",
    )
    ap.add_argument("--starts", type=int, default=4)
    ap.add_argument(
        "--seed",
        type=int,
        default=1,
        help="seed of the noise realisation (and the starts)",
    )
    ap.add_argument(
        "--tag", default="", help="suffix of the results files, e.g. _seed2"
    )
    ap.add_argument(
        "--methods",
        default="adam,lbfgs,nelder_mead,lm",
        help="comma-separated subset of the fit methods",
    )
    ap.add_argument(
        "--no-checks",
        action="store_true",
        help="stop after the Hessian analysis (skip the finite-difference and solve() checks)",
    )
    ap.add_argument(
        "--disp", type=float, default=0.5, help="std of the start displacement in theta"
    )
    args = ap.parse_args()
    n_starts = 2 if args.quick else args.starts
    rng = np.random.default_rng(args.seed)
    out: dict = {"names": NAMES, "truth": TRUTH.tolist(), "sigma": SIGMA}

    dps = jnp.linspace(-3.0, 3.0, 5 if args.quick else 11)
    ad = make_solver().to_autodiff(**FIT_OPTS)
    spectrum = make_model(ad)
    spec_j = jax.jit(spectrum)

    # ---- data -------------------------------------------------------------------
    clean = np.asarray(spec_j(jnp.asarray(TRUTH), dps))
    data = clean + SIGMA * rng.standard_normal(clean.shape)
    data_j = jnp.asarray(data)

    def chi2(theta):
        return jnp.sum(((spectrum(theta, dps) - data_j) / SIGMA) ** 2)

    def nll(theta):
        return 0.5 * chi2(theta)

    vg = jax.jit(jax.value_and_grad(nll))
    nll_j = jax.jit(nll)

    # compile + time the building blocks
    _, t_compile = tm(lambda: vg(jnp.asarray(TRUTH)))
    _, t_fwd = tm(lambda: nll_j(jnp.asarray(TRUTH)), repeat=5)
    _, t_vg = tm(lambda: vg(jnp.asarray(TRUTH)), repeat=5)
    out["timing_building_blocks"] = {
        "first_call_value_and_grad_s": t_compile,
        "spectrum_loss_s": t_fwd,
        "value_and_grad_s": t_vg,
        "grad_over_forward": t_vg / t_fwd,
        "n_detunings": int(dps.size),
    }
    print(
        f"spectrum loss {t_fwd:.3f}s, value_and_grad {t_vg:.3f}s ({t_vg / t_fwd:.1f}x), "
        f"first call {t_compile:.1f}s"
    )
    print("chi2 at truth:", float(chi2(jnp.asarray(TRUTH))), "for", dps.size, "points")

    # ---- fits -------------------------------------------------------------------
    import optax

    def run_adam(x0, steps=15 if args.quick else 60, lr=0.12):
        opt = optax.adam(lr)
        x, st = jnp.asarray(x0), opt.init(jnp.asarray(x0))
        for _ in range(steps):
            _, g = vg(x)
            u, st = opt.update(g, st)
            x = optax.apply_updates(x, u)
        return np.asarray(x), steps, steps

    def run_lbfgs(x0, steps=5 if args.quick else 15):
        opt = optax.lbfgs()
        x, st = jnp.asarray(x0), opt.init(jnp.asarray(x0))

        @jax.jit
        def step(x, st):
            v, g = jax.value_and_grad(nll)(x)
            u, st = opt.update(g, st, x, value=v, grad=g, value_fn=nll)
            return optax.apply_updates(x, u), st, v

        nev, last = 0, None
        for nev in range(1, steps + 1):  # noqa: B007
            x, st, v = step(x, st)
            if last is not None and abs(float(last - v)) < 1e-9 * max(1.0, float(v)):
                break
            last = v
        return np.asarray(x), nev, nev

    def run_nm(x0, maxfev=250):
        calls = [0]

        def f(x):
            calls[0] += 1
            return float(nll_j(jnp.asarray(x)))

        r = sopt.minimize(
            f,
            x0,
            method="Nelder-Mead",
            options={"xatol": 1e-5, "fatol": 1e-7, "maxfev": maxfev, "adaptive": True},
        )
        return r.x, calls[0], calls[0]

    spectrum_f = make_model(ad, forward=True)
    res_jac = jax.jit(
        lambda th: (lambda j, v: (v, j))(
            *jax.jacfwd(
                lambda t: (lambda sp: (sp, sp))(spectrum_f(t, dps)), has_aux=True
            )(th)
        )
    )

    def run_lm(x0, iters=40):
        """Levenberg-Marquardt on the residuals with the forward-mode Jacobian."""
        x = jnp.asarray(x0)
        sp, J = res_jac(x)
        r = (sp - data_j) / SIGMA
        c, lam, nev = float(r @ r), 1e-2, 1
        for _ in range(iters):
            Jn = np.asarray(J) / SIGMA
            A = Jn.T @ Jn
            step = np.linalg.solve(
                A + lam * (np.diag(np.diag(A)) + 1e-9 * np.eye(A.shape[0])),
                -Jn.T @ np.asarray(r),
            )
            xn = x + jnp.asarray(np.clip(step, -0.7, 0.7))  # trust region in log-space
            nev += 1
            try:
                spn, Jnew = res_jac(xn)
                rn = (spn - data_j) / SIGMA
                cn = float(rn @ rn)
            except Exception:  # noqa: BLE001 - the solver hit max_steps in a stiff corner: reject the step
                cn = np.inf
            if not np.isfinite(cn):
                cn = np.inf
            if cn < c:
                done = c - cn < 1e-7 * max(c, 1.0)
                x, J, r, c, lam = xn, Jnew, rn, cn, max(lam * 0.3, 1e-9)
                if done:
                    break
            else:
                lam *= 5.0
        return np.asarray(x), nev, nev

    methods = {
        "adam": run_adam,
        "lbfgs": run_lbfgs,
        "nelder_mead": run_nm,
        "lm": run_lm,
    }
    # a warm-up so compile time is not charged to the first start
    run_lbfgs(TRUTH, steps=2)
    starts = TRUTH + args.disp * rng.standard_normal((n_starts, TRUTH.size))
    methods = {m: methods[m] for m in args.methods.split(",")}
    fits = {m: [] for m in methods}
    if args.reuse:
        old = json.loads((RESULTS / f"spectrum_fit{args.tag}.json").read_text())
        starts = np.asarray(old["starts"])
        fits.update({m: old["fits"][m] for m in old["fits"]})
        fits.update({m: [] for m in methods if m not in old["fits"]})
    for i, x0 in enumerate(starts):
        for m, fn in methods.items():
            if args.reuse and m in old["fits"]:
                continue
            if args.quick and m == "nelder_mead":
                fn = lambda x, f=fn: f(x, maxfev=40)  # noqa: E731
            t = time.perf_counter()
            x, nev, _ = fn(x0)
            dt = time.perf_counter() - t
            c = float(chi2(jnp.asarray(x)))
            fits[m].append(
                {"x": x.tolist(), "chi2": c, "time_s": dt, "iters_or_evals": nev}
            )
            print(f"start {i:2d} {m:12s} chi2 {c:9.2f} time {dt:6.1f}s  n={nev}")
    best = min((f for m in fits for f in fits[m]), key=lambda f: f["chi2"])
    x_opt = np.asarray(best["x"])
    chi2_opt = best["chi2"]
    out["starts"] = starts.tolist()
    out["fits"] = fits
    summary = {}
    for m, lst in fits.items():
        ok = [
            f for f in lst if f["chi2"] < chi2_opt + 1.0
        ]  # within 1 chi2 unit of the best
        summary[m] = {
            "success_rate": len(ok) / len(lst),
            "median_time_s_success": float(np.median([f["time_s"] for f in ok]))
            if ok
            else None,
            "median_time_s_all": float(np.median([f["time_s"] for f in lst])),
            "median_n": float(np.median([f["iters_or_evals"] for f in lst])),
        }
    out["fit_summary"] = summary
    out["chi2_opt"] = chi2_opt
    out["chi2_truth"] = float(chi2(jnp.asarray(TRUTH)))
    out["x_opt"] = x_opt.tolist()
    print(json.dumps(summary, indent=1))
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"spectrum_fit{args.tag}.json").write_text(
        json.dumps(out, indent=1)
    )  # checkpoint after the fit stage

    # ---- Hessian, covariance, identifiability ------------------------------------
    def nll_f(theta):
        return 0.5 * jnp.sum(((spectrum_f(theta, dps) - data_j) / SIGMA) ** 2)

    hess = jax.jit(
        jax.jacfwd(jax.jacfwd(nll_f))
    )  # forward-over-forward (see make_model)
    x_j = jnp.asarray(x_opt)
    H, t_h1 = tm(lambda: hess(x_j))
    H, t_h = tm(lambda: hess(x_j), repeat=2)
    H = np.asarray(H)
    jac = jax.jit(jax.jacfwd(lambda th: spectrum_f(th, dps)))
    J = np.asarray(jac(x_j))
    GN = J.T @ J / SIGMA**2  # Gauss-Newton Hessian of nll
    out["timing_hessian_s"] = {
        "first_call": t_h1,
        "steady": t_h,
        "value_and_grad": t_vg,
    }
    print(
        f"Hessian: {t_h:.2f}s steady ({t_h / t_vg:.1f}x a gradient), first call {t_h1:.1f}s"
    )
    print("Hessian symmetric to", np.abs(H - H.T).max() / np.abs(H).max())

    w, V = np.linalg.eigh(0.5 * (H + H.T))
    wg, Vg = np.linalg.eigh(GN)
    out["hessian"] = H.tolist()
    out["gauss_newton"] = GN.tolist()
    out["eigvals"] = w.tolist()
    out["eigvecs"] = V.tolist()
    out["eigvals_gn"] = wg.tolist()
    print("eigenvalues of exact Hessian:", np.array2string(w, precision=3))
    print("eigenvalues of Gauss-Newton: ", np.array2string(wg, precision=3))
    print("softest eigenvector (theta basis):")
    for n, v in zip(NAMES, V[:, 0], strict=True):
        print(f"   {n:11s} {v:+.3f}")
    cov = np.linalg.inv(0.5 * (H + H.T))
    sd = np.sqrt(np.diag(cov))
    out["covariance"] = cov.tolist()
    out["sd_theta"] = sd.tolist()
    # standard errors in the physical (not log) variables by the delta method
    phys = np.array([np.exp(x_opt[0]), x_opt[1], np.exp(x_opt[2]), *np.exp(x_opt[3:6])])
    scale = np.array([phys[0], 1, phys[2], *phys[3:6]])
    out["phys_opt"] = phys.tolist()
    out["phys_sd"] = (sd * scale).tolist()
    for n, p, s_ in zip(NAMES, phys, sd * scale, strict=True):
        print(
            f"   {n:11s} {p:8.4f} +- {s_:.4f}   (truth {dict(zip(NAMES, [np.exp(TRUTH[0]), TRUTH[1], np.exp(TRUTH[2]), *np.exp(TRUTH[3:6])], strict=True))[n]:.4f})"
        )
    # rate sum and difference
    g01, g21 = np.exp(x_opt[3]), np.exp(x_opt[4])
    a = np.array([0, 0, 0, g01, g21, 0.0])  # d(sum)/dtheta
    b = np.array([0, 0, 0, g01, -g21, 0.0])  # d(diff)/dtheta
    out["sum_sd"] = float(np.sqrt(a @ cov @ a))
    out["diff_sd"] = float(np.sqrt(b @ cov @ b))
    print(
        f"gamma_01+gamma_21 = {g01 + g21:.4f} +- {out['sum_sd']:.4f};"
        f"  gamma_01-gamma_21 = {g01 - g21:.4f} +- {out['diff_sd']:.4f}"
    )

    # profile chi2 along the two softest eigenvectors (verifies the quadratic picture)
    out["soft_direction_profile"] = {}
    for k in (0, 1):
        prof = []
        for length in (-3.0, -1.5, 0.0, 1.5, 3.0):  # distance in theta (log) space
            try:
                d = float(chi2(jnp.asarray(x_opt + length * V[:, k]))) - chi2_opt
            except Exception:  # noqa: BLE001 - solver step limit in a stiff corner
                d = float("nan")
            prof.append(
                {
                    "length": length,
                    "dchi2": d,
                    "quadratic_prediction": float(w[k] * length**2),
                }
            )
        out["soft_direction_profile"][str(k)] = prof
        print(
            f"profile along eigenvector {k} (eigenvalue {w[k]:.3g}):",
            [
                (
                    p_["length"],
                    round(p_["dchi2"], 4),
                    round(p_["quadratic_prediction"], 4),
                )
                for p_ in prof
            ],
        )
    # the soft direction of the two decay rates is curved: profile along the curve of constant sum
    S = g01 + g21
    curve = []
    for frac in (0.1, 0.25, 0.5, 0.75, 0.9):
        xs = x_opt.copy()
        xs[3], xs[4] = np.log(frac * S), np.log((1 - frac) * S)
        curve.append(
            {
                "gamma_01": float(frac * S),
                "gamma_21": float((1 - frac) * S),
                "dchi2": float(chi2(jnp.asarray(xs))) - chi2_opt,
            }
        )
    out["constant_sum_profile"] = curve
    print(
        "chi2 - chi2_opt at constant gamma_01 + gamma_21 (no refit):",
        [(round(c["gamma_01"], 3), round(c["dchi2"], 3)) for c in curve],
    )
    for k in (0, 1):
        print(
            f"eigenvector {k}:",
            {n: round(float(v), 3) for n, v in zip(NAMES, V[:, k], strict=True)},
        )

    if args.no_checks:
        out["spectrum"] = {"dps": np.asarray(dps).tolist(), "data": data.tolist()}
        (RESULTS / f"spectrum_fit{args.tag}.json").write_text(json.dumps(out, indent=1))
        return

    # ---- gradient check against fixed-step finite differences ------------------------
    # Fixed-step runs need n_steps well above the adaptive solver's typical count: 53 and 211
    # steps per slice give NaN here (observed, cause not investigated); 997 (prime, so not
    # commensurate with the 75-interval time grid) is finite. A subset of the detunings keeps it cheap.
    n_fd = 997
    sub = dps[::2]
    ad_fd = make_solver().to_autodiff(n_steps=n_fd, **FIT_OPTS)
    spec_fd = make_model(ad_fd)
    spec_fd_f = make_model(ad_fd, forward=True)
    d_sub = data_j[::2]

    def nll_fd(theta):
        return 0.5 * jnp.sum(((spec_fd(theta, sub) - d_sub) / SIGMA) ** 2)

    def nll_fd_f(theta):
        return 0.5 * jnp.sum(((spec_fd_f(theta, sub) - d_sub) / SIGMA) ** 2)

    h = 1e-5
    f_j = jax.jit(nll_fd)
    g_fn = jax.jit(jax.grad(nll_fd))

    def central(fn, x):
        return np.array(
            [
                (float(fn(x.at[i].add(h))) - float(fn(x.at[i].add(-h)))) / (2 * h)
                for i in range(x.size)
            ]
        )

    x_far = x_j + 0.25 * jnp.array([1.0, -1.0, 1.0, -1.0, 1.0, -1.0])
    g_ad_far, g_cd_far = np.asarray(g_fn(x_far)), central(f_j, x_far)
    g_ad_opt, g_cd_opt = np.asarray(g_fn(x_j)), central(f_j, x_j)
    rel = lambda a_, b_: float(np.abs(a_ - b_).max() / np.abs(b_).max())  # noqa: E731
    out["gradient_check"] = {
        "n_steps": n_fd,
        "h": h,
        "n_detunings": int(sub.size),
        "rel_err_max_far_from_optimum": rel(g_ad_far, g_cd_far),
        "abs_err_max_at_optimum": float(np.abs(g_ad_opt - g_cd_opt).max()),
        "grad_scale_far": float(np.abs(g_cd_far).max()),
        "grad_far_ad": g_ad_far.tolist(),
        "grad_far_fd": g_cd_far.tolist(),
    }
    print(
        "gradient AD vs central FD (far from optimum), max rel err:",
        rel(g_ad_far, g_cd_far),
        "| at the optimum, max abs err:",
        out["gradient_check"]["abs_err_max_at_optimum"],
        "(gradient scale far:",
        out["gradient_check"]["grad_scale_far"],
        ")",
    )
    # Hessian check: forward-over-forward against central FD of the reverse-mode gradient
    Hfd = np.array(
        [
            (np.asarray(g_fn(x_j.at[i].add(h))) - np.asarray(g_fn(x_j.at[i].add(-h))))
            / (2 * h)
            for i in range(x_j.size)
        ]
    )
    H_ff = np.asarray(jax.jit(jax.jacfwd(jax.jacfwd(nll_fd_f)))(x_j))
    out["hessian_check_rel_err"] = float(np.abs(H_ff - Hfd).max() / np.abs(H_ff).max())
    print(
        "Hessian (forward-over-forward) vs FD of the reverse-mode gradient, max rel err:",
        out["hessian_check_rel_err"],
    )

    # ---- cross-check against PropagationSolver.solve() ---------------------------------
    idx = np.arange(0, dps.size, 3 if not args.quick else 8)
    t = time.perf_counter()
    T_solve = np.array([solve_T(x_opt, float(dps[i])) for i in idx])
    t_solve = time.perf_counter() - t
    T_ad = np.asarray(spec_j(x_j, dps))[idx]
    out["solve_crosscheck"] = {
        "detunings": np.asarray(dps)[idx].tolist(),
        "T_solve": T_solve.tolist(),
        "T_ad": T_ad.tolist(),
        "max_abs_diff": float(np.abs(T_solve - T_ad).max()),
        "solve_time_s_per_point": t_solve / len(idx),
    }
    print(
        "solve() vs autodiff spectrum at the optimum, max |dT|:",
        out["solve_crosscheck"]["max_abs_diff"],
        f"({t_solve / len(idx):.2f}s per solve())",
    )

    out["spectrum"] = {
        "dps": np.asarray(dps).tolist(),
        "data": data.tolist(),
        "clean": clean.tolist(),
        "fit": np.asarray(spec_j(x_j, dps)).tolist(),
    }
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"spectrum_fit{args.tag}.json").write_text(json.dumps(out, indent=1))

    if not args.no_figure:
        figure(out, fits, x_opt, cov, H)


def figure(out, fits, x_opt, cov, H):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Ellipse

    fig, ax = plt.subplots(2, 3, figsize=(15, 8))
    s = out["spectrum"]
    ax[0, 0].errorbar(s["dps"], s["data"], SIGMA, fmt="k.", label="noisy data")
    ax[0, 0].plot(s["dps"], s["clean"], "C0-", label="truth")
    ax[0, 0].plot(s["dps"], s["fit"], "C3--", label="fit")
    ax[0, 0].set(
        xlabel="probe detuning", ylabel="transmission", title="simulated spectrum"
    )
    ax[0, 0].legend()

    for m, c in zip(fits, ("C0", "C1", "C2", "C3"), strict=True):
        cs = np.array([f["chi2"] for f in fits[m]])
        ax[0, 1].semilogy(np.sort(cs), "o-", c=c, label=m)
    ax[0, 1].set(
        xlabel="start (sorted)", ylabel=r"final $\chi^2$", title="basin of attraction"
    )
    ax[0, 1].legend()

    ax[0, 2].semilogy(np.sort(np.abs(out["eigvals"])), "ko-", label="exact Hessian")
    ax[0, 2].semilogy(np.sort(np.abs(out["eigvals_gn"])), "r^--", label="Gauss-Newton")
    ax[0, 2].set(
        xlabel="eigenvalue index", ylabel="|eigenvalue|", title="Hessian spectrum"
    )
    ax[0, 2].legend()

    def ellipse(a, i, j, color, label):
        if not np.all(np.isfinite(cov)):  # a smoke-test fit that did not converge
            return
        sub = cov[np.ix_([i, j], [i, j])]
        wv, vv = np.linalg.eigh(sub)
        ang = np.degrees(np.arctan2(vv[1, 1], vv[0, 1]))
        k = np.sqrt(2.30)  # 68% joint
        a.add_patch(
            Ellipse(
                (x_opt[i], x_opt[j]),
                2 * k * np.sqrt(wv[1]),
                2 * k * np.sqrt(wv[0]),
                angle=ang,
                fill=False,
                color=color,
                label=label,
            )
        )
        a.plot(*[x_opt[i], x_opt[j]], "k.")
        a.plot(TRUTH[i], TRUTH[j], "r*")
        r = 3 * np.sqrt(np.diag(sub))
        a.set_xlim(x_opt[i] - r[0], x_opt[i] + r[0])
        a.set_ylim(x_opt[j] - r[1], x_opt[j] + r[1])
        a.set(
            xlabel=NAMES[i] + (" (log)" if i in (0, 2, 3, 4, 5) else ""),
            ylabel=NAMES[j] + (" (log)" if j in (0, 2, 3, 4, 5) else ""),
        )

    for a, (i, j) in zip(
        (ax[1, 0], ax[1, 1], ax[1, 2]), ((3, 4), (0, 2), (1, 5)), strict=True
    ):
        ellipse(a, i, j, "C0", "68% region")
        a.set_title("confidence ellipse (red star = truth)")
    fig.tight_layout()
    fig.savefig(RESULTS / "spectrum_fit.png", dpi=120)
    print("wrote", RESULTS / "spectrum_fit.png")


if __name__ == "__main__":
    main()
