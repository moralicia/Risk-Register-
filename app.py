"""Register Risiko Pasar (Market Risk Register) - Streamlit app, v2 layout.

Layout is designed for risk owners who fill in data:
  Tab 1  "Daftar Risiko"  -> action buttons first, then the register table
  Tab 2  "Ringkasan"      -> KPIs, readable heat map and top risks (for management)

Run locally:   streamlit run app.py
Demo mode:     works out of the box with fictional sample data (local CSV).
Shared mode:   add Google Sheets credentials to .streamlit/secrets.toml.
"""
from __future__ import annotations

import hmac
import html
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import schema as S
import teks as T
from sample_data import sample_risks
from storage import CSVStorage, GoogleSheetsStorage, diagnose_secrets

st.set_page_config(page_title=T.APP_TITLE, page_icon=T.APP_ICON, layout="wide",
                   initial_sidebar_state="collapsed")


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
def _demo_storage():
    return CSVStorage("data/risks.csv", seed=sample_risks())


@st.cache_resource(show_spinner=False)
def _connect_sheets(url: str, worksheet: str, _service_account: dict):
    return GoogleSheetsStorage(url, worksheet, _service_account)


def get_storage():
    """Return (storage, mode, error). Uses Google Sheets when configured; otherwise
    falls back to demo mode and reports why (error is '' when simply not configured)."""
    url = secret("gsheets", "spreadsheet_url")
    try:
        service_account = dict(st.secrets["gcp_service_account"])
    except Exception:
        service_account = None
    if url and service_account:
        try:
            worksheet = secret("gsheets", "worksheet", "Risks")
            return _connect_sheets(url, worksheet, service_account), "sheets", ""
        except Exception as exc:  # noqa: BLE001 - surfaced to the user, not hidden
            return _demo_storage(), "demo", f"{type(exc).__name__}: {str(exc)[:300]}"
    return _demo_storage(), "demo", ""


def render_demo_diagnostics(conn_error: str):
    """Explain, without revealing secret values, why the app is in demo mode."""
    if conn_error:
        st.error(f"Secrets terbaca, tetapi gagal terhubung ke Google Sheets: {conn_error}")
    with st.expander("🔍 Mengapa masih mode demo? (diagnostik koneksi)", expanded=not conn_error):
        rep = diagnose_secrets(st.secrets)
        mark = lambda ok: "✅" if ok else "❌"  # noqa: E731
        sections = ", ".join(f"[{s}]" for s in rep["sections"]) or "tidak ada sama sekali"
        st.markdown(
            f"- Bagian yang terdeteksi di Secrets aplikasi **ini**: {sections}\n"
            f"- {mark(rep['auth'])} Bagian `[auth]` (password)\n"
            f"- {mark(rep['url'])} `[gsheets]` berisi `spreadsheet_url`\n"
            f"- {mark(rep['sa_section'])} Bagian `[gcp_service_account]` ada\n"
            f"- {mark(rep['client_email'])} `client_email` terisi\n"
            f"- {mark(rep['private_key_present'])} `private_key` terisi\n"
            f"- {mark(rep['private_key_format'])} `private_key` berformat lengkap (BEGIN ... END PRIVATE KEY)"
        )
        if not rep["sections"]:
            st.warning("Secrets **kosong** pada aplikasi ini. Buka Manage app → Settings → Secrets "
                       "dari aplikasi yang alamatnya sama dengan halaman ini, isi, Save, lalu Reboot app.")
        else:
            st.caption("Perbaiki baris yang bertanda ❌, Save, lalu Reboot app.")


@st.cache_data(ttl=20, show_spinner="Memuat data risiko...")
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

    st.title(f"{T.APP_ICON} {T.APP_TITLE}")
    st.caption(T.LOGIN_CAPTION)
    password = st.text_input(T.LOGIN_PASSWORD_LABEL, type="password")
    if st.button(T.LOGIN_BUTTON, type="primary"):
        if editor_pw and hmac.compare_digest(password, str(editor_pw)):
            st.session_state["role"] = "editor"
            st.rerun()
        elif viewer_pw and hmac.compare_digest(password, str(viewer_pw)):
            st.session_state["role"] = "viewer"
            st.rerun()
        else:
            st.error(T.LOGIN_ERROR)
    st.stop()


