# 📋 Market Risk Register

A web-based **enterprise risk register** built with Streamlit. Risk owners enter and update
their own risks from a browser (no software to install, no special account), while management
gets a live dashboard: KPIs, a 5×5 heat map, a ranked top-risks list and a filterable register.

> **Live demo:** _add your Streamlit Community Cloud link here_ (runs on fictional data)

<!-- Add a screenshot: ![Dashboard](docs/dashboard.png) -->

## Features

- **5×5 risk matrix heat map** with inherent vs targeted (residual) views and hover details
- **KPI strip**: total, critical, high, overdue reviews, average targeted score
- **Top risks** ranked by targeted risk level
- **Full 21-field register** following the Indonesian corporate risk-register template
  (Identifikasi Risiko, Severity, Risk Owner, Existing Control, Inherent Analysis,
  Mitigation Plan, Targeted Risk) plus status and review-date tracking
- **Tingkat Risiko = Likelihood × Impact**: computed live in the app and written to
  Google Sheets as real `=N5*O5` formulas
- **Overdue review flagging**, filters (category, status, severity), text search
- **Add / edit / delete** through a guided dialog with live score preview
- **Role-based access**: separate *editor* (risk owners) and *viewer* (management) passwords
- **Audit trail**: every save records who changed it and when
- **CSV export** (Excel-friendly)
- **Two storage backends** behind one interface: local CSV (demo) and Google Sheets (shared)

## Architecture

```
app.py          Streamlit UI (dashboard, filters, dialog, auth)
schema.py       Column layout, scoring, severity bands, normalisation (pure Python, tested)
storage.py      CSVStorage (demo) and GoogleSheetsStorage (multi-user, row-level writes)
sample_data.py  Fictional demo risks
tests/          Unit tests for core logic and storage
```

Design decisions worth noting:

- **Row-level writes.** Google Sheets saves append or overwrite only the affected row; the sheet
  is never rewritten wholesale, so two risk owners adding risks at the same time don't collide.
- **Scores can't drift.** Tingkat Risiko is always recomputed from likelihood × impact on read.
- **Same sheet layout as the Google Apps Script edition** of this project (columns A–Y), so
  either front end can use the same spreadsheet.
- **Config over code.** Switching from demo to production is done purely through secrets.

## Quick start (demo mode, no credentials)

macOS / Linux:

```bash
git clone <your-repo-url> && cd risk-register
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Windows (PowerShell):

```powershell
git clone <your-repo-url>; cd risk-register
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Run the tests: `pip install pytest && pytest -q`

## Connect a shared Google Sheet

1. Create a Google Sheet (any name).
2. In Google Cloud Console: create a project → enable **Google Sheets API** →
   **IAM & Admin → Service Accounts** → create one → **Keys → Add key → JSON** (download).
3. Open your Sheet → **Share** → add the service account's `client_email` as **Editor**.
4. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in the sheet URL,
   the passwords and the values from the JSON key.
5. `streamlit run app.py`. The `Risks` worksheet and header row are created automatically.

## Deploy on Streamlit Community Cloud

1. Push this repo to GitHub (the `.gitignore` keeps secrets and local data out).
2. Go to <https://share.streamlit.io> → **New app** → pick the repo, branch and `app.py`.
3. **Advanced settings → Secrets**: paste the contents of your `secrets.toml`.
4. Deploy, then share the link.

### Two deployments (recommended)

| Instance | Data | Secrets | Visibility |
|---|---|---|---|
| **Portfolio demo** | Fictional sample data (demo mode) | none | Public |
| **Company production** | Real risks in the company's Google Sheet | passwords + service account | Private / password-protected |

Never put real company risk data in the public repository or the public demo.

## Security notes

- Real risk data is confidential: always set `[auth]` passwords for a production deployment.
- Never commit `secrets.toml` or the service-account JSON.
- Passwords are checked with constant-time comparison. For stronger needs (SSO, per-user
  roles) put the app behind your organisation's identity provider.

## Known limitations / roadmap

- Two people editing the *same* risk at the same instant → last write wins.
- Single shared password per role (no individual accounts yet).
- Roadmap: per-owner edit permissions, change history view, KRI tracking, email reminders for
  overdue reviews, PDF management report.

## License

MIT — free to use and adapt.
