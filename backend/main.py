"""FastAPI backend for crime map application."""
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import sqlite3
import os
from typing import Optional

# Detectar se está rodando no Docker
IN_DOCKER = os.path.exists('/app/frontend')

if IN_DOCKER:
    # No Docker, os arquivos estão em /app
    DB_PATH = "/app/crimes.db"
    FRONTEND_PATH = "/app/frontend"
else:
    # No host local, paths relativos
    DB_PATH = os.path.join(os.path.dirname(__file__), "crimes.db")
    FRONTEND_PATH = os.path.join(os.path.dirname(__file__), "..", "frontend")

app = FastAPI(title="Mapa de Roubos de Celulares - SP 2025")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def build_where(bounds, cidade, bairro, periodo, data_inicio, data_fim, ano=None):
    """Build WHERE clause and params from common filter arguments."""
    conditions = []
    params = []

    if bounds:
        parts = bounds.split(",")
        if len(parts) == 4:
            sw_lat, sw_lon, ne_lat, ne_lon = [float(p) for p in parts]
            conditions.append("latitude BETWEEN ? AND ?")
            conditions.append("longitude BETWEEN ? AND ?")
            params.extend([sw_lat, ne_lat, sw_lon, ne_lon])

    if cidade:
        conditions.append("cidade = ?")
        params.append(cidade)
    if bairro:
        conditions.append("bairro = ?")
        params.append(bairro)
    if periodo:
        conditions.append("descr_periodo = ?")
        params.append(periodo)
    if data_inicio:
        conditions.append("data_ocorrencia_bo >= ?")
        params.append(data_inicio)
    if data_fim:
        conditions.append("data_ocorrencia_bo <= ?")
        params.append(data_fim)
    if ano:
        conditions.append("CAST(SUBSTR(data_ocorrencia_bo, 1, 4) AS INTEGER) = ?")
        params.append(ano)

    where = " AND ".join(conditions) if conditions else "1=1"
    return where, params


# ─── Serve frontend ──────────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory=FRONTEND_PATH), name="static")


@app.get("/")
async def index():
    return FileResponse(os.path.join(FRONTEND_PATH, "index.html"))


# ─── API Endpoints ───────────────────────────────────────────────────────────

