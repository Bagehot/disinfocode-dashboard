"""Downloads JSON reports from the disinfocode.eu API."""

import json
import time
import requests
from pathlib import Path
from scraper.config import BASE_URL, WAVES, REPORT_TARGETS

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (research/academic project)"})


def fetch_report(slug: str, wave: int) -> dict | None:
    url = f"{BASE_URL}/{slug}/{wave}/json"
    try:
        resp = SESSION.get(url, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            print(f"  [{wave}] {slug} — OK ({len(resp.content)//1024} KB)")
            return data
        print(f"  [{wave}] {slug} — HTTP {resp.status_code}")
        return None
    except requests.RequestException as e:
        print(f"  [{wave}] {slug} — ERROR: {e}")
        return None


def cache_path(slug: str, wave: int) -> Path:
    d = RAW_DIR / f"wave{wave}"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{slug}.json"


def fetch_all(waves: list[int] = None) -> list[dict]:
    target_waves = waves or list(WAVES.keys())
    results = []

    for wave in target_waves:
        print(f"\n=== Wave {wave} — {WAVES[wave]} ===")
        for slug, platform, service in REPORT_TARGETS[wave]:
            cached = cache_path(slug, wave)
            if cached.exists():
                print(f"  [{wave}] {slug} — cached")
                api_data = json.loads(cached.read_text(encoding="utf-8"))
            else:
                api_data = fetch_report(slug, wave)
                if api_data:
                    cached.write_text(json.dumps(api_data, ensure_ascii=False, indent=2), encoding="utf-8")
                time.sleep(0.8)

            if api_data:
                results.append({
                    "wave": wave,
                    "wave_label": WAVES[wave],
                    "platform": platform,
                    "service": service,
                    "slug": slug,
                    "api_data": api_data,
                })

    return results


def load_cached(waves: list[int] = None) -> list[dict]:
    target_waves = waves or list(WAVES.keys())
    results = []
    for wave in target_waves:
        for slug, platform, service in REPORT_TARGETS[wave]:
            p = cache_path(slug, wave)
            if p.exists():
                api_data = json.loads(p.read_text(encoding="utf-8"))
                results.append({
                    "wave": wave,
                    "wave_label": WAVES[wave],
                    "platform": platform,
                    "service": service,
                    "slug": slug,
                    "api_data": api_data,
                })
    return results
