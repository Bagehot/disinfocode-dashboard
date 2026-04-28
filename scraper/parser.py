"""
Extracts quantitative SLI (Structural Level Indicator) tables from report JSON.

Each SLI with field_type='table' contains a JSON array:
  [["Country", "Metric A", "Metric B", ...], [row...], ...]
We flatten these into one row per (wave, platform, SLI, country, metric).
"""

import json
import re
from html.parser import HTMLParser


class _StripTags(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts = []

    def handle_data(self, data):
        self._parts.append(data)

    def get_text(self):
        return " ".join(self._parts).strip()


def _strip_html(html: str) -> str:
    p = _StripTags()
    p.feed(html or "")
    return p.get_text()


def _parse_number(val) -> float | None:
    if val is None:
        return None
    s = str(val).strip()
    if s in ("-", "N/A", "n/a", ""):
        return None
    s = s.replace(",", "").replace(" ", "")
    s = re.sub(r"%$", "", s)
    try:
        return float(s)
    except ValueError:
        return None


def _extract_slis(api_data: dict) -> list[dict]:
    rows = []
    chapters_raw = api_data.get("chapters", [])
    if isinstance(chapters_raw, str):
        try:
            chapters_raw = json.loads(chapters_raw)
        except json.JSONDecodeError:
            return rows
    # API returns list for some platforms, dict for others
    if isinstance(chapters_raw, dict):
        chapters = list(chapters_raw.values())
    else:
        chapters = chapters_raw
    for chapter in chapters:
        if not isinstance(chapter, dict):
            continue
        chapter_name = chapter.get("name", "")
        commitments_raw = chapter.get("commitments", [])
        if isinstance(commitments_raw, str):
            try:
                commitments_raw = json.loads(commitments_raw)
            except json.JSONDecodeError:
                commitments_raw = []
        commitments = list(commitments_raw.values()) if isinstance(commitments_raw, dict) else commitments_raw
        for commitment in commitments:
            if not isinstance(commitment, dict):
                continue
            commitment_name = commitment.get("name", "")
            commitment_code = commitment.get("code", "")
            measures_raw = commitment.get("measures", [])
            if isinstance(measures_raw, str):
                try:
                    measures_raw = json.loads(measures_raw)
                except json.JSONDecodeError:
                    measures_raw = []
            measures = list(measures_raw.values()) if isinstance(measures_raw, dict) else measures_raw
            for measure in measures:
                if not isinstance(measure, dict):
                    continue
                measure_name = measure.get("name", "")
                measure_code = measure.get("code", "")
                for sli in measure.get("slis", []):
                    rows.append({
                        "chapter": chapter_name,
                        "commitment": commitment_name,
                        "commitment_code": commitment_code,
                        "measure": measure_name,
                        "measure_code": measure_code,
                        "sli_id": sli.get("id"),
                        "sli_name": sli.get("name", ""),
                        "sli_code": sli.get("code", ""),
                        "field_type": sli.get("field_type", ""),
                        "table_value": sli.get("table_value"),
                        "sig_value": _strip_html(sli.get("sig_value", "")),
                    })
    return rows


def _flatten_table(table_json: str) -> list[dict]:
    """
    Parses a table_value JSON string like:
      [["Country","Metric A","Metric B"], ["Austria","12","34"], ...]
    Returns list of {country, metric_name, value} dicts.
    """
    try:
        rows = json.loads(table_json)
    except (json.JSONDecodeError, TypeError):
        return []
    if not rows or len(rows) < 2:
        return []

    headers = [str(h).strip() for h in rows[0]]
    country_col = next(
        (i for i, h in enumerate(headers) if "country" in h.lower() or "state" in h.lower()),
        0
    )
    metric_cols = [i for i in range(len(headers)) if i != country_col]

    flat = []
    for row in rows[1:]:
        if not row:
            continue
        country = str(row[country_col]).strip() if len(row) > country_col else ""
        for mc in metric_cols:
            raw_val = row[mc] if len(row) > mc else None
            value = _parse_number(raw_val)
            flat.append({
                "country": country,
                "metric_name": headers[mc],
                "raw_value": str(raw_val) if raw_val is not None else "",
                "value": value,
            })
    return flat


def parse_all(reports: list[dict]) -> list[dict]:
    all_rows = []
    for r in reports:
        slis = _extract_slis(r["api_data"])
        count = 0
        for sli in slis:
            base = {
                "wave": r["wave"],
                "wave_label": r["wave_label"],
                "platform": r["platform"],
                "service": r["service"],
                "slug": r["slug"],
                "chapter": sli["chapter"],
                "commitment": sli["commitment"],
                "commitment_code": sli["commitment_code"],
                "measure": sli["measure"],
                "measure_code": sli["measure_code"],
                "sli_name": sli["sli_name"],
                "sli_code": sli["sli_code"],
                "methodology": sli["sig_value"][:300] if sli["sig_value"] else "",
            }
            if sli["field_type"] == "table" and sli["table_value"]:
                flat = _flatten_table(sli["table_value"])
                for entry in flat:
                    all_rows.append({**base, **entry})
                    count += 1
            else:
                # Non-table SLI: store as a single text row
                all_rows.append({
                    **base,
                    "country": "N/A",
                    "metric_name": sli["sli_name"],
                    "raw_value": sli["sig_value"][:500] if sli["sig_value"] else "",
                    "value": None,
                })

        print(f"  {r['slug']}/wave{r['wave']} — {len(slis)} SLIs, {count} table rows")

    return all_rows