# ---------------------------------------------------------------------------
# Heat map: layout and palette follow the organisation's reference matrix.
#   y axis = Likelihood / Kemungkinan (5 at the top), x axis = Impact / Dampak.
#   Cells contain risk codes only (no level names).
# ---------------------------------------------------------------------------
def build_heatmap(df: pd.DataFrame, mode: str) -> go.Figure:
    levels = [1, 2, 3, 4, 5]
    cells = S.heatmap_cells(df, mode)  # (likelihood, impact) -> risk codes
    z, hovers = [], []
    for like in levels:  # rows = likelihood
        z_row, h_row = [], []
        for impact in levels:  # columns = impact
            value = S.score(like, impact)
            level = S.severity(value)
            codes = cells[(like, impact)]
            hover = (f"Likelihood {like} x Impact {impact} = {value} "
                     f"({level} / {S.SEVERITY_ID[level]})")
            if codes:  # ALL risk codes of the cell are listed on hover
                hover += f"<br><b>{len(codes)} risiko:</b><br>" + "<br>".join(S.hover_code_lines(codes))
            z_row.append(S.SEVERITY_ORDER.index(level))  # 0..4 -> one flat colour per level
            h_row.append(hover)
        z.append(z_row)
        hovers.append(h_row)

    colors = [S.SEVERITY_COLOR[name] for name in S.SEVERITY_ORDER]
    scale = []
    for i, colour in enumerate(colors):
        scale += [[i / 5, colour], [(i + 1) / 5, colour]]
    fig = go.Figure(go.Heatmap(
        z=z, x=levels, y=levels, hovertext=hovers, hoverinfo="text",
        colorscale=scale, zmin=-0.5, zmax=4.5, showscale=False, xgap=3, ygap=3,
    ))
    # Dashed risk-tolerance line (staircase between cells below / at-or-above the tolerance)
    for path in S.tolerance_boundary():
        fig.add_trace(go.Scatter(
            x=[p[0] for p in path], y=[p[1] for p in path], mode="lines",
            line=dict(color=S.TOLERANCE_COLOR, width=3, dash="dash"),
            hoverinfo="skip", showlegend=False,
        ))
    fig.add_annotation(x=1.5, y=5.5, text=f"<b>{T.HEATMAP_TOLERANCE_LABEL}</b>", showarrow=False,
                       xanchor="left", yanchor="bottom", yshift=6,
                       font=dict(size=12, color=S.TOLERANCE_COLOR))
    # Risk codes only inside the cells; more than 4 -> first 4 plus the word "more"
    for (like, impact), codes in cells.items():
        if codes:
            fig.add_annotation(x=impact, y=like, showarrow=False, font=dict(size=11, color="#111827"),
                               text="<br>".join(S.heatmap_cell_lines(codes, 4, T.HEATMAP_MORE)))
    fig.update_layout(
        height=520, margin=dict(l=10, r=10, t=44, b=10),
        xaxis=dict(title=dict(text="<b>Impact / Dampak</b>", font=dict(size=15)),
                   tickmode="array", tickvals=levels, range=[0.5, 5.5], fixedrange=True, automargin=True,
                   ticktext=[f"<b>{v}</b><br>{S.IMPACT_LABELS[v]}" for v in levels]),
        yaxis=dict(title=dict(text="<b>Likelihood / Kemungkinan</b>", font=dict(size=15)),
                   tickmode="array", tickvals=levels, range=[0.5, 5.5], fixedrange=True, automargin=True,
                   ticktext=[f"{S.LIKELIHOOD_LABELS[v]}  <b>{v}</b>" for v in levels]),
    )
    return fig


