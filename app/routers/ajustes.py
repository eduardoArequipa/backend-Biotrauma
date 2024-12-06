from fastapi import APIRouter, HTTPException
from typing import List
from app.database.connection import get_db_connection
from app.models.schemas import AjusteInventario, AjusteInventarioCreate

router = APIRouter(
    prefix="/ajustes",
    tags=["ajustes"]
)

@router.get("/", response_model=List[AjusteInventario])
async def get_ajustes():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT a.*, p.nombre as producto_nombre
            FROM ajustes_inventario a
            JOIN productos_inventario pi ON a.producto_inventario_id = pi.id
            JOIN productos p ON pi.producto_id = p.id
            ORDER BY a.fecha DESC
        """)
        ajustes = cur.fetchall()
        return ajustes
    finally:
        cur.close()
        conn.close()

@router.post("/", response_model=AjusteInventario)
async def create_ajuste(ajuste: AjusteInventarioCreate):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Registrar el ajuste
        cur.execute("""
            INSERT INTO ajustes_inventario 
            (producto_inventario_id, tipo, cantidad_anterior, 
             cantidad_nueva, motivo, fecha)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP) RETURNING *
        """, (ajuste.producto_inventario_id, ajuste.tipo,
              ajuste.cantidad_anterior, ajuste.cantidad_nueva,
              ajuste.motivo))

        # Actualizar el inventario
        cur.execute("""
            UPDATE productos_inventario 
            SET cantidad = %s 
            WHERE id = %s
        """, (ajuste.cantidad_nueva, ajuste.producto_inventario_id))
        
        conn.commit()
        nuevo_ajuste = cur.fetchone()
        return nuevo_ajuste
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@router.get("/producto/{producto_id}")
async def get_ajustes_producto(producto_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT a.*, p.nombre as producto_nombre
            FROM ajustes_inventario a
            JOIN productos_inventario pi ON a.producto_inventario_id = pi.id
            JOIN productos p ON pi.producto_id = p.id
            WHERE pi.producto_id = %s
            ORDER BY a.fecha DESC
        """, (producto_id,))
        ajustes = cur.fetchall()
        return ajustes
    finally:
        cur.close()
        conn.close()