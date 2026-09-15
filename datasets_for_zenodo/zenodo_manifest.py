"""Declarative manifest of the Zenodo deposit: which S3 keys land in which bundle.

Pure data and pure functions — no I/O. The builder (``build_and_upload.py``) and the
auditor (``verify_bundle.py``) both import this module so they cannot drift apart.

The one input that is *not* hardcoded is which (strategy, imputation, method, post_rm)
combinations actually exist on S3: coverage is uneven (``22_tmm`` ran on 6 strategies,
``33_amdbnorm`` on 14, ``36_explobatch`` on 60), so ``build_bundles()`` takes a live
listing and reports every requested combination that has no output instead of
assuming one is there.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ── The deposited method set ─────────────────────────────────────────────────
# Exactly one Shambhala configuration is deposited: the default Borisov calibration
# pair. Its public name is the one the article's Supplementary File 3 already uses,
# so the deposit and the supplementary share a method vocabulary. Dropping the other
# 17 P/Q variants is also what satisfies rule R3 of the sanitization plan: the internal
# group label survives only inside those variants' run identifiers, so dropping them
# removes it. A rename would resurrect the very rows that are being dropped.
SHAMBHALA_S3 = "shambhala_P0std_Q0std"
SHAMBHALA_PUB = "20_shambhala"

SWEEP_METHODS = ("10_mnn", "16_fsqn_r", "04_sva")
ANCHOR_STRAT = "A_confirmed_bad"
IMPUTATIONS = ("strict", "softimpute", "knn")

STRATEGIES = (
    "S0_no_removal",
    "A_confirmed_bad",
    "B_extended_bad",
    "C_rnaseq_only",
    "D_malignant_only",
    "E1_iterative_r1",
    "E2_iterative_r2",
    "E3_iterative_r3",
    "F_microarray_only",
    "G_affymetrix_only",
    "H_affymetrix_extended",
    "I_rare_batches_removed",
    "J_ff_only",
    "K_ffpe_only",
)

# ── Budget guards ────────────────────────────────────────────────────────────
MAX_BUNDLE_GB = 3.0     # keeps peak build-host disk under ~3.5 GB
MAX_RECORD_GB = 46.0    # hard budget below Zenodo's 50 GB free quota
MAX_FILES = 100         # Zenodo's per-record file cap — the binding constraint
MIN_FREE_GB = 3.0       # refuse to start a bundle that would not fit

# Second-level split, keyed on a name `_split()` has already produced. Zenodo drops a
# TLS connection held open for 25-45 min, and on 2026-09-14 it served 0.3-1.2 MB/s
# instead of the morning's 4.9, so anything above ~1.5 GB exceeded that window and
# could never complete: the 3.16 GB I_part1 failed 8 of 8 attempts while the 0.62 GB
# I_part2 succeeded. Keyed rather than a lower global MAX_BUNDLE_GB, because lowering
# the cap renames bundles that are already uploaded — and would hand the uploaded
# I_..._part2 a different member list under the same name.
RESPLIT_CAP_GB: dict[str, float] = {
    "grid_strict__I_rare_batches_removed_part1.zip": 1.2,
    "grid_strict__S0_no_removal.zip": 1.2,
    "sweep_methods__A_confirmed_bad__softimpute__post0_part1.zip": 1.2,
    "sweep_methods__A_confirmed_bad__knn__post0_part1.zip": 1.2,
}

DECIMALS = 4            # bounds the absolute rounding error at 5e-5
GZIP_SHRINK = 2.97      # measured gz shrink from float64 repr to "%.4f"

# ── Measured reference data (2026-09-13) ─────────────────────────────────────
# Samples per strategy before and after removing the 1,996 proprietary rows. The
# builder asserts every written matrix against the public figure; a mismatch means
# the S3 prepared layer moved and the deposit plan is stale.
EXPECTED_COUNTS: dict[str, tuple[int, int]] = {
    "S0_no_removal": (7174, 5178),
    "A_confirmed_bad": (5444, 4071),
    "B_extended_bad": (5108, 3735),
    "C_rnaseq_only": (2243, 878),
    "D_malignant_only": (6285, 4478),
    "E1_iterative_r1": (5420, 4047),
    "E2_iterative_r2": (5387, 4014),
    "E3_iterative_r3": (5256, 3883),
    "F_microarray_only": (4931, 4300),
    "G_affymetrix_only": (2801, 2178),
    "H_affymetrix_extended": (3727, 3096),
    "I_rare_batches_removed": (6803, 4847),
    "J_ff_only": (3167, 2203),
    "K_ffpe_only": (3000, 2591),
}

# Reference-based harmonizers drop whole batches they cannot map onto the reference,
# so their output is smaller than the strategy it was run on. Measured 2026-09-14 over
# all 1,204 post0 attempts in the metrics table: exactly four fall short, all in
# H_affymetrix_extended, all by the same 118 public samples — three singleton
# Affymetrix batches (GPL20188 68, GPL23541 35, GPL26356 15, every one FF/Unknown)
# that 19_tdm and 20_shambhala both discard. Keyed rather than relaxed into a bound,
# so an accidental over-filter anywhere else still fails the row-count check.
SHORT_POST0_PUBLIC_ROWS: dict[tuple[str, str], int] = {
    ("H_affymetrix_extended", "19_tdm"): 2978,
    ("H_affymetrix_extended", SHAMBHALA_PUB): 2978,
}

EXPECTED_PROP_COHORTS = 15
EXPECTED_PROP_IDS = 1996
EXPECTED_PUBLIC_ROWS = 5178
# Annotation columns *excluding* the sample-ID index. Written out with its index
# the deposited file has 192 columns, which is the figure the public mirror and
# DATA_AVAILABILITY.md quote — the two numbers describe the same table.
EXPECTED_ANN_COLUMNS = 191
EXPECTED_ANN_COLUMNS_WITH_INDEX = 192
EXPECTED_METRIC_ROWS = 2407   # 33 methods; matches Supplementary File 3 run for run

# ── The curated Best-15 ──────────────────────────────────────────────────────
# harmonization-metrics/create_v3_notebook.py:20-34, post_rm=False only.
# Nine of these are `strict` and therefore already inside the complete strict grid;
# the other six get their own bundle. All fifteen are flagged in manifest.csv.
BEST15: tuple[tuple[str, str, str], ...] = (
    ("10_mnn", "strict", "S0_no_removal"),
    ("10_mnn", "strict", "H_affymetrix_extended"),
    ("10_mnn", "strict", "D_malignant_only"),
    ("04_sva", "knn", "C_rnaseq_only"),
    ("04_sva", "softimpute", "C_rnaseq_only"),
    ("16_fsqn_r", "knn", "C_rnaseq_only"),
    ("16_fsqn_r", "softimpute", "C_rnaseq_only"),
    ("16_fsqn_r", "strict", "C_rnaseq_only"),
    ("10_mnn", "strict", "J_ff_only"),
    ("16_fsqn_r", "strict", "J_ff_only"),
    ("04_sva", "knn", "K_ffpe_only"),
    ("04_sva", "strict", "K_ffpe_only"),
    ("04_sva", "softimpute", "K_ffpe_only"),
    ("13_fsmvn", "strict", "S0_no_removal"),
    ("33_amdbnorm", "strict", "S0_no_removal"),
)

# ── The 2026-06-04 decision tree, as run identifiers ─────────────────────────
DECISION_TREE_PICKS: tuple[tuple[str, str, str, str], ...] = (
    ("J_ff_only", "softimpute", "10_mnn", "post0"),
    ("J_ff_only", "softimpute", "16_fsqn_r", "post0"),
    ("K_ffpe_only", "softimpute", "04_sva", "post0"),
    ("K_ffpe_only", "knn", "04_sva", "post0"),
    ("C_rnaseq_only", "softimpute", "04_sva", "post0"),
    ("C_rnaseq_only", "knn", "04_sva", "post0"),
    ("F_microarray_only", "softimpute", "16_fsqn_r", "post0"),
    ("F_microarray_only", "softimpute", "33_amdbnorm", "post1"),
    ("S0_no_removal", "softimpute", "10_mnn", "post1"),
    ("A_confirmed_bad", "softimpute", "10_mnn", "post1"),
)

Key = tuple[str, str, str, str]   # (strategy, imputation, s3_method, post_rm)


@dataclass
class Bundle:
    """One ZIP archive uploaded as a single Zenodo file.

    Attributes
    ----------
    name : str
        The .zip filename as it appears on Zenodo.
    keys : list[Key]
        S3 (strategy, imputation, method, post_rm) tuples for a harmonized bundle.
    prepared : list[str]
        `prepared/` basenames for an imputed-input bundle.
    kind : str
        "harmonized" or "prepared".
    priority : int
        Drop order under MAX_RECORD_GB — the lowest number is dropped first. The
        complete strict grid, best15 and decision_tree carry the highest priority
        and are never dropped.
    est_gb : float
        Projected size after redaction and rounding.
    """

    name: str
    keys: list[Key] = field(default_factory=list)
    prepared: list[str] = field(default_factory=list)
    kind: str = "harmonized"
    priority: int = 0
    est_gb: float = 0.0

    @property
    def n_members(self) -> int:
        return len(self.keys) + len(self.prepared)


def public_method(s3_method: str) -> str:
    """Map an S3 method token to the name used in the deposit and the article."""
    return SHAMBHALA_PUB if s3_method == SHAMBHALA_S3 else s3_method


def s3_method(public: str) -> str:
    """Inverse of :func:`public_method`."""
    return SHAMBHALA_S3 if public == SHAMBHALA_PUB else public


def deposited_methods(index: dict[Key, int]) -> list[str]:
    """Every S3 method token eligible for the deposit, sorted by public name.

    Parameters
    ----------
    index : dict[Key, int]
        Live S3 listing: key tuple -> object size in bytes.

    Returns
    -------
    list[str]
        S3 method tokens: all non-Shambhala methods plus the default Shambhala pair.
    """
    methods = {k[2] for k in index if not k[2].startswith("shambhala")}
    if any(k[2] == SHAMBHALA_S3 for k in index):
        methods.add(SHAMBHALA_S3)
    return sorted(methods, key=public_method)


def public_fraction(strat: str) -> float:
    """Fraction of a strategy's samples that survive the proprietary-row filter."""
    total, public = EXPECTED_COUNTS[strat]
    return public / total


