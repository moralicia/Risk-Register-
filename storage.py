"""Storage backends for the risk register.

Two interchangeable backends share the same tiny interface:

    load()          -> normalized DataFrame
    exists(kode)    -> bool
    upsert(record)  -> create or update ONE risk (row-level write)
    delete(kode)    -> delete ONE risk

* CSVStorage          - local file; zero-config demo / development mode.
* GoogleSheetsStorage - shared, multi-user storage in a Google Sheet.
                        Writes touch only the affected row (never rewrite
                        the whole sheet) and the two "Tingkat Risiko"
                        columns are real Sheets formulas (=Likelihood*Impact).
"""
from __future__ import annotations

import os
import re
import threading

import pandas as pd

import schema as S


def _col_letter(index_zero_based: int) -> str:
    """0 -> 'A', 25 -> 'Z', 26 -> 'AA' ..."""
    n = index_zero_based + 1
    letters = ""
    while n:
        n, rem = divmod(n - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


COL = {key: _col_letter(i) for i, key in enumerate(S.KEYS)}
LAST_COL = _col_letter(len(S.KEYS) - 1)


# ---------------------------------------------------------------------------
# Local CSV backend (demo / development)
# ---------------------------------------------------------------------------
class CSVStorage:
    """File-backed storage. Not suitable for real multi-user production use
    (a hosted container's disk is ephemeral) - use GoogleSheetsStorage."""

    _lock = threading.Lock()

    def __init__(self, path: str = "data/risks.csv", seed: list[dict] | None = None):
        self.path = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        if not os.path.exists(path):
            rows = [S.risk_to_record(r) for r in (seed or [])]
            pd.DataFrame(rows, columns=S.KEYS).to_csv(path, index=False)

    def _read(self) -> pd.DataFrame:
        return S.normalize(pd.read_csv(self.path, dtype=str, keep_default_na=False))

    def load(self) -> pd.DataFrame:
        with self._lock:
            return self._read()

    def exists(self, kode: str) -> bool:
        return kode in set(self.load()["kode"])

    def upsert(self, record: dict) -> None:
        record = S.risk_to_record(record)
        with self._lock:
            df = self._read()
            if record["kode"] in set(df["kode"]):
                idx = df.index[df["kode"] == record["kode"]][0]
                for key, value in record.items():
                    df.at[idx, key] = value
            else:
                df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
            df.to_csv(self.path, index=False)

    def delete(self, kode: str) -> None:
        with self._lock:
            df = self._read()
            df[df["kode"] != kode].to_csv(self.path, index=False)


# ---------------------------------------------------------------------------
# Google Sheets backend (shared, multi-user)
# ---------------------------------------------------------------------------
class GoogleSheetsStorage:
    """One risk per row in a Google Sheet.

    Concurrency notes
    -----------------
    * New rows use the Sheets API *append* call, which is atomic, so two people
      adding risks at the same moment get two separate rows.
    * Edits overwrite only the one row being edited.
    * Remaining small window: two people editing the *same* risk at the same
      moment -> last write wins. Delete also looks the row up just before
      deleting. For a team of risk owners editing mostly their own risks this
      is acceptable; use a transactional database if you need stricter
      guarantees.
    """

    def __init__(self, spreadsheet_url: str, worksheet: str, service_account_info: dict):
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(service_account_info, scopes=scopes)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_url(spreadsheet_url)
        try:
            self.ws = spreadsheet.worksheet(worksheet)
        except gspread.WorksheetNotFound:
            self.ws = spreadsheet.add_worksheet(title=worksheet, rows=500, cols=len(S.KEYS))
        if not self.ws.row_values(1):
            self.ws.update(range_name=f"A1:{LAST_COL}1", values=[S.HEADERS],
                           value_input_option="RAW")
            self.ws.freeze(rows=1)

    # -- helpers ----------------------------------------------------------
    def _codes(self) -> list[str]:
        return self.ws.col_values(1)  # index 0 is the header

    def _row_of(self, kode: str) -> int | None:
        codes = self._codes()
        if kode in codes[1:]:
            return codes.index(kode, 1) + 1  # 1-based sheet row number
        return None

    @staticmethod
    def _sheet_value(value):
        """RAW-safe cell value: keep numbers as numbers, blanks as ''."""
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return ""
        if hasattr(value, "item"):  # numpy scalar -> python scalar
            value = value.item()
        return value

    def _formula_updates(self, row: int) -> list[dict]:
        return [
            {"range": f"{COL['inh_score']}{row}",
             "values": [[f"={COL['inh_l']}{row}*{COL['inh_i']}{row}"]]},
            {"range": f"{COL['res_score']}{row}",
             "values": [[f"={COL['res_l']}{row}*{COL['res_i']}{row}"]]},
        ]

    # -- public API -------------------------------------------------------
    def load(self) -> pd.DataFrame:
        values = self.ws.get_all_values(value_render_option="UNFORMATTED_VALUE")
        if len(values) < 2:
            return S.normalize(pd.DataFrame(columns=S.KEYS))
        width = len(S.KEYS)
        rows = [(r + [""] * width)[:width] for r in values[1:]]
        return S.normalize(pd.DataFrame(rows, columns=S.KEYS))

    def exists(self, kode: str) -> bool:
        return self._row_of(kode) is not None

    def upsert(self, record: dict) -> None:
        record = S.risk_to_record(record)
        values = [self._sheet_value(record[k]) for k in S.KEYS]
        # Score cells are written as formulas below, so leave them blank here.
        values[S.KEYS.index("inh_score")] = ""
        values[S.KEYS.index("res_score")] = ""

        row = self._row_of(record["kode"])
        if row is not None:
            self.ws.update(range_name=f"A{row}:{LAST_COL}{row}", values=[values],
                           value_input_option="RAW")
        else:
            response = self.ws.append_row(values, value_input_option="RAW", table_range="A1")
            updated_range = (response or {}).get("updates", {}).get("updatedRange", "")
            match = re.search(r"![A-Z]+(\d+)", updated_range)
            row = int(match.group(1)) if match else self._row_of(record["kode"])
        if row is None:
            raise RuntimeError("Could not locate the saved row to set formulas.")
        self.ws.batch_update(self._formula_updates(row), value_input_option="USER_ENTERED")

    def delete(self, kode: str) -> None:
        row = self._row_of(kode)
        if row is not None:
            self.ws.delete_rows(row)
