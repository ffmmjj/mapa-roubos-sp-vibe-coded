#!/usr/bin/env python3
"""Step 1: Cross-reference - infer coordinates from similar addresses."""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "crimes.db")


def cross_reference_coords():
    """Fill missing coordinates using cross-reference with similar addresses."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

    print("=== CROSS-REFERENCE COORDINATES ===\n")

    # Count before
    c.execute("SELECT COUNT(*) FROM crimes WHERE latitude IS NOT NULL AND latitude != 0")
    before = c.fetchone()[0]
    print(f"Before: {before:,} records with coords")

    # Step 1: Match by exact (logradouro, bairro, cidade)
    print("\nStep 1: Exact match (rua + bairro + cidade)...")
    c.execute("""
        UPDATE crimes
        SET latitude = sub.avg_lat,
            longitude = sub.avg_lon,
            coords_resolved = 1,
            coords_source = 'cross_reference_exact'
        FROM (
            SELECT
                c2.logradouro,
                c2.bairro,
                c2.cidade,
                AVG(c1.latitude) as avg_lat,
                AVG(c1.longitude) as avg_lon
            FROM crimes c1
            JOIN crimes c2 ON c1.logradouro = c2.logradouro
                            AND c1.bairro = c2.bairro
                            AND c1.cidade = c2.cidade
            WHERE c1.latitude IS NOT NULL AND c1.latitude != 0
              AND c2.latitude IS NULL OR c2.latitude = 0
              AND c1.logradouro IS NOT NULL AND c1.logradouro != ''
              AND c2.logradouro IS NOT NULL AND c2.logradouro != ''
            GROUP BY c2.logradouro, c2.bairro, c2.cidade
        ) sub
        WHERE crimes.logradouro = sub.logradouro
          AND crimes.bairro = sub.bairro
          AND crimes.cidade = sub.cidade
          AND (crimes.latitude IS NULL OR crimes.latitude = 0)
    """)
    conn.commit()
    exact_match = c.rowcount if hasattr(c, 'rowcount') else 0
    print(f"  Matched: {exact_match:,} records")

    # Step 2: Match by (bairro, cidade) - less precise but better than nothing
    print("\nStep 2: Partial match (bairro + cidade)...")
    c.execute("""
        UPDATE crimes
        SET latitude = sub.avg_lat,
            longitude = sub.avg_lon,
            coords_resolved = 1,
            coords_source = 'cross_reference_bairro'
        FROM (
            SELECT
                c2.bairro,
                c2.cidade,
                AVG(c1.latitude) as avg_lat,
                AVG(c1.longitude) as avg_lon
            FROM crimes c1
            JOIN crimes c2 ON c1.bairro = c2.bairro
                            AND c1.cidade = c2.cidade
            WHERE c1.latitude IS NOT NULL AND c1.latitude != 0
              AND c2.latitude IS NULL OR c2.latitude = 0
              AND c1.bairro IS NOT NULL AND c1.bairro != ''
              AND c2.bairro IS NOT NULL AND c2.bairro != ''
            GROUP BY c2.bairro, c2.cidade
        ) sub
        WHERE crimes.bairro = sub.bairro
          AND crimes.cidade = sub.cidade
          AND (crimes.latitude IS NULL OR crimes.latitude = 0)
    """)
    conn.commit()
    bairro_match = c.rowcount if hasattr(c, 'rowcount') else 0
    print(f"  Matched: {bairro_match:,} records")

    # Count after cross-reference
    c.execute("SELECT COUNT(*) FROM crimes WHERE latitude IS NOT NULL AND latitude != 0")
    after = c.fetchone()[0]
    print(f"\nAfter cross-reference: {after:,} records with coords")
    print(f"Resolved: {after - before:,} records")

    # Remaining without coords
    c.execute("SELECT COUNT(*) FROM crimes WHERE latitude IS NULL OR latitude = 0")
    remaining = c.fetchone()[0]
    print(f"Still missing: {remaining:,} records")

    # Sample of remaining addresses
    print("\nSample of addresses still without coords:")
    c.execute("""
        SELECT logradouro, bairro, cidade, cep, COUNT(*) as cnt
        FROM crimes
        WHERE latitude IS NULL OR latitude = 0
        GROUP BY logradouro, bairro, cidade, cep
        ORDER BY cnt DESC
        LIMIT 10
    """)
    for row in c.fetchall():
        logr, bairro, cidade, cep, cnt = row
        print(f"  {logr or 'N/A':40s} {bairro or 'N/A':20s} {cidade or 'N/A':20s} ({cnt} regs)")

    conn.close()
    return remaining


if __name__ == "__main__":
    remaining = cross_reference_coords()
    if remaining > 0:
        print(f"\nNext step: Use Mapbox API for remaining {remaining:,} records")
    else:
        print("\n✅ All records resolved via cross-reference!")