def legend_table_html() -> str:
    """'Scoring Tingkat Risiko' legend, same palette and order as the reference image."""
    ranges = {name: rng for name, _low, rng in S.SEVERITY_BANDS}
    rows = "".join(
        f"<tr><td style='background:{S.SEVERITY_COLOR[name]};color:#111827;padding:5px 14px;"
        f"font-weight:600;border:1px solid #9ca3af'>{name} "
        f"<span style='font-weight:400;font-size:0.8em'>· {S.SEVERITY_ID[name]}</span></td>"
        f"<td style='padding:5px 14px;text-align:center;border:1px solid #9ca3af;"
        f"background:#ffffff;color:#111827'>{ranges[name]}</td></tr>"
        for name in S.SEVERITY_ORDER
    )
    return (
        "<table style='border-collapse:collapse;font-size:0.9em;margin-top:8px'>"
        "<tr><td colspan='2' style='background:#d9d9d9;color:#111827;font-weight:700;"
        "text-align:center;padding:5px 14px;border:1px solid #9ca3af'>SCORING TINGKAT RISIKO</td></tr>"
        f"{rows}</table>"
    )


def risk_card_html(row) -> str:
    color = S.SEVERITY_COLOR[S.severity(row["res_score"])]
    title = html.escape(row["potensi"] or row["objective"] or "-")
    meta = html.escape(f"{row['category']} · {row['divisi'] or 'Tanpa divisi'} · {row['status']}")
    return (
        "<div style='display:flex;gap:12px;align-items:center;padding:8px 0;"
        "border-bottom:1px solid #e5e7eb'>"
        f"<div style='background:{color};color:#1f2937;font-weight:700;border-radius:6px;"
        f"min-width:46px;text-align:center;padding:8px 0'>{int(row['res_score'])}</div>"
        f"<div><div style='font-weight:600'>{html.escape(row['kode'])} — {title}</div>"
        f"<div style='color:#6b7280;font-size:0.85em'>{meta}</div></div></div>"
    )


# ---------------------------------------------------------------------------
# Add / edit dialog (guided, with plain-language help)
# ---------------------------------------------------------------------------
def _level_select(label: str, key: str, default: int, labels: dict[int, str], help_text: str) -> int:
    return st.selectbox(
        label, options=[1, 2, 3, 4, 5], index=max(1, min(5, int(default or 3))) - 1,
        format_func=lambda v: f"{v} - {labels[v]}", key=key, help=help_text,
    )


def _parse_date(text: str):
    try:
        return date.fromisoformat(text) if text else None
    except ValueError:
        return None


