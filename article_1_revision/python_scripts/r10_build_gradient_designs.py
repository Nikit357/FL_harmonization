"""
r10_build_gradient_designs.py — the 45 designs of the confounding gradient (plan WP6 6.1).

Definition of λ: plan §3.3 (revision_lib.build_gradient_design). Designs:
- 5 batches (plan §3.2) × λ ∈ {0, 0.1, …, 1} × replicates 1–3, cap 150 → 33 designs of
  405 samples (λ = 0 positive control, λ = 1 negative control);
- the same 11 λ levels × replicate 1 without the cap → 11 designs of 505 samples;
- `L11_single_dx`: all samples of the 11 real single-diagnosis batches (2,068) → 1 design.

Assertions (the script stops on failure): every (batch, diagnosis) cell is feasible;
batch sizes are identical across λ inside each (cap, replicate) series; the measured
bias-corrected Cramér's V (batch × major group) rises strictly with λ in every series.

Outputs (output/wp6/designs/, small, committed to git so that the Mac can copy them into
the pod): one `<design_id>.tsv` per design (sample_id, RNA_BATCH, diagnosis_3class,
cell_target) and the manifest `designs.tsv` (design, λ, replicate, cap, n, V, AMI).

Usage
-----
python r10_build_gradient_designs.py [--dry-run]
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

import revision_lib as rl

DESIGN_DIR = rl.OUTPUT_DIR / "wp6/designs"


def design_series() -> list[tuple[float, int, int | None]]:
    """(λ, replicate, cap) of the 44 gradient designs, in run order."""
    capped = [
        (lam, rep, rl.GRADIENT_CAP)
        for rep in rl.GRADIENT_REPLICATES
        for lam in rl.GRADIENT_LAMBDAS
    ]
    uncapped = [(lam, 1, None) for lam in rl.GRADIENT_LAMBDAS]
    return capped + uncapped


def build_all(ann: pd.DataFrame) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    """Every design and its manifest row, with the plan's assertions."""
    designs: dict[str, pd.DataFrame] = {}
    rows = []
    for lam, replicate, cap in design_series():
        design_id = rl.gradient_design_id(lam, replicate, cap)
        design = rl.build_gradient_design(ann, lam, replicate, cap)
        designs[design_id] = design
        rows.append(
            {
                "design_id": design_id,
                "kind": "gradient",
                "lambda": lam,
                "replicate": replicate,
                "cap": cap if cap is not None else "none",
                **rl.design_confounding(ann, design.index),
                "batch_sizes": ";".join(
                    f"{b}={n}"
                    for b, n in design[rl.BATCH_COL].value_counts().sort_index().items()
                ),
            }
        )
    single = rl.single_diagnosis_batches(ann)
    in_single = ann[ann[rl.BATCH_COL].isin(single)]
    designs[rl.SINGLE_DX_DESIGN_ID] = pd.DataFrame(
        {
            rl.BATCH_COL: in_single[rl.BATCH_COL],
            "diagnosis_3class": rl.major_group(in_single, n_classes=3),
            "cell_target": np.nan,
        },
        index=in_single.index.rename("sample_id"),
    )
    rows.append(
        {
            "design_id": rl.SINGLE_DX_DESIGN_ID,
            "kind": "single_dx_control",
            "lambda": np.nan,
            "replicate": np.nan,
            "cap": "none",
            **rl.design_confounding(ann, in_single.index),
            "batch_sizes": ";".join(single),
        }
    )
    manifest = pd.DataFrame(rows)
    check_manifest(manifest)
    return designs, manifest


def check_manifest(manifest: pd.DataFrame) -> None:
    """Equal batch sizes across λ and strictly rising V in every (cap, replicate) series."""
    gradient = manifest[manifest["kind"] == "gradient"]
    for (cap, replicate), series in gradient.groupby(["cap", "replicate"]):
        series = series.sort_values("lambda")
        assert (
            series["batch_sizes"].nunique() == 1
        ), f"batch sizes vary: {cap} r{replicate}"
        assert series["n_samples"].nunique() == 1, f"n varies: {cap} r{replicate}"
        v = series["cramers_v_major_group"].to_numpy()
        assert (np.diff(v) > 0).all(), f"V not strictly rising: {cap} r{replicate}: {v}"
    assert len(manifest) == 45, f"expected 45 designs, got {len(manifest)}"


def main() -> None:
    """Build, check and (unless --dry-run) write the designs."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    ann = rl.load_s0_annotation()
    designs, manifest = build_all(ann)
    summary = manifest.groupby(["kind", "cap"]).agg(
        n_designs=("design_id", "size"), n_samples=("n_samples", "first")
    )
    print(summary.to_string())
    capped_r1 = manifest[
        (manifest["cap"] == rl.GRADIENT_CAP) & (manifest["replicate"] == 1)
    ]
    print(
        "V (batch × major group), cap 150, replicate 1:",
        capped_r1["cramers_v_major_group"].round(3).tolist(),
    )
    print(f"{len(manifest)} designs; all assertions passed")
    if args.dry_run:
        return
    DESIGN_DIR.mkdir(parents=True, exist_ok=True)
    for design_id, design in designs.items():
        design.to_csv(DESIGN_DIR / f"{design_id}.tsv", sep="\t")
    manifest.to_csv(DESIGN_DIR / "designs.tsv", sep="\t", index=False)
    print(f"wrote {len(designs)} design files + designs.tsv to {DESIGN_DIR}")


if __name__ == "__main__":
    main()
