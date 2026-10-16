"""Shared schema, constants and pure helper functions.

This module deliberately has no Streamlit dependency so the core logic
can be unit-tested and reused (e.g. by a future API or batch job).

The 25-column layout (A..Y) is identical to the Google Apps Script version
of this project, so the same Google Sheet works with either front end.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd

# ---------------------------------------------------------------------------
# Column layout (order matters: it is the physical column order in the Sheet)
# ---------------------------------------------------------------------------
HEADERS = [
    "Kode Risiko", "Objective/Tujuan", "Potensi Risiko", "Risk Category", "Risk Cause",
    "Deskripsi/Uraian", "Rp (dalam jutaan)",
    "Divisi", "Department", "Unit Kerja", "Eksternal Terkait",
    "Ada/Tidak Ada", "Deskripsi Kontrol",
    "Inherent Likelihood", "Inherent Impact", "Inherent Tingkat Risiko",
    "Opsi Mitigasi", "Deskripsi Mitigasi",
    "Targeted Likelihood", "Targeted Impact", "Targeted Tingkat Risiko",
    "Status", "Next Review Date", "Last Updated", "Updated By",
]

KEYS = [
    "kode", "objective", "potensi", "category", "cause",
    "sev_desc", "sev_rp",
    "divisi", "dept", "unit", "external",
    "control_exists", "control_desc",
    "inh_l", "inh_i", "inh_score",
    "mit_option", "mit_desc",
    "res_l", "res_i", "res_score",
    "status", "review_date", "last_updated", "updated_by",
]

assert len(HEADERS) == len(KEYS) == 25

LABELS = dict(zip(KEYS, HEADERS))
NUMERIC = ["sev_rp", "inh_l", "inh_i", "inh_score", "res_l", "res_i", "res_score"]
LEVEL_COLS = ["inh_l", "inh_i", "res_l", "res_i"]

# ---------------------------------------------------------------------------
# Option lists
# ---------------------------------------------------------------------------
CATEGORIES = ["Market", "Credit", "Liquidity", "Operational", "Compliance", "Strategic", "Other"]
STATUSES = ["Open", "Mitigating", "Monitoring", "Closed"]
MIT_OPTIONS = ["Avoid", "Reduce", "Transfer", "Accept"]
CONTROL_OPTIONS = ["Ada", "Tidak Ada"]

LIKELIHOOD_LABELS = {1: "Rare", 2: "Unlikely", 3: "Moderate", 4: "Likely", 5: "Almost Certain"}
IMPACT_LABELS = {1: "Insignificant", 2: "Minor", 3: "Moderate", 4: "Major", 5: "Significant"}

# ---------------------------------------------------------------------------
# Scoring: Tingkat Risiko = Likelihood x Impact  (5x5 matrix, scores 1..25)
# ---------------------------------------------------------------------------
# Five levels, matching the organisation's "Scoring Tingkat Risiko" table:
#   Very Low 1-3 | Low 4-6 | Medium 8-10 | High 12-16 | Very High 20-25
# Products of two 1..5 numbers can never be 7, 11, 13, 14 or 17-19, so the lowest
# score of each band below (7, 11, 17) only closes those gaps for classification.
SEVERITY_BANDS = [  # (name, lowest score of the band, range shown to users)
    ("Very High", 17, "20-25"),
    ("High", 11, "12-16"),
    ("Medium", 7, "8-10"),
    ("Low", 4, "4-6"),
    ("Very Low", 1, "1-3"),
]
SEVERITY_ORDER = ["Very Low", "Low", "Medium", "High", "Very High"]  # low -> high
SEVERITY_EMOJI = {"Very High": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🟢",
                  "Very Low": "🔵", "Unrated": "⚪"}
# Exact colours sampled from the reference matrix image
SEVERITY_COLOR = {
    "Very Low": "#5B9BD4",
    "Low": "#C5DFB4",
    "Medium": "#FFFF00",
    "High": "#FFC000",
    "Very High": "#FF0000",
}


def score(likelihood: int, impact: int) -> int:
    """Tingkat Risiko = Likelihood x Impact."""
    return int(likelihood) * int(impact)


def severity(value: float | int) -> str:
    """Map a 1..25 score to a severity band name."""
    if value is None or pd.isna(value) or value <= 0:
        return "Unrated"
    for name, low, _display in SEVERITY_BANDS:
        if value >= low:
            return name
    return "Unrated"


def severity_label(value: float | int) -> str:
    """e.g. '🔴 16' - used in tables so severity is visible at a glance."""
    if value is None or pd.isna(value) or value <= 0:
        return "—"
    return f"{SEVERITY_EMOJI[severity(value)]} {int(value)}"


# ---------------------------------------------------------------------------
# Cleaning / normalisation
# ---------------------------------------------------------------------------
def _clean_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return str(value).strip()


def to_iso_date(value) -> str:
    """Return 'YYYY-MM-DD' or ''. Accepts ISO strings, date objects and
    Google Sheets serial numbers (days since 1899-12-30)."""
    if value is None:
        return ""
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = _clean_text(value)
    if not text:
        return ""
    try:
        serial = float(text)
        if serial > 20000:  # a plausible Sheets/Excel serial date
            return (date(1899, 12, 30) + timedelta(days=int(serial))).isoformat()
    except ValueError:
        pass
    return text[:10]


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Return a clean DataFrame with exactly KEYS as columns, proper dtypes,
    recomputed scores, and blank rows removed."""
    out = df.reindex(columns=KEYS).copy()
    for col in KEYS:
        if col in NUMERIC:
            out[col] = pd.to_numeric(out[col], errors="coerce")
        else:
            out[col] = out[col].apply(_clean_text)
    out["review_date"] = out["review_date"].apply(to_iso_date)
    out["last_updated"] = out["last_updated"].apply(to_iso_date)
    for col in LEVEL_COLS:
        out[col] = out[col].fillna(0).astype(int)
    # Always recompute scores so they can never drift from likelihood x impact
    out["inh_score"] = out["inh_l"] * out["inh_i"]
    out["res_score"] = out["res_l"] * out["res_i"]
    out = out[out["kode"] != ""].reset_index(drop=True)
    return out


