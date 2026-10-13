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

LIKELIHOOD_LABELS = {1: "Rare", 2: "Unlikely", 3: "Possible", 4: "Likely", 5: "Almost certain"}
IMPACT_LABELS = {1: "Negligible", 2: "Minor", 3: "Moderate", 4: "Major", 5: "Severe"}

# ---------------------------------------------------------------------------
# Scoring: Tingkat Risiko = Likelihood x Impact  (5x5 matrix, scores 1..25)
# ---------------------------------------------------------------------------
SEVERITY_BANDS = [
    ("Critical", 15, 25),
    ("High", 10, 14),
    ("Medium", 5, 9),
    ("Low", 1, 4),
]
SEVERITY_EMOJI = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🟢", "Unrated": "⚪"}
SEVERITY_COLOR = {
    "Low": "#CDEBD5",
    "Medium": "#F7E7A6",
    "High": "#F6C79A",
    "Critical": "#EFA3A3",
}


def score(likelihood: int, impact: int) -> int:
    """Tingkat Risiko = Likelihood x Impact."""
    return int(likelihood) * int(impact)


def severity(value: float | int) -> str:
    """Map a 1..25 score to a severity band name."""
    if value is None or pd.isna(value) or value <= 0:
        return "Unrated"
    for name, low, _high in SEVERITY_BANDS:
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
SEVERITY_ID = {"Critical": "Kritis", "High": "Tinggi", "Medium": "Sedang", "Low": "Rendah",
               "Unrated": "Belum dinilai"}

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