def estimate_gb(keys: list[Key], index: dict[Key, int]) -> float:
    """Project the deposited size of a set of S3 objects.

    Scales each object by its strategy's public sample fraction and by the measured
    gzip shrink from float64 `repr` to "%.4f". Conservative: gzip's window sees more
    repetition in a full file than in the 53-row block the factor was measured on.
    """
    return sum(index[k] * public_fraction(k[0]) for k in keys) / GZIP_SHRINK / 1e9


def member_name(key: Key) -> str:
    """Filename of a harmonized matrix inside its bundle."""
    strat, imp, method, post = key
    return f"{strat}__{imp}__{public_method(method)}__{post}.public.tsv.gz"


def prepared_member_name(basename: str) -> str:
    """Filename of a prepared exp/ann matrix inside its bundle."""
    return basename.replace(".tsv.gz", ".public.tsv.gz")


def _split(name: str, keys: list[Key], index: dict[Key, int],
           cap_gb: float = MAX_BUNDLE_GB) -> list[tuple[str, list[Key]]]:
    """Split one logical bundle into parts no larger than ``cap_gb``.

    Splitting is what keeps peak disk on the build host bounded: a bundle is written
    to disk in full before it is uploaded, so the cap is the real memory of the
    10 GB JupyterHub volume.
    """
    parts: list[list[Key]] = []
    current: list[Key] = []
    running = 0.0
    for key in sorted(keys):
        size = estimate_gb([key], index)
        if current and running + size > cap_gb:
            parts.append(current)
            current, running = [], 0.0
        current.append(key)
        running += size
    if current:
        parts.append(current)
    if len(parts) == 1:
        named = [(name, parts[0])]
    else:
        named = [
            (name.replace(".zip", f"_part{i + 1}.zip"), part)
            for i, part in enumerate(parts)
        ]
    return [out for part_name, part_keys in named
            for out in _resplit(part_name, part_keys, index)]