def next_kode(df: pd.DataFrame, prefix: str = "RSK") -> str:
    """Suggest the next sequential risk code, e.g. RSK-009."""
    highest = 0
    for code in df["kode"].astype(str) if len(df) else []:
        digits = "".join(ch for ch in code if ch.isdigit())
        if digits:
            highest = max(highest, int(digits))
    return f"{prefix}-{highest + 1:03d}"


def overdue_mask(df: pd.DataFrame, today: date | None = None) -> pd.Series:
    """True where a review date has passed and the risk is not Closed."""
    today_str = (today or date.today()).isoformat()
    has_date = df["review_date"] != ""
    return has_date & (df["review_date"] < today_str) & (df["status"] != "Closed")


def risk_to_record(risk: dict) -> dict:
    """Prepare a risk dict for persistence: fixed key set, no NaN."""
    record = {}
    for key in KEYS:
        value = risk.get(key, "")
        if value is None or (isinstance(value, float) and pd.isna(value)):
            value = ""
        record[key] = value
    record["inh_score"] = score(record["inh_l"] or 0, record["inh_i"] or 0)
    record["res_score"] = score(record["res_l"] or 0, record["res_i"] or 0)
    return record


# ---------------------------------------------------------------------------
# UI helpers (pure pandas - tested without Streamlit)
# ---------------------------------------------------------------------------
SEVERITY_ID = {"Very High": "Sangat tinggi", "High": "Tinggi", "Medium": "Sedang",
               "Low": "Rendah", "Very Low": "Sangat rendah", "Unrated": "Belum dinilai"}

COMPACT_KEYS = ["kode", "potensi", "category", "divisi", "inh_score", "res_score",
                "status", "review_date"]
COMPACT_LABELS = {
    "kode": "Kode", "potensi": "Potensi Risiko", "category": "Kategori", "divisi": "Divisi",
    "inh_score": "Level Inherent", "res_score": "Level Target", "status": "Status",
    "review_date": "Review berikutnya",
}