@st.dialog("Tambah / ubah risiko", width="large")
def risk_dialog(storage, df: pd.DataFrame, record: dict | None):
    is_edit = record is not None
    r = record or {}
    kp = r.get("kode", "new")  # key prefix keeps widget state separate per risk

    st.caption("Isi lima tab di bawah dari kiri ke kanan. Arahkan kursor ke tanda ❔ untuk penjelasan.")

    name = st.text_input("Nama Anda *", value=st.session_state.get("saved_name", ""),
                         key=f"{kp}_name", help="Dicatat sebagai pengubah data (audit trail).")

    def text(label, field, area=False, help_text=None, placeholder=""):
        widget = st.text_area if area else st.text_input
        return widget(label, value=str(r.get(field, "") or ""), key=f"{kp}_{field}",
                      help=help_text, placeholder=placeholder)

    t1, t2, t3, t4, t5 = st.tabs(
        ["① Identifikasi", "② Dampak & Pemilik", "③ Pengendalian & Penilaian",
         "④ Mitigasi & Target", "⑤ Status"]
    )

    with t1:
        if is_edit:
            kode = st.text_input("Kode Risiko", value=r["kode"], disabled=True, key=f"{kp}_kode")
        else:
            kode = st.text_input("Kode Risiko", value="", key=f"{kp}_kode",
                                 help="Kode unik risiko. Kosongkan agar dibuatkan otomatis.",
                                 placeholder=f"Kosongkan untuk otomatis ({S.next_kode(df)})")
        objective = text("Objective / Tujuan", "objective", area=True,
                         help_text="Sasaran bisnis atau unit yang terancam oleh risiko ini.")
        potensi = text("Potensi Risiko *", "potensi", area=True,
                       help_text="Kejadian yang mungkin terjadi dan merugikan. Tulis singkat, satu kalimat.")
        categories = list(S.CATEGORIES)
        current_cat = r.get("category") or "Market"
        if current_cat not in categories:
            categories.append(current_cat)
        category = st.selectbox("Risk Category / Kategori Risiko", categories,
                                index=categories.index(current_cat), key=f"{kp}_category")
        cause = text("Risk Cause / Penyebab Risiko", "cause",
                     help_text="Akar penyebab yang membuat risiko ini bisa terjadi.")

    with t2:
        st.markdown("**Severity / Dampak / Potensi Kerugian**")
        sev_desc = text("Deskripsi / Uraian", "sev_desc", area=True,
                        help_text="Apa akibatnya jika risiko ini benar-benar terjadi?")
        sev_rp_raw = r.get("sev_rp")
        sev_rp = st.number_input(
            "Rp (dalam jutaan)", min_value=0.0, step=100.0, key=f"{kp}_sev_rp",
            help="Perkiraan kerugian dalam jutaan rupiah. Isi 0 jika belum diketahui.",
            value=0.0 if sev_rp_raw is None or pd.isna(sev_rp_raw) else float(sev_rp_raw),
        )
        st.markdown("**Risk Owner / Satuan**")
        c1, c2, c3 = st.columns(3)
        with c1:
            divisi = text("Divisi", "divisi", help_text="Unit yang bertanggung jawab atas risiko ini.")
        with c2:
            dept = text("Department", "dept")
        with c3:
            unit = text("Unit Kerja", "unit")
        external = text("(Divisi/Dept/Unit Kerja) Eksternal Terkait", "external",
                        help_text="Pihak lain di luar unit Anda yang ikut terlibat, jika ada.")

    with t3:
        with st.expander("📖 Panduan skala penilaian 1-5"):
            st.markdown(
                "| Nilai | Likelihood (kemungkinan) | Impact (dampak) |\n|---|---|---|\n"
                + "\n".join(f"| {v} | {S.LIKELIHOOD_LABELS[v]} | {S.IMPACT_LABELS[v]} |"
                            for v in range(1, 6))
                + "\n\n**Tingkat Risiko = Likelihood x Impact.** "
                  "Very Low 1-3 · Low 4-6 · Medium 8-10 · High 12-16 · Very High 20-25."
            )
        st.markdown("**Existing Control / Pengendalian yang ada**")
        ctrl_default = r.get("control_exists") or "Ada"
        control_exists = st.selectbox(
            "Ada / Tidak Ada", S.CONTROL_OPTIONS,
            index=S.CONTROL_OPTIONS.index(ctrl_default) if ctrl_default in S.CONTROL_OPTIONS else 0,
            key=f"{kp}_control_exists", help="Apakah sudah ada pengendalian yang berjalan saat ini?")
        control_desc = text("Deskripsi Kontrol", "control_desc", area=True,
                            help_text="Pengendalian yang SUDAH berjalan, bukan rencana.")
        st.markdown("**Analisis Risiko - Inherent** (sebelum memperhitungkan pengendalian)")
        c1, c2 = st.columns(2)
        with c1:
            inh_l = _level_select("Likelihood", f"{kp}_inh_l", r.get("inh_l") or 3,
                                  S.LIKELIHOOD_LABELS, "Seberapa mungkin risiko terjadi? 1 = sangat jarang, 5 = hampir pasti.")
        with c2:
            inh_i = _level_select("Impact", f"{kp}_inh_i", r.get("inh_i") or 3,
                                  S.IMPACT_LABELS, "Seberapa parah dampaknya? 1 = dapat diabaikan, 5 = sangat berat.")
        inh_score = S.score(inh_l, inh_i)
        st.info(f"Tingkat Risiko (Inherent) = {inh_l} x {inh_i} = **{inh_score}** "
                f"({S.SEVERITY_EMOJI[S.severity(inh_score)]} {S.SEVERITY_ID[S.severity(inh_score)]})")

    with t4:
        st.markdown("**Rencana Perlakuan / Mitigasi Risiko**")
        mit_default = r.get("mit_option") or "Reduce"
        mit_option = st.selectbox(
            "Opsi Perlakuan / Mitigasi", S.MIT_OPTIONS,
            index=S.MIT_OPTIONS.index(mit_default) if mit_default in S.MIT_OPTIONS else 1,
            key=f"{kp}_mit_option",
            help="Avoid = menghindari · Reduce = mengurangi · Transfer = mengalihkan (mis. asuransi) · Accept = menerima.")
        mit_desc = text("Deskripsi Perlakuan / Mitigasi", "mit_desc", area=True,
                        help_text="Langkah konkret yang akan dilakukan untuk menurunkan risiko.")
        st.markdown("**Targeted Risk** (target penilaian setelah mitigasi dijalankan)")
        c1, c2 = st.columns(2)
        with c1:
            res_l = _level_select("Likelihood", f"{kp}_res_l", r.get("res_l") or 2,
                                  S.LIKELIHOOD_LABELS, "Target kemungkinan setelah mitigasi.")
        with c2:
            res_i = _level_select("Impact", f"{kp}_res_i", r.get("res_i") or 2,
                                  S.IMPACT_LABELS, "Target dampak setelah mitigasi.")
        res_score = S.score(res_l, res_i)
        st.info(f"Tingkat Risiko (Targeted) = {res_l} x {res_i} = **{res_score}** "
                f"({S.SEVERITY_EMOJI[S.severity(res_score)]} {S.SEVERITY_ID[S.severity(res_score)]})")

    with t5:
        status_default = r.get("status") or "Open"
        status = st.selectbox(
            "Status", S.STATUSES,
            index=S.STATUSES.index(status_default) if status_default in S.STATUSES else 0,
            key=f"{kp}_status",
            help="Open = baru dicatat · Mitigating = mitigasi berjalan · Monitoring = dipantau · Closed = selesai.")
        review_date = st.date_input("Tanggal review berikutnya",
                                    value=_parse_date(r.get("review_date", "")),
                                    key=f"{kp}_review_date")

    st.divider()
    left, right = st.columns(2)
    with left:
        save = st.button("💾 Simpan risiko", type="primary", key=f"{kp}_save")
    with right:
        if is_edit:
            confirm = st.checkbox("Ya, saya yakin ingin menghapus", key=f"{kp}_confirm_delete")
            if st.button("🗑️ Hapus risiko", disabled=not confirm, key=f"{kp}_delete"):
                try:
                    storage.delete(r["kode"])
                except Exception as exc:  # noqa: BLE001 - show backend error to the user
                    st.error(f"Gagal menghapus: {exc}")
                else:
                    refresh_data()
                    st.session_state["flash"] = f"Risiko {r['kode']} dihapus."
                    st.rerun()

    if save:
        if not name.strip():
            st.error("Isi 'Nama Anda' di bagian atas formulir terlebih dahulu.")
            return
        if not (potensi.strip() or objective.strip()):
            st.error("Isi minimal 'Potensi Risiko' (tab ①).")
            return
        final_kode = (r["kode"] if is_edit else kode.strip()) or S.next_kode(df)
        if not is_edit and storage.exists(final_kode):
            st.error(f"Kode Risiko {final_kode} sudah dipakai. Gunakan kode lain atau kosongkan.")
            return
        record_out = dict(
            kode=final_kode, objective=objective.strip(), potensi=potensi.strip(),
            category=category, cause=cause.strip(), sev_desc=sev_desc.strip(),
            sev_rp=sev_rp if sev_rp else "", divisi=divisi.strip(), dept=dept.strip(),
            unit=unit.strip(), external=external.strip(), control_exists=control_exists,
            control_desc=control_desc.strip(), inh_l=inh_l, inh_i=inh_i,
            mit_option=mit_option, mit_desc=mit_desc.strip(), res_l=res_l, res_i=res_i,
            status=status, review_date=review_date.isoformat() if review_date else "",
            last_updated=date.today().isoformat(), updated_by=name.strip(),
        )
        try:
            storage.upsert(record_out)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Gagal menyimpan: {exc}")
            return
        st.session_state["saved_name"] = name.strip()
        st.session_state["flash"] = f"Risiko {final_kode} berhasil disimpan."
        refresh_data()
        st.rerun()