def _resplit(name: str, keys: list[Key],
             index: dict[Key, int]) -> list[tuple[str, list[Key]]]:
    """Split one already-named part again if RESPLIT_CAP_GB lists it.

    Sub-parts are suffixed `_s1`, `_s2`, … instead of renumbering `_partN`, so every
    name already on the Zenodo draft keeps its exact spelling and `--resume` goes on
    recognising it.
    """
    cap = RESPLIT_CAP_GB.get(name)
    if cap is None:
        return [(name, keys)]
    pieces: list[list[Key]] = []
    current: list[Key] = []
    running = 0.0
    for key in sorted(keys):
        size = estimate_gb([key], index)
        if current and running + size > cap:
            pieces.append(current)
            current, running = [], 0.0
        current.append(key)
        running += size
    if current:
        pieces.append(current)
    if len(pieces) == 1:
        return [(name, pieces[0])]
    return [(name.replace(".zip", f"_s{i + 1}.zip"), piece)
            for i, piece in enumerate(pieces)]


def build_bundles(
    index: dict[Key, int],
    prepared_index: dict[str, int],
) -> tuple[list[Bundle], list[Key]]:
    """Resolve the deposit's bundle layout against a live S3 listing.

    Parameters
    ----------
    index : dict[Key, int]
        Listing of `exp/`: (strategy, imputation, method, post_rm) -> size in bytes.
    prepared_index : dict[str, int]
        Listing of `prepared/`: basename -> size in bytes.

    Returns
    -------
    tuple[list[Bundle], list[Key]]
        The bundles in upload order, and the requested-but-absent keys so the caller
        can report them rather than silently shipping a short list.
    """
    methods = deposited_methods(index)
    missing: list[Key] = []
    bundles: list[Bundle] = []

    def resolve(keys: list[Key]) -> list[Key]:
        present, absent = [], []
        for key in keys:
            (present if key in index else absent).append(key)
        missing.extend(absent)
        return present

    # ── Imputed inputs: one bundle per imputation, exp + ann twins ───────────
    prio_prepared = {"strict": 60, "softimpute": 25, "knn": 20}
    for imp in IMPUTATIONS:
        members = sorted(
            name for name in prepared_index
            if f"__{imp}__" in name and name.endswith(".tsv.gz")
        )
        bundles.append(
            Bundle(
                name=f"prepared_inputs__{imp}.zip",
                prepared=members,
                kind="prepared",
                priority=prio_prepared[imp],
            )
        )

    # ── Tier 1: the complete strict grid, one bundle per strategy ───────────
    tier1: set[Key] = set()
    for strat in STRATEGIES:
        keys = resolve([
            (strat, "strict", method, post)
            for method in methods
            for post in ("post0", "post1")
        ])
        tier1.update(keys)
        for part_name, part_keys in _split(f"grid_strict__{strat}.zip", keys, index):
            bundles.append(Bundle(name=part_name, keys=part_keys, priority=90))

    # ── Tier 2: softimpute / knn marginal slices, deduplicated against Tier 1 ─
    seen: set[Key] = set(tier1)

    def tier2(name: str, keys: list[Key], priority: int) -> None:
        fresh = [k for k in resolve(keys) if k not in seen]
        seen.update(fresh)
        if not fresh:
            return
        for part_name, part_keys in _split(name, fresh, index):
            bundles.append(Bundle(name=part_name, keys=part_keys, priority=priority))

    tier2(
        f"sweep_methods__{ANCHOR_STRAT}__softimpute__post0.zip",
        [(ANCHOR_STRAT, "softimpute", m, "post0") for m in methods],
        priority=30,
    )
    tier2(
        f"sweep_methods__{ANCHOR_STRAT}__knn__post0.zip",
        [(ANCHOR_STRAT, "knn", m, "post0") for m in methods],
        priority=10,
    )
    for method in SWEEP_METHODS:
        tier2(
            f"sweep_strategies__{method}__softimpute__post0.zip",
            [(s, "softimpute", method, "post0") for s in STRATEGIES],
            priority=40,
        )
    tier2(
        "best15_clustermap_approaches.zip",
        [(s, i, m, "post0") for m, i, s in BEST15],
        priority=95,
    )
    tier2(
        "decision_tree_recommended.zip",
        list(DECISION_TREE_PICKS),
        priority=95,
    )

    for bundle in bundles:
        if bundle.kind == "harmonized":
            bundle.est_gb = estimate_gb(bundle.keys, index)
        else:
            bundle.est_gb = sum(
                prepared_index[n] * public_fraction(n.split("__")[0])
                / (GZIP_SHRINK if n.endswith("exp.tsv.gz") else 1.0)
                for n in bundle.prepared
            ) / 1e9

    bundles.sort(key=lambda b: (-b.priority, b.name))
    return bundles, missing