def heatmap_cells(df: pd.DataFrame, mode: str = "targeted") -> dict:
    """Map (likelihood, impact) -> list of risk codes in that heat-map cell."""
    l_col, i_col = ("res_l", "res_i") if mode == "targeted" else ("inh_l", "inh_i")
    cells = {}
    for like in range(1, 6):
        for impact in range(1, 6):
            sub = df[(df[l_col] == like) & (df[i_col] == impact)]
            cells[(like, impact)] = list(sub["kode"])
    return cells


def display_frame(df: pd.DataFrame, view: str = "compact") -> pd.DataFrame:
    """Table shown to users. 'compact' = 8 key columns, 'full' = all template columns."""
    compact = view == "compact"
    keys = COMPACT_KEYS if compact else KEYS
    labels = COMPACT_LABELS if compact else LABELS
    out = df[keys].copy()
    for col in ("inh_score", "res_score"):
        if col in out:
            out[col] = out[col].apply(severity_label)
    if "review_date" in out:
        overdue = overdue_mask(df)
        out["review_date"] = [
            (d + "  ⚠️ terlambat") if o else (d or "—")
            for d, o in zip(out["review_date"], overdue)
        ]
    if "sev_rp" in out:
        out["sev_rp"] = out["sev_rp"].apply(lambda v: "—" if pd.isna(v) else f"{v:,.0f}")
    return out.rename(columns=labels)


# ---------------------------------------------------------------------------
# Heat map helpers: risk-tolerance line and cell text (pure, tested)
# ---------------------------------------------------------------------------
# Scores at or above this value are above the risk tolerance line (Medium and higher).
# Read from the reference matrix; change it here if the company's tolerance differs.
TOLERANCE_MIN_SCORE = 8
TOLERANCE_COLOR = "#FF2500"  # dashed-line colour sampled from the reference matrix


def _chain_segments(segments) -> list[list[tuple[float, float]]]:
    """Join unit segments into polylines (deterministic order)."""
    adjacency: dict = {}
    for a, b in sorted(segments):
        adjacency.setdefault(a, []).append(b)
        adjacency.setdefault(b, []).append(a)
    visited: set = set()
    lines = []
    starts = sorted(p for p, nb in adjacency.items() if len(nb) == 1) + sorted(adjacency)
    for start in starts:
        path, current = [start], start
        while True:
            nxt = [q for q in adjacency[current] if frozenset((current, q)) not in visited]
            if not nxt:
                break
            visited.add(frozenset((current, nxt[0])))
            path.append(nxt[0])
            current = nxt[0]
        if len(path) > 1:
            lines.append(path)
    return lines


def _drop_collinear(path):
    out = [path[0]]
    for prev, cur, nxt in zip(path, path[1:], path[2:]):
        same_x = prev[0] == cur[0] == nxt[0]
        same_y = prev[1] == cur[1] == nxt[1]
        if not (same_x or same_y):
            out.append(cur)
    out.append(path[-1])
    return out


def tolerance_boundary(min_score: int = TOLERANCE_MIN_SCORE) -> list[list[tuple[float, float]]]:
    """Polyline(s) in heat-map coordinates (x = impact, y = likelihood) that separate
    cells below the tolerance from cells at or above it."""
    def above(like: int, impact: int) -> bool:
        return score(like, impact) >= min_score

    segments = set()
    for like in range(1, 6):
        for impact in range(1, 6):
            if impact < 5 and above(like, impact) != above(like, impact + 1):
                segments.add(((impact + 0.5, like - 0.5), (impact + 0.5, like + 0.5)))
            if like < 5 and above(like, impact) != above(like + 1, impact):
                segments.add(((impact - 0.5, like + 0.5), (impact + 0.5, like + 0.5)))
    return [_drop_collinear(p) for p in _chain_segments(segments)]


def heatmap_cell_lines(codes: list[str], limit: int = 4, more_text: str = "more") -> list[str]:
    """Text inside a heat-map cell: up to `limit` risk codes, then the word 'more'."""
    if len(codes) <= limit:
        return list(codes)
    return list(codes[:limit]) + [more_text]


def hover_code_lines(codes: list[str], per_line: int = 3) -> list[str]:
    """ALL codes of a cell, grouped per line so the tooltip stays compact."""
    return [", ".join(codes[i:i + per_line]) for i in range(0, len(codes), per_line)]