@app.get("/api/crimes")
async def get_crimes(
    bounds: Optional[str] = Query(None, description="sw_lat,sw_lon,ne_lat,ne_lon"),
    cidade: Optional[str] = None,
    bairro: Optional[str] = None,
    periodo: Optional[str] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    ano: Optional[int] = Query(None, description="Ano de ocorrência"),
    limit: int = Query(5000, le=20000),
    offset: int = Query(0, ge=0),
):
    """Return crime points within map bounds, with optional filters."""
    conn = get_db()
    try:
        where, params = build_where(bounds, cidade, bairro, periodo, data_inicio, data_fim, ano)

        sql = f"""
            SELECT id, latitude, longitude, cidade, bairro,
                   logradouro, data_ocorrencia_bo, hora_ocorrencia,
                   marca_objeto, descr_periodo, flag_status, descr_tipolocal
            FROM crimes
            WHERE {where}
            ORDER BY data_ocorrencia_bo DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@app.get("/api/crimes/count")
async def get_crimes_count(
    bounds: Optional[str] = Query(None, description="sw_lat,sw_lon,ne_lat,ne_lon"),
    cidade: Optional[str] = None,
    bairro: Optional[str] = None,
    periodo: Optional[str] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    ano: Optional[int] = Query(None, description="Ano de ocorrência"),
):
    """Return count of crimes matching filters."""
    conn = get_db()
    try:
        where, params = build_where(bounds, cidade, bairro, periodo, data_inicio, data_fim, ano)

        sql = f"SELECT COUNT(*) as total FROM crimes WHERE {where}"
        row = conn.execute(sql, params).fetchone()
        return {"total": row["total"]}
    finally:
        conn.close()


@app.get("/api/crimes/heatmap")
async def get_heatmap_data(
    bounds: Optional[str] = Query(None, description="sw_lat,sw_lon,ne_lat,ne_lon"),
    cidade: Optional[str] = None,
    periodo: Optional[str] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    ano: Optional[int] = Query(None, description="Ano de ocorrência"),
    precision: int = Query(3, description="Decimal precision for clustering"),
):
    """Return clustered/heatmap data - groups by rounded lat/lon."""
    conn = get_db()
    try:
        where, params = build_where(bounds, cidade, None, periodo, data_inicio, data_fim, ano)

        # Build params: ROUND args come first in SQL, then WHERE args, then GROUP BY args
        heat_params = [precision, precision] + list(params) + [precision, precision]

        sql = f"""
            SELECT ROUND(latitude, ?) as lat, ROUND(longitude, ?) as lon,
                   COUNT(*) as count
            FROM crimes
            WHERE {where}
            GROUP BY ROUND(latitude, ?), ROUND(longitude, ?)
            ORDER BY count DESC
            LIMIT 10000
        """

        rows = conn.execute(sql, heat_params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@app.get("/api/filters")
async def get_filter_options():
    """Return available filter options."""
    conn = get_db()
    try:
        cidades = [r[0] for r in conn.execute(
            "SELECT DISTINCT cidade FROM crimes WHERE cidade IS NOT NULL ORDER BY cidade"
        ).fetchall()]
        periodos = [r[0] for r in conn.execute(
            "SELECT DISTINCT descr_periodo FROM crimes WHERE descr_periodo IS NOT NULL ORDER BY descr_periodo"
        ).fetchall()]
        return {
            "cidades": cidades,
            "periodos": periodos,
        }
    finally:
        conn.close()


@app.get("/api/filters/bairros")
async def get_bairros(cidade: str):
    """Return bairros for a given cidade."""
    conn = get_db()
    try:
        bairros = [r[0] for r in conn.execute(
            "SELECT DISTINCT bairro FROM crimes WHERE cidade = ? AND bairro IS NOT NULL ORDER BY bairro",
            (cidade,)
        ).fetchall()]
        return {"bairros": bairros}
    finally:
        conn.close()


@app.get("/api/stats")
async def get_stats(
    cidade: Optional[str] = None,
    bairro: Optional[str] = None,
    periodo: Optional[str] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    ano: Optional[int] = Query(None, description="Ano de ocorrência"),
):
    """Return general statistics about the dataset."""
    conn = get_db()
    try:
        # Build WHERE clause based on filters
        conditions = []
        params = []
        if cidade:
            conditions.append("cidade = ?")
            params.append(cidade)
        if bairro:
            conditions.append("bairro = ?")
            params.append(bairro)
        if periodo:
            conditions.append("descr_periodo = ?")
            params.append(periodo)
        if data_inicio:
            conditions.append("data_ocorrencia_bo >= ?")
            params.append(data_inicio)
        if data_fim:
            conditions.append("data_ocorrencia_bo <= ?")
            params.append(data_fim)
        if ano:
            conditions.append("CAST(SUBSTR(data_ocorrencia_bo, 1, 4) AS INTEGER) = ?")
            params.append(ano)
        
        where = " AND ".join(conditions) if conditions else "1=1"

        total = conn.execute(f"SELECT COUNT(*) FROM crimes WHERE {where}", params).fetchone()[0]

        by_periodo = [dict(r) for r in conn.execute(f"""
            SELECT descr_periodo, COUNT(*) as count
            FROM crimes WHERE descr_periodo IS NOT NULL AND {where}
            GROUP BY descr_periodo ORDER BY count DESC
        """, params).fetchall()]

        by_month = [dict(r) for r in conn.execute(f"""
            SELECT mes_registro_bo as mes, COUNT(*) as count
            FROM crimes WHERE {where}
            GROUP BY mes_registro_bo ORDER BY mes_registro_bo
        """, params).fetchall()]

        by_cidade = [dict(r) for r in conn.execute(f"""
            SELECT cidade, COUNT(*) as count
            FROM crimes WHERE {where}
            GROUP BY cidade ORDER BY count DESC LIMIT 10
        """, params).fetchall()]

        by_tipolocal = [dict(r) for r in conn.execute(f"""
            SELECT descr_tipolocal, COUNT(*) as count
            FROM crimes WHERE descr_tipolocal IS NOT NULL AND {where}
            GROUP BY descr_tipolocal ORDER BY count DESC LIMIT 10
        """, params).fetchall()]

        anos = [row[0] for row in conn.execute(f"""
            SELECT DISTINCT CAST(SUBSTR(data_ocorrencia_bo, 1, 4) AS INTEGER) as ano
            FROM crimes WHERE data_ocorrencia_bo IS NOT NULL AND {where}
            ORDER BY ano
        """, params).fetchall()]

        return {
            "total": total,
            "by_periodo": by_periodo,
            "by_month": by_month,
            "by_cidade": by_cidade,
            "by_tipolocal": by_tipolocal,
            "anos": anos,
        }
    finally:
        conn.close()


@app.get("/api/stats/area")
async def get_area_stats(
    selection: str = Query(..., description="sw_lat,sw_lon,ne_lat,ne_lon for selected rectangle"),
    cidade: Optional[str] = None,
    bairro: Optional[str] = None,
    periodo: Optional[str] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    ano: Optional[int] = Query(None, description="Ano de ocorrência"),
):
    """Return statistics for crimes within a selected rectangular area."""
    conn = get_db()
    try:
        # Parse selection bounds
        parts = selection.split(",")
        if len(parts) != 4:
            return {"error": "selection must be sw_lat,sw_lon,ne_lat,ne_lon"}
        sw_lat, sw_lon, ne_lat, ne_lon = [float(p) for p in parts]

        conditions = ["latitude BETWEEN ? AND ?", "longitude BETWEEN ? AND ?"]
        params = [sw_lat, ne_lat, sw_lon, ne_lon]

        if cidade:
            conditions.append("cidade = ?")
            params.append(cidade)
        if bairro:
            conditions.append("bairro = ?")
            params.append(bairro)
        if periodo:
            conditions.append("descr_periodo = ?")
            params.append(periodo)
        if data_inicio:
            conditions.append("data_ocorrencia_bo >= ?")
            params.append(data_inicio)
        if data_fim:
            conditions.append("data_ocorrencia_bo <= ?")
            params.append(data_fim)
        if ano:
            conditions.append("CAST(SUBSTR(data_ocorrencia_bo, 1, 4) AS INTEGER) = ?")
            params.append(ano)

        where = " AND ".join(conditions)

        # Total count
        total = conn.execute(f"SELECT COUNT(*) FROM crimes WHERE {where}", params).fetchone()[0]

        if total == 0:
            return {
                "total": 0,
                "by_periodo": [],
                "by_month": [],
                "by_tipolocal": [],
                "by_marca": [],
                "by_bairro": [],
                "by_flagrante": [],
                "by_autoria": [],
                "hotspots": [],
            }

        # By period of day
        by_periodo = [dict(r) for r in conn.execute(f"""
            SELECT descr_periodo, COUNT(*) as count
            FROM crimes WHERE {where} AND descr_periodo IS NOT NULL
            GROUP BY descr_periodo ORDER BY count DESC
        """, params).fetchall()]

        # By month
        by_month = [dict(r) for r in conn.execute(f"""
            SELECT mes_registro_bo as mes, COUNT(*) as count
            FROM crimes WHERE {where}
            GROUP BY mes_registro_bo ORDER BY mes_registro_bo
        """, params).fetchall()]

        # By type of location
        by_tipolocal = [dict(r) for r in conn.execute(f"""
            SELECT descr_tipolocal, COUNT(*) as count
            FROM crimes WHERE {where} AND descr_tipolocal IS NOT NULL
            GROUP BY descr_tipolocal ORDER BY count DESC LIMIT 10
        """, params).fetchall()]

        # By phone brand
        by_marca = [dict(r) for r in conn.execute(f"""
            SELECT marca_objeto, COUNT(*) as count
            FROM crimes WHERE {where} AND marca_objeto IS NOT NULL
            GROUP BY marca_objeto ORDER BY count DESC LIMIT 8
        """, params).fetchall()]

        # By bairro (top 10)
        by_bairro = [dict(r) for r in conn.execute(f"""
            SELECT bairro, COUNT(*) as count
            FROM crimes WHERE {where} AND bairro IS NOT NULL
            GROUP BY bairro ORDER BY count DESC LIMIT 10
        """, params).fetchall()]

        # Flagrante
        flagrante_row = conn.execute(f"""
            SELECT
                SUM(CASE WHEN flag_flagrante = 'S' THEN 1 ELSE 0 END) as com_flagrante,
                SUM(CASE WHEN flag_flagrante = 'N' THEN 1 ELSE 0 END) as sem_flagrante
            FROM crimes WHERE {where}
        """, params).fetchone()
        flagrante_data = dict(flagrante_row) if flagrante_row else {}

        # Autoria
        by_autoria = [dict(r) for r in conn.execute(f"""
            SELECT autoria_bo, COUNT(*) as count
            FROM crimes WHERE {where} AND autoria_bo IS NOT NULL
            GROUP BY autoria_bo ORDER BY count DESC
        """, params).fetchall()]

        # Top hotspots (rounded coordinates with most occurrences)
        hotspots = [dict(r) for r in conn.execute(f"""
            SELECT ROUND(latitude, 4) as lat, ROUND(longitude, 4) as lon,
                   COUNT(*) as count,
                   GROUP_CONCAT(DISTINCT logradouro) as ruas
            FROM crimes WHERE {where}
            GROUP BY ROUND(latitude, 4), ROUND(longitude, 4)
            ORDER BY count DESC LIMIT 5
        """, params).fetchall()]

        return {
            "total": total,
            "by_periodo": by_periodo,
            "by_month": by_month,
            "by_tipolocal": by_tipolocal,
            "by_marca": by_marca,
            "by_bairro": by_bairro,
            "by_flagrante": flagrante_data,
            "by_autoria": by_autoria,
            "hotspots": hotspots,
        }
    finally:
        conn.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