def best15_keys() -> set[Key]:
    """The Best-15 as post0 run identifiers, for flagging rows in manifest.csv."""
    return {(s, i, m, "post0") for m, i, s in BEST15}


def apply_budget(bundles: list[Bundle],
                 standalone_gb: float,
                 n_standalone_files: int,
                 max_record_gb: float = MAX_RECORD_GB,
                 max_files: int = MAX_FILES) -> tuple[list[Bundle], list[Bundle]]:
    """Split the bundle list into what is deposited and what the budget drops.

    A bundle is dropped whole, never truncated, so every deposited slice stays a
    complete, self-describing unit.

    Parameters
    ----------
    bundles : list[Bundle]
        Bundles in priority order, highest first.
    standalone_gb : float
        Projected size of the standalone tables, which are never dropped.
    n_standalone_files : int
        How many top-level files the standalone tables occupy. Zenodo counts these
        against the same 100-file cap as the bundles.
    max_record_gb, max_files : float, int
        The budget guards.

    Returns
    -------
    tuple[list[Bundle], list[Bundle]]
        (kept, dropped), kept in upload order.
    """
    kept: list[Bundle] = []
    running = standalone_gb
    for bundle in bundles:                      # already sorted, highest priority first
        if running + bundle.est_gb > max_record_gb:
            continue
        kept.append(bundle)
        running += bundle.est_gb
    dropped = [b for b in bundles if b not in kept]
    total_files = len(kept) + n_standalone_files
    if total_files > max_files:
        raise ValueError(
            f"{total_files} top-level files ({len(kept)} bundles + "
            f"{n_standalone_files} tables) exceed Zenodo's {max_files}-file cap"
        )
    return kept, dropped
