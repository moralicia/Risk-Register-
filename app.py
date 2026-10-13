"""Market Risk Register - Streamlit app.

Run locally:   streamlit run app.py
Demo mode:     works out of the box with fictional sample data (local CSV).
Shared mode:   add Google Sheets credentials to .streamlit/secrets.toml
               (see secrets.toml.example) to store data in a Google Sheet.
"""
from __future__ import annotations

import hmac
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import schema as S
from sample_data import sample_risks
from storage import CSVStorage, GoogleSheetsStorage

st.set_page_config(page_title="Market Risk Register", page_icon="📋", layout="wide")


# ---------------------------------------------------------------------------
# Config / secrets helpers
# ---------------------------------------------------------------------------
def secret(section: str, key: str, default=None):
    """Read st.secrets[section][key] without crashing when secrets are absent."""
    try:
        return st.secrets[section][key]
    except Exception:
        return default


@st.cache_resource(show_spinner=False)
def get_storage():
    """Return (storage, mode). Uses Google Sheets when configured, else local demo CSV."""
    url = secret("gsheets", "spreadsheet_url")
    try:
        service_account = dict(st.secrets["gcp_service_account"])
    except Exception:
        service_account = None
    if url and service_account:
        worksheet = secret("gsheets", "worksheet", "Risks")
        return GoogleSheetsStorage(url, worksheet, service_account), "sheets"
    return CSVStorage("data/risks.csv", seed=sample_risks()), "demo"


@st.cache_data(ttl=20, show_spinner="Loading risks...")
def load_df(_storage) -> pd.DataFrame:
    return _storage.load()


def refresh_data():
    load_df.clear()


# ---------------------------------------------------------------------------
# Authentication (optional): viewer vs editor passwords from secrets
# ---------------------------------------------------------------------------
def login_gate() -> str:
    """Return the role: 'editor' or 'viewer'. Open (editor) if no passwords set."""
    viewer_pw = secret("auth", "viewer_password")
    editor_pw = secret("auth", "editor_password")
    if not viewer_pw and not editor_pw:
        return "editor"
    if st.session_state.get("role"):
        return st.session_state["role"]

    st.title("📋 Market Risk Register")
    st.caption("Please sign in to continue.")
    password = st.text_input("Password", type="password")
    if st.button("Sign in", type="primary"):
        if editor_pw and hmac.compare_digest(password, str(editor_pw)):
            st.session_state["role"] = "editor"
            st.rerun()
        elif viewer_pw and hmac.compare_digest(password, str(viewer_pw)):
            st.session_state["role"] = "viewer"
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
def build_heatmap(df: pd.DataFrame, mode: str) -> go.Figure:
    l_col, i_col = ("res_l", "res_i") if mode == "Targeted (residual)" else ("inh_l", "inh_i")
    levels = [1, 2, 3, 4, 5]
    z, texts, hovers = [], [], []
    for impact in levels:
        z_row, t_row, h_row = [], [], []
        for like in levels:
            value = S.score(like, impact)
            cell = df[(df[l_col] == like) & (df[i_col] == impact)]
            codes = list(cell["kode"])
            z_row.append(value)
            t_row.append(str(len(codes)) if codes else "")
            hover = f"Likelihood {like} x Impact {impact} = {value} ({S.severity(value)})"
            if codes:
                hover += "<br>" + "<br>".join(codes[:8]) + ("<br>..." if len(codes) > 8 else "")
            h_row.append(hover)
        z.append(z_row)
        texts.append(t_row)
        hovers.append(h_row)

    # Stepwise colour scale so each severity band is a flat colour
    c = S.SEVERITY_COLOR
    scale = [
        [0.00, c["Low"]], [0.16, c["Low"]],
        [0.16, c["Medium"]], [0.36, c["Medium"]],
        [0.36, c["High"]], [0.56, c["High"]],
        [0.56, c["Critical"]], [1.00, c["Critical"]],
    ]
    fig = go.Figure(go.Heatmap(
        z=z, x=levels, y=levels, text=texts, texttemplate="%{text}",
        textfont=dict(size=18, color="#1f2937"), hovertext=hovers, hoverinfo="text",
        colorscale=scale, zmin=0.5, zmax=25.5, showscale=False, xgap=4, ygap=4,
    ))
    fig.update_layout(
        height=360, margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(title="Likelihood", tickmode="array", tickvals=levels, fixedrange=True),
        yaxis=dict(title="Impact", tickmode="array", tickvals=levels, fixedrange=True),
    )
    return fig


