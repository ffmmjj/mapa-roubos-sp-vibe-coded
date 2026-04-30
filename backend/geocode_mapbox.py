#!/usr/bin/env python3
"""Step 2: Geocode remaining addresses using Mapbox API."""
import sqlite3
import os
import json
import time
from typing import Optional, Tuple, List

DB_PATH = os.path.join(os.path.dirname(__file__), "crimes.db")
GEOCACHE_PATH = os.path.join(os.path.dirname(__file__), "geocache.json")

# Mapbox API - you need to set your access token
# Get free token at: https://www.mapbox.com/
MAPBOX_ACCESS_TOKEN = os.environ.get('MAPBOX_ACCESS_TOKEN', '')
if not MAPBOX_ACCESS_TOKEN:
    print("⚠️  MAPBOX_ACCESS_TOKEN environment variable not set!")
    print("Get free token at: https://www.mapbox.com/")
    print("Then run: export MAPBOX_ACCESS_TOKEN='your_token_here'")
    exit(1)

MAPBOX_GEOCODING_URL = "https://api.mapbox.com/geocoding/v5/mapbox.places"
REQUEST_DELAY = 0.1  # Mapbox allows faster rate limits


def load_geocache() -> dict:
    """Load geocoding cache."""
    if os.path.exists(GEOCACHE_PATH):
        with open(GEOCACHE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_geocache(cache: dict):
    """Save geocoding cache."""
    with open(GEOCACHE_PATH, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def build_address(logradouro: Optional[str], bairro: Optional[str],
                  cidade: Optional[str], cep: Optional[str]) -> str:
    """Build address for geocoding."""
    parts = []
    if logradouro and str(logradouro) not in ('NULL', ''):
        parts.append(str(logradouro))
    if bairro and str(bairro) not in ('NULL', ''):
        parts.append(str(bairro))
    if cidade:
        # Normalize city names
        cidade_norm = str(cidade).replace('S.PAULO', 'São Paulo').replace('S /', 'São ').replace('S.', 'São ')
        parts.append(cidade_norm)
    if cep and str(cep) not in ('NULL', ''):
        parts.append(str(cep))
    if parts:
        parts.append('São Paulo State')  # Improve accuracy for SP state
        return ', '.join(parts)
    return ''


def geocode_address_mapbox(address: str) -> Optional[Tuple[float, float]]:
    """Geocode address using Mapbox API."""
    if not address:
        return None

    params = {
        'access_token': MAPBOX_ACCESS_TOKEN,
        'limit': 1,
        'country': 'BR',
        'types': 'address,place'
    }

    try:
        import urllib.parse
        url = f"{MAPBOX_GEOCODING_URL}/{urllib.parse.quote(address)}.json"
        with urllib.parse.urlencode(params) as qs:
            url += f"?{qs}"

        import urllib.request
        req = urllib.request.Request(url, headers={'User-Agent': 'mapa-crimes-sp/1.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())

        if data.get('features'):
            feature = data['features'][0]
            center = feature.get('center')
            if center and len(center) >= 2:
                return (center[1], center[0])  # lat, lon
    except Exception as e:
        print(f"    ⚠️  Error: {e}")

    return None


def geocode_remaining():
    """Geocode remaining records without coordinates."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    print("=== MAPBOX GEOCODING ===\n")

    # Check for records without coords
    c.execute("SELECT COUNT(*) FROM crimes WHERE latitude IS NULL OR latitude = 0")
    missing = c.fetchone()[0]
    print(f"Records to geocode: {missing:,}")

    if missing == 0:
        print("No records to geocode.")
        conn.close()
        return

    # Get unique addresses to geocode (batch by unique address)
    c.execute("""
        SELECT DISTINCT
            logradouro, bairro, cidade, cep,
            COUNT(*) as record_count,
            GROUP_CONCAT(id) as record_ids
        FROM crimes
        WHERE latitude IS NULL OR latitude = 0
        GROUP BY logradouro, bairro, cidade, cep
        ORDER BY record_count DESC
    """)
    unique_addresses = c.fetchall()
    print(f"Unique addresses to geocode: {len(unique_addresses):,}\n")

    # Load cache
    cache = load_geocache()
    print(f"Cache loaded: {len(cache):,} cached addresses\n")

    geocoded = 0
    failed = 0
    total_updated = 0

    for i, addr_info in enumerate(unique_addresses, 1):
        logr, bairro, cidade, cep, count, ids_str = addr_info
        record_ids = [int(x) for x in ids_str.split(',') if x]

        address = build_address(logr, bairro, cidade, cep)
        cache_key = address.lower().strip() if address else ''

        if not cache_key:
            print(f"[{i}/{len(unique_addresses)}] ⏭  No address to geocode ({count} records)")
            continue

        # Check cache
        if cache_key in cache:
            lat, lon = cache[cache_key]
            print(f"[{i}/{len(unique_addresses)}] ✅ Cache hit: ({count} records)")
        else:
            print(f"[{i}/{len(unique_addresses)}] 🔍 Geocoding: {address[:60]}... ({count} records)")
            result = geocode_address_mapbox(address)

            if result:
                lat, lon = result
                cache[cache_key] = (lat, lon)
                save_geocache(cache)  # Save periodically
                print(f"[{i}/{len(unique_addresses)}] ✅ Found: {lat:.6f}, {lon:.6f}")
            else:
                print(f"[{i}/{len(unique_addresses)}] ❌ Not found: {address[:60]}...")
                failed += 1
                continue

        # Update all records with this address
        placeholders = ','.join(['?'] * len(record_ids))
        c.execute(f"UPDATE crimes SET latitude = ?, longitude = ?, coords_source = 'mapbox_api' WHERE id IN ({placeholders})",
                  [lat, lon] + record_ids)
        conn.commit()

        geocoded += 1
        total_updated += count

        # Rate limiting
        time.sleep(REQUEST_DELAY)

    # Final stats
    c.execute("SELECT COUNT(*) FROM crimes WHERE latitude IS NOT NULL AND latitude != 0")
    final = c.fetchone()[0]

    print(f"\n=== RESULTS ===")
    print(f"Addresses geocoded: {geocoded:,}")
    print(f"Addresses failed: {failed:,}")
    print(f"Records updated: {total_updated:,}")
    print(f"\nFinal with coords: {final:,}")
    print(f"Still missing: {135763 - final:,}")

    conn.close()


if __name__ == "__main__":
    geocode_remaining()