# ---------------------------------------------------------------------------
# Tab 1: register (for risk owners)
# ---------------------------------------------------------------------------
def render_register(df: pd.DataFrame, storage, can_edit: bool):
    if can_edit:
        st.markdown(T.HOWTO_EDITOR)
    else:
        st.info(T.HOWTO_VIEWER)

    c_add, c_edit, c_view, c_exp = st.columns([2, 2, 3, 2])

    query = st.text_input("Cari", placeholder=T.SEARCH_PLACEHOLDER,
                          label_visibility="collapsed")
    with st.expander(T.FILTER_EXPANDER):
        f1, f2, f3, f4 = st.columns(4)
        sel_div = f1.multiselect("Divisi", sorted(set(df["divisi"]) - {""}))
        sel_cat = f2.multiselect("Kategori", sorted(set(df["category"]) - {""}))
        sel_status = f3.multiselect("Status", S.STATUSES)
        sel_sev = f4.multiselect("Level target", list(reversed(S.SEVERITY_ORDER)),
                                 format_func=lambda v: S.SEVERITY_ID[v])

    fdf = df.copy()
    if sel_div:
        fdf = fdf[fdf["divisi"].isin(sel_div)]
    if sel_cat:
        fdf = fdf[fdf["category"].isin(sel_cat)]
    if sel_status:
        fdf = fdf[fdf["status"].isin(sel_status)]
    if sel_sev:
        fdf = fdf[fdf["res_score"].apply(S.severity).isin(sel_sev)]
    if query.strip():
        hay = (fdf["kode"] + " " + fdf["objective"] + " " + fdf["potensi"]).str.lower()
        fdf = fdf[hay.str.contains(query.strip().lower(), regex=False)]
    fdf = fdf.sort_values("res_score", ascending=False).reset_index(drop=True)

    view_choice = c_view.radio("Tampilan tabel", [T.VIEW_COMPACT, T.VIEW_FULL],
                               horizontal=True, label_visibility="collapsed",
                               help="Ringkas = kolom penting saja. Lengkap = seluruh kolom template.")
    view = "compact" if view_choice == T.VIEW_COMPACT else "full"

    selection_slot = st.empty()
    selected_kode = None
    if fdf.empty:
        st.info("Tidak ada risiko yang cocok dengan filter." if len(df) else "Register masih kosong.")
    else:
        event = st.dataframe(
            S.display_frame(fdf, view), hide_index=True, key=f"risk_table_{view}",
            on_select="rerun", selection_mode="single-row",
            column_config={"Potensi Risiko": st.column_config.TextColumn(width="large")},
        )
        rows = event.selection.rows if event is not None else []
        if rows:
            selected_kode = fdf.iloc[rows[0]]["kode"]

    if can_edit:
        if selected_kode:
            title = fdf[fdf["kode"] == selected_kode].iloc[0]["potensi"]
            selection_slot.success(f"Terpilih: **{selected_kode}** - {title}")
        elif not fdf.empty:
            selection_slot.caption("Belum ada baris yang dipilih. Centang kotak di sisi kiri sebuah baris.")
        if c_add.button(T.BTN_ADD, type="primary"):
            risk_dialog(storage, df, None)
        if c_edit.button(T.BTN_EDIT, disabled=selected_kode is None):
            risk_dialog(storage, df, df[df["kode"] == selected_kode].iloc[0].to_dict())

    c_exp.download_button(
        T.BTN_EXPORT, data=df.rename(columns=S.LABELS).to_csv(index=False).encode("utf-8-sig"),
        file_name=f"register_risiko_{date.today().isoformat()}.csv", mime="text/csv",
    )