# ---------------------------------------------------------------------------
# Table display
# ---------------------------------------------------------------------------
def build_display_table(df: pd.DataFrame) -> pd.DataFrame:
    out = df[S.KEYS].copy()
    out["inh_score"] = out["inh_score"].apply(S.severity_label)
    out["res_score"] = out["res_score"].apply(S.severity_label)
    overdue = S.overdue_mask(df)
    out["review_date"] = [
        (d + "  ⚠️ overdue") if o else (d or "—") for d, o in zip(out["review_date"], overdue)
    ]
    out["sev_rp"] = out["sev_rp"].apply(lambda v: "—" if pd.isna(v) else f"{v:,.0f}")
    return out.rename(columns=S.LABELS)


# ---------------------------------------------------------------------------
# Add / edit dialog
# ---------------------------------------------------------------------------
def _level_select(label: str, key: str, default: int, labels: dict[int, str]) -> int:
    return st.selectbox(
        label, options=[1, 2, 3, 4, 5], index=max(1, min(5, int(default or 3))) - 1,
        format_func=lambda v: f"{v} - {labels[v]}", key=key,
    )


def _parse_date(text: str):
    try:
        return date.fromisoformat(text) if text else None
    except ValueError:
        return None


@st.dialog("Risk details", width="large")
def risk_dialog(storage, df: pd.DataFrame, record: dict | None, user_name: str):
    is_edit = record is not None
    r = record or {}
    kp = r.get("kode", "new")  # key prefix keeps widget state separate per risk

    def text(label, field, area=False, placeholder=""):
        widget = st.text_area if area else st.text_input
        return widget(label, value=str(r.get(field, "") or ""), key=f"{kp}_{field}",
                      placeholder=placeholder)

    t1, t2, t3, t4, t5 = st.tabs(
        ["Identifikasi", "Severity & Owner", "Control & Inherent", "Mitigasi & Targeted", "Tracking"]
    )

    with t1:
        if is_edit:
            kode = st.text_input("Kode Risiko", value=r["kode"], disabled=True, key=f"{kp}_kode")
        else:
            kode = st.text_input("Kode Risiko", value="", key=f"{kp}_kode",
                                 placeholder=f"Leave blank to auto-generate ({S.next_kode(df)})")
        objective = text("Objective / Tujuan", "objective", area=True)
        potensi = text("Potensi Risiko", "potensi", area=True)
        categories = list(S.CATEGORIES)
        current_cat = r.get("category") or "Market"
        if current_cat not in categories:
            categories.append(current_cat)
        category = st.selectbox("Risk Category / Kategori Risiko", categories,
                                index=categories.index(current_cat), key=f"{kp}_category")
        cause = text("Risk Cause / Penyebab Risiko", "cause")

    with t2:
        st.markdown("**Severity / Dampak / Potensi Kerugian**")
        sev_desc = text("Deskripsi / Uraian", "sev_desc", area=True)
        sev_rp_raw = r.get("sev_rp")
        sev_rp = st.number_input(
            "Rp (dalam jutaan)", min_value=0.0, step=100.0, key=f"{kp}_sev_rp",
            value=0.0 if sev_rp_raw is None or pd.isna(sev_rp_raw) else float(sev_rp_raw),
        )
        st.markdown("**Risk Owner / Satuan**")
        c1, c2, c3 = st.columns(3)
        with c1:
            divisi = text("Divisi", "divisi")
        with c2:
            dept = text("Department", "dept")
        with c3:
            unit = text("Unit Kerja", "unit")
        external = text("(Divisi/Dept/Unit Kerja) Eksternal Terkait", "external")

    with t3:
        st.markdown("**Existing Control / Pengendalian yang ada**")
        ctrl_default = r.get("control_exists") or "Ada"
        control_exists = st.selectbox("Ada / Tidak Ada", S.CONTROL_OPTIONS,
                                      index=S.CONTROL_OPTIONS.index(ctrl_default)
                                      if ctrl_default in S.CONTROL_OPTIONS else 0,
                                      key=f"{kp}_control_exists")
        control_desc = text("Deskripsi Kontrol", "control_desc", area=True)
        st.markdown("**Analisis Risiko - Inherent**")
        c1, c2 = st.columns(2)
        with c1:
            inh_l = _level_select("Likelihood", f"{kp}_inh_l", r.get("inh_l") or 3, S.LIKELIHOOD_LABELS)
        with c2:
            inh_i = _level_select("Impact", f"{kp}_inh_i", r.get("inh_i") or 3, S.IMPACT_LABELS)
        inh_score = S.score(inh_l, inh_i)
        st.info(f"Tingkat Risiko (Inherent) = {inh_l} x {inh_i} = **{inh_score}** "
                f"({S.SEVERITY_EMOJI[S.severity(inh_score)]} {S.severity(inh_score)})")

    with t4:
        st.markdown("**Rencana Perlakuan / Mitigasi Risiko**")
        mit_default = r.get("mit_option") or "Reduce"
        mit_option = st.selectbox("Opsi Perlakuan / Mitigasi", S.MIT_OPTIONS,
                                  index=S.MIT_OPTIONS.index(mit_default)
                                  if mit_default in S.MIT_OPTIONS else 1,
                                  key=f"{kp}_mit_option")
        mit_desc = text("Deskripsi Perlakuan / Mitigasi", "mit_desc", area=True)
        st.markdown("**Targeted Risk (residual)**")
        c1, c2 = st.columns(2)
        with c1:
            res_l = _level_select("Likelihood", f"{kp}_res_l", r.get("res_l") or 2, S.LIKELIHOOD_LABELS)
        with c2:
            res_i = _level_select("Impact", f"{kp}_res_i", r.get("res_i") or 2, S.IMPACT_LABELS)
        res_score = S.score(res_l, res_i)
        st.info(f"Tingkat Risiko (Targeted) = {res_l} x {res_i} = **{res_score}** "
                f"({S.SEVERITY_EMOJI[S.severity(res_score)]} {S.severity(res_score)})")

    with t5:
        status_default = r.get("status") or "Open"
        status = st.selectbox("Status", S.STATUSES,
                              index=S.STATUSES.index(status_default)
                              if status_default in S.STATUSES else 0, key=f"{kp}_status")
        review_date = st.date_input("Next review date", value=_parse_date(r.get("review_date", "")),
                                    key=f"{kp}_review_date")

    st.divider()
    left, right = st.columns([1, 1])
    with left:
        save = st.button("Save risk", type="primary", key=f"{kp}_save")
    with right:
        if is_edit:
            confirm = st.checkbox("Confirm delete", key=f"{kp}_confirm_delete")
            if st.button("Delete risk", disabled=not confirm, key=f"{kp}_delete"):
                try:
                    storage.delete(r["kode"])
                except Exception as exc:  # noqa: BLE001 - show any backend error to the user
                    st.error(f"Could not delete: {exc}")
                else:
                    refresh_data()
                    st.rerun()

    if save:
        if not user_name.strip():
            st.error("Please enter your name in the sidebar first (used for the audit trail).")
            return
        if not (potensi.strip() or objective.strip()):
            st.error("Please fill in at least 'Objective / Tujuan' or 'Potensi Risiko'.")
            return
        final_kode = (r["kode"] if is_edit else kode.strip()) or S.next_kode(df)
        if not is_edit and storage.exists(final_kode):
            st.error(f"Kode Risiko {final_kode} already exists. Choose another or leave blank.")
            return
        record_out = dict(
            kode=final_kode, objective=objective.strip(), potensi=potensi.strip(),
            category=category, cause=cause.strip(), sev_desc=sev_desc.strip(),
            sev_rp=sev_rp if sev_rp else "", divisi=divisi.strip(), dept=dept.strip(),
            unit=unit.strip(), external=external.strip(), control_exists=control_exists,
            control_desc=control_desc.strip(), inh_l=inh_l, inh_i=inh_i,
            mit_option=mit_option, mit_desc=mit_desc.strip(), res_l=res_l, res_i=res_i,
            status=status, review_date=review_date.isoformat() if review_date else "",
            last_updated=date.today().isoformat(), updated_by=user_name.strip(),
        )
        try:
            storage.upsert(record_out)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Could not save: {exc}")
            return
        refresh_data()
        st.rerun()


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
def main():
    role = login_gate()
    storage, mode = get_storage()
    can_edit = role == "editor"

    # ---- sidebar
    with st.sidebar:
        st.header("Risk Register")
        if mode == "demo":
            st.warning("**Demo mode** - fictional sample data stored locally. "
                       "Connect Google Sheets for shared, persistent data.")
        else:
            st.success("Connected to Google Sheets")
            if not (secret("auth", "viewer_password") or secret("auth", "editor_password")):
                st.error("No passwords are configured - anyone with the link can edit. "
                         "Set [auth] passwords in secrets.")
        st.caption(f"Signed in as: **{role}**")
        user_name = ""
        if can_edit:
            user_name = st.text_input("Your name (audit trail)", key="user_name")
        if st.button("Refresh data"):
            refresh_data()
            st.rerun()
        if st.session_state.get("role") and st.button("Sign out"):
            st.session_state.pop("role", None)
            st.rerun()

    df = load_df(storage)

    # ---- header + KPIs
    st.title("📋 Market Risk Register")
    overdue = S.overdue_mask(df)
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total risks", len(df))
    k2.metric("Critical (targeted)", int((df["res_score"] >= 15).sum()))
    k3.metric("High (targeted)", int(df["res_score"].between(10, 14).sum()))
    k4.metric("Overdue reviews", int(overdue.sum()))
    k5.metric("Avg. targeted score", f"{df['res_score'].mean():.1f}" if len(df) else "0.0")

    # ---- heat map + top risks
    left, right = st.columns(2)
    with left:
        st.subheader("Risk heat map")
        mode_choice = st.radio("View", ["Targeted (residual)", "Inherent"],
                               horizontal=True, label_visibility="collapsed")
        st.plotly_chart(build_heatmap(df, mode_choice), key="heatmap")
        st.caption("🟢 Low 1-4 · 🟡 Medium 5-9 · 🟠 High 10-14 · 🔴 Critical 15-25")
    with right:
        st.subheader("Top risks")
        st.caption("Ranked by targeted (residual) risk level")
        top = df.sort_values("res_score", ascending=False).head(6)
        if top.empty:
            st.info("No risks logged yet.")
        for _, row in top.iterrows():
            st.markdown(
                f"{S.severity_label(row['res_score'])} &nbsp; **{row['kode']}** - "
                f"{row['potensi'] or row['objective']}  \n"
                f"<span style='color:gray;font-size:0.85em'>{row['category']} · "
                f"{row['divisi'] or 'Unassigned'} · {row['status']}</span>",
                unsafe_allow_html=True,
            )

    # ---- filters
    st.subheader("Register")
    f1, f2, f3, f4 = st.columns([2, 2, 2, 3])
    categories = sorted(set(df["category"]) - {""})
    sel_cat = f1.multiselect("Category", categories)
    sel_status = f2.multiselect("Status", S.STATUSES)
    sel_sev = f3.multiselect("Severity (targeted)", ["Critical", "High", "Medium", "Low"])
    query = f4.text_input("Search", placeholder="Search code, objective, risk...")

    fdf = df.copy()
    if sel_cat:
        fdf = fdf[fdf["category"].isin(sel_cat)]
    if sel_status:
        fdf = fdf[fdf["status"].isin(sel_status)]
    if sel_sev:
        fdf = fdf[fdf["res_score"].apply(S.severity).isin(sel_sev)]
    if query.strip():
        q = query.strip().lower()
        hay = (fdf["kode"] + " " + fdf["objective"] + " " + fdf["potensi"]).str.lower()
        fdf = fdf[hay.str.contains(q, regex=False)]
    fdf = fdf.sort_values("res_score", ascending=False).reset_index(drop=True)

    # ---- toolbar
    selected_kode = None
    t_add, t_edit, t_export, _ = st.columns([1, 1, 1, 5])

    if fdf.empty:
        st.info("No risks match these filters." if len(df) else "The register is empty.")
        event = None
    else:
        event = st.dataframe(
            build_display_table(fdf), hide_index=True, key="risk_table",
            on_select="rerun", selection_mode="single-row",
        )
        rows = event.selection.rows if event is not None else []
        if rows:
            selected_kode = fdf.iloc[rows[0]]["kode"]
        st.caption("Select a row (checkbox on the left) and click **Edit selected**."
                   if can_edit else "Read-only view.")

    if can_edit:
        if t_add.button("➕ Add risk", type="primary"):
            risk_dialog(storage, df, None, user_name)
        if t_edit.button("✏️ Edit selected", disabled=selected_kode is None):
            record = df[df["kode"] == selected_kode].iloc[0].to_dict()
            risk_dialog(storage, df, record, user_name)

    export_df = df.rename(columns=S.LABELS)
    t_export.download_button(
        "⬇️ Export CSV", data=export_df.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"risk_register_{date.today().isoformat()}.csv", mime="text/csv",
    )


main()
