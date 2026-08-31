"""
Notebook helper: load cross-product results from S3 into cross_results dict.

Import into harmonization_benchmark.ipynb with:
    from load_cross_product_results import load_metrics, load_exp, cross_results

Or paste the load_metrics() / load_exp() calls directly into a notebook cell.
"""
from __future__ import annotations

import io

import boto3
import pandas as pd

from bench_shared import S3_BUCKET, download_exp_from_s3, s3_key_exp, s3_key_metrics

_s3 = boto3.client("s3")

# Global dict populated by load_metrics(); keyed by (strat, imp, method, post_rm).
cross_results: dict[tuple[str, str, str, bool], dict] = {}


def load_metrics() -> pd.DataFrame:
    """
    Download metrics.csv from S3 and populate cross_results with lazy exp placeholders.

    Returns
    -------
    metrics_df
        DataFrame with one row per (strat, imp, method, post_rm) combination.
    """
    obj        = _s3.get_object(Bucket=S3_BUCKET, Key=s3_key_metrics())
    metrics_df = pd.read_csv(io.BytesIO(obj["Body"].read()))

    cross_results.clear()
    for _, row in metrics_df.iterrows():
        key = (row["strat"], row["imp"], row["method"], bool(row["post_rm"]))
        cross_results[key] = {
            "exp":       None,
            "ann":       None,
            "r2_batch":  row["r2_batch"],
            "r2_diag":   row["r2_diag"],
            "harshness": row["harshness"],
            "status":    row["status"],
            "n_samples": row.get("n_samples"),
            "n_genes":   row.get("n_genes"),
        }

    ok_count     = (metrics_df["status"] == "ok").sum()
    fail_count   = (metrics_df["status"] == "failed").sum()
    skip_count   = (metrics_df["status"] == "skipped").sum()
    cached_count = (metrics_df["status"] == "cached").sum()
    print(f"Loaded {len(cross_results)} combinations from S3.")
    print(f"  ok={ok_count}  failed={fail_count}  skipped={skip_count}  cached={cached_count}")

    return metrics_df


def load_exp(strat: str, imp: str, method: str, post_rm: bool) -> pd.DataFrame | None:
    """
    Download and cache expression matrix for one combination.

    Results are cached in cross_results[key]['exp'] — subsequent calls return the
    cached DataFrame without re-downloading.

    Parameters
    ----------
    strat
        Filter strategy name.
    imp
        Imputation method.
    method
        Normalization method key.
    post_rm
        Whether post-normalization outlier removal was applied.

    Returns
    -------
    Expression DataFrame (samples × genes), or None if unavailable.
    """
    key_tuple = (strat, imp, method, post_rm)
    if key_tuple not in cross_results:
        print(f"Key {key_tuple} not in cross_results. Call load_metrics() first.")
        return None
    if cross_results[key_tuple]["exp"] is not None:
        return cross_results[key_tuple]["exp"]
    s3_key = s3_key_exp(strat, imp, method, post_rm)
    try:
        exp = download_exp_from_s3(_s3, s3_key)
        cross_results[key_tuple]["exp"] = exp
        return exp
    except Exception as e:
        print(f"Could not load {s3_key}: {e}")
        return None


def load_top_k(metrics_df: pd.DataFrame, k: int = 15, sort_by: str = "r2_batch") -> pd.DataFrame:
    """
    Load expression matrices for the top-K combinations by sort_by metric.

    Parameters
    ----------
    metrics_df
        DataFrame returned by load_metrics().
    k
        Number of top combinations to load.
    sort_by
        Column to sort by (ascending). Default: 'r2_batch'.

    Returns
    -------
    Subset of metrics_df for the top-K combinations (expressions loaded into cross_results).
    """
    top_k = (
        metrics_df[metrics_df["status"] == "ok"]
        .sort_values(sort_by)
        .head(k)
    )
    for _, row in top_k.iterrows():
        load_exp(row["strat"], row["imp"], row["method"], bool(row["post_rm"]))
    print(f"Top-{k} expression matrices loaded into cross_results.")
    return top_k