# ---------------------------------------------------------------------------
# Tab 2: summary (for management)
# ---------------------------------------------------------------------------
def render_summary(df: pd.DataFrame):
    overdue = S.overdue_mask(df)
    target_level = df["res_score"].apply(S.severity)
    cards = [
        (T.KPI_TOTAL, len(df), T.KPI_TOTAL_TIP),
        (T.KPI_CRITICAL, int((target_level == "Very High").sum()), T.KPI_CRITICAL_TIP),
        (T.KPI_HIGH, int((target_level == "High").sum()), T.KPI_HIGH_TIP),
        (T.KPI_OVERDUE, int(overdue.sum()), T.KPI_OVERDUE_TIP),
        (T.KPI_AVG, f"{df['res_score'].mean():.1f}" if len(df) else "0.0", T.KPI_AVG_TIP),
    ]
    for col, (label, value, tip) in zip(st.columns(5), cards):
        with col:
            with st.container(border=True):
                st.metric(label, value, help=tip)

    left, right = st.columns([3, 2])
    with left:
        st.subheader(T.HEATMAP_TITLE)
        view = st.radio(T.HEATMAP_VIEW_LABEL,
                        [T.HEATMAP_VIEW_TARGETED, T.HEATMAP_VIEW_INHERENT],
                        horizontal=True)
        mode = "targeted" if view == T.HEATMAP_VIEW_TARGETED else "inherent"
        st.plotly_chart(build_heatmap(df, mode), key="heatmap")
        st.markdown(legend_table_html(), unsafe_allow_html=True)
        with st.expander("📖 Cara membaca peta ini"):
            st.markdown(
                "- Setiap kotak adalah kombinasi **tingkat dampak** (kiri ke kanan) dan "
                "**kemungkinan terjadi** (bawah ke atas).\n"
                "- Kode di dalam kotak adalah risiko yang berada di posisi tersebut. "
                "Jika lebih dari empat, ditambahkan tulisan \"more\"; arahkan kursor ke kotak untuk melihat semua kodenya.\n"
                "- **Garis putus-putus merah** adalah batas toleransi risiko: kotak di kanan-atas garis berada di atas batas toleransi (skor 8 ke atas).\n"
                "- Semakin ke **kanan-atas** (merah), semakin berbahaya. Skor = Likelihood x Impact.\n"
                "- **Inherent** = penilaian sebelum pengendalian. **Targeted** = target setelah mitigasi. "
                "Idealnya risiko bergeser ke kiri-bawah setelah mitigasi."
            )
    with right:
        st.subheader(T.TOP_RISKS_TITLE)
        st.caption(T.TOP_RISKS_CAPTION)
        top = df.sort_values("res_score", ascending=False).head(6)
        if top.empty:
            st.info(T.TOP_RISKS_EMPTY)
        else:
            st.markdown("".join(risk_card_html(row) for _, row in top.iterrows()),
                        unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
def main():
    role = login_gate()
    storage, mode, conn_error = get_storage()
    can_edit = role == "editor"
    df = load_df(storage)

    head_l, head_r = st.columns([5, 2])
    with head_l:
        st.title(f"{T.APP_ICON} {T.APP_TITLE}")
        st.caption(T.APP_SUBTITLE)
    with head_r:
        b1, b2 = st.columns(2)
        if b1.button(T.BTN_REFRESH):
            refresh_data()
            st.rerun()
        if st.session_state.get("role") and b2.button(T.BTN_SIGNOUT):
            st.session_state.pop("role", None)
            st.rerun()

    if mode == "demo":
        st.info(T.DEMO_BANNER)
        # Show diagnostics only when something is configured but not working
        if conn_error or diagnose_secrets(st.secrets)["sections"]:
            render_demo_diagnostics(conn_error)
    elif not (secret("auth", "viewer_password") or secret("auth", "editor_password")):
        st.warning(T.NO_PASSWORD_WARNING)

    flash = st.session_state.pop("flash", None)
    if flash:
        st.success(flash)

    tab_register, tab_summary = st.tabs([T.TAB_REGISTER, T.TAB_SUMMARY])
    with tab_register:
        render_register(df, storage, can_edit)
    with tab_summary:
        render_summary(df)


main()
