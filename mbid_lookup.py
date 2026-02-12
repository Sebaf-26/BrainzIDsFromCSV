#!/usr/bin/env python3
"""
Read a CSV of artists and fetch MusicBrainz Artist MBIDs.

Input CSV:
- must have a column named: Artist

Output CSV columns:
- original_artist_field
- extracted_artist_name
- mbid
- score
- type
- country
- disambiguation
- matched_name

Usage:
  python mbid_lookup.py --input artisti_playlist.csv --output artisti_mbid.csv \
    --app "ProgettoHydratech-MBIDLookup/1.0" --contact "you@example.com"

Notes:
- MusicBrainz requires a proper User-Agent that includes an application name + version + contact.
- Rate-limited: this script sleeps 1.0s between requests by default.
"""

import argparse
import csv
import re
import time
from typing import Dict, List, Optional, Tuple

import requests


SEPARATORS_REGEX = re.compile(
    r"""
    \s*(?:,|&| and | x | feat\. | ft\. | featuring | with | vs\. )\s*
    """,
    re.IGNORECASE | re.VERBOSE,
)


def split_collab(s: str) -> List[str]:
    """
    Split common collaboration strings into individual artist names.
    Keeps things like "The Rolling Stones" intact.
    """
    s = (s or "").strip()
    if not s:
        return []

    # Normalize fancy apostrophes etc. (MusicBrainz usually copes, but it helps)
    s = s.replace("’", "'").replace("–", "-").replace("—", "-")

    parts = [p.strip() for p in SEPARATORS_REGEX.split(s) if p.strip()]
    # Deduplicate while keeping order
    seen = set()
    out = []
    for p in parts:
        key = p.lower()
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def mb_search_artist(name: str, session: requests.Session, headers: Dict[str, str], timeout: int = 20) -> Optional[Dict]:
    """
    Query MusicBrainz artist search and return best match dict.
    """
    url = "https://musicbrainz.org/ws/2/artist/"
    params = {
        "query": f'artist:"{name}"',
        "fmt": "json",
        "limit": 5,
    }
    r = session.get(url, params=params, headers=headers, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    artists = data.get("artists") or []
    if not artists:
        return None

    # Choose the best match:
    # 1) highest score
    # 2) if tie, prefer type "Group" or "Person" over null
    def rank(a: Dict) -> Tuple[int, int]:
        score = int(a.get("score") or 0)
        t = a.get("type") or ""
        type_bonus = 1 if t in ("Group", "Person", "Orchestra", "Choir") else 0
        return (score, type_bonus)

    best = sorted(artists, key=rank, reverse=True)[0]
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Input CSV path (must have column 'Artist')")
    ap.add_argument("--output", required=True, help="Output CSV path")
    ap.add_argument("--app", required=True, help="App name/version for User-Agent, e.g. 'MyApp/1.0'")
    ap.add_argument("--contact", required=True, help="Contact email or URL for User-Agent")
    ap.add_argument("--sleep", type=float, default=1.0, help="Seconds to sleep between API calls (default 1.0)")
    ap.add_argument("--no-split", action="store_true", help="Do not split collaborations; treat each row as one artist string")
    args = ap.parse_args()

    headers = {
        "User-Agent": f"{args.app} ({args.contact})",
        "Accept": "application/json",
    }

    session = requests.Session()

    # Read input
    with open(args.input, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if "Artist" not in reader.fieldnames:
            raise SystemExit(f"Input CSV must contain a column named 'Artist'. Found: {reader.fieldnames}")
        rows = list(reader)

    # Build a unique lookup list to minimize API calls
    extracted_entries: List[Tuple[str, str]] = []  # (original_field, extracted_name)
    for row in rows:
        original = (row.get("Artist") or "").strip()
        if not original:
            continue
        if args.no_split:
            extracted_entries.append((original, original))
        else:
            for name in split_collab(original):
                extracted_entries.append((original, name))

    # Deduplicate extracted names (case-insensitive) but keep originals mapping
    unique_names: Dict[str, str] = {}
    for _, name in extracted_entries:
        k = name.lower()
        if k not in unique_names:
            unique_names[k] = name

    cache: Dict[str, Optional[Dict]] = {}
    out_rows = []

    # Query MusicBrainz for each unique name
    for k, name in unique_names.items():
        try:
            best = mb_search_artist(name, session, headers)
        except requests.HTTPError as e:
            # If rate limited (503/429), wait longer and continue
            best = None
            print(f"[WARN] HTTP error for '{name}': {e}")
        except Exception as e:
            best = None
            print(f"[WARN] Error for '{name}': {e}")

        cache[k] = best
        time.sleep(args.sleep)

    # Expand back to per-original/per-extracted output rows
    for original, extracted in extracted_entries:
        best = cache.get(extracted.lower())
        out_rows.append({
            "original_artist_field": original,
            "extracted_artist_name": extracted,
            "mbid": (best or {}).get("id"),
            "score": (best or {}).get("score"),
            "type": (best or {}).get("type"),
            "country": (best or {}).get("country"),
            "disambiguation": (best or {}).get("disambiguation"),
            "matched_name": (best or {}).get("name"),
        })

    # Write output
    fieldnames = [
        "original_artist_field",
        "extracted_artist_name",
        "mbid",
        "score",
        "type",
        "country",
        "disambiguation",
        "matched_name",
    ]
    with open(args.output, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out_rows)

    print(f"✅ Wrote: {args.output}")
    print(f"Unique artist names queried: {len(unique_names)}")
    print("Tip: if you see many wrong matches, try --no-split or increase --sleep.")


if __name__ == "__main__":
    main()
