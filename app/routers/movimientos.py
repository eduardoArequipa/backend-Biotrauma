# app/routers/movimientos.py
from fastapi import APIRouter, HTTPException
from typing import List
from app.database.connection import get_db_connection
from app.models.schemas import MovimientoAlmacen, MovimientoAlmacenCreate

router = APIRouter(
    prefix="/movimientos",
    tags=["movimientos"]
)

@router.get("/", response_model=List[MovimientoAlmacen])
async def get_movimientos():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT m.*, p.nombre as producto_nombre, a.nombre as almacen_nombre
            FROM movimientos_almacen m
            JOIN productos_inventario pi ON m.producto_inventario_id = pi.id
            JOIN productos p ON pi.producto_id = p.id
            JOIN almacenes a ON pi.almacen_id = a.id
            ORDER BY m.fecha DESC
        """)
        movimientos = cur.fetchall()
        return movimientos
    finally:
        cur.close()
        conn.close()

@router.post("/", response_model=MovimientoAlmacen)
async def create_movimiento(movimiento: MovimientoAlmacenCreate):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Primero verificamos el inventario actual
        cur.execute("""
            SELECT cantidad FROM productos_inventario 
            WHERE id = %s
        """, (movimiento.producto_inventario_id,))
        
        inventario_actual = cur.fetchone()
        if not inventario_actual:
            raise HTTPException(status_code=404, detail="Producto en inventario no encontrado")

        # Calculamos la nueva cantidad
        cantidad_actual = inventario_actual['cantidad']
        nueva_cantidad = (cantidad_actual + movimiento.cantidad 
                         if movimiento.tipo == "ENTRADA" 
                         else cantidad_actual - movimiento.cantidad)
        
        if nueva_cantidad < 0 and movimiento.tipo == "SALIDA":
            raise HTTPException(status_code=400, detail="Stock insuficiente")

        # Actualizamos el inventario
        cur.execute("""
            UPDATE productos_inventario 
            SET cantidad = %s 
            WHERE id = %s
        """, (nueva_cantidad, movimiento.producto_inventario_id))

        # Registramos el movimiento
        cur.execute("""
            INSERT INTO movimientos_almacen 
            (producto_inventario_id, tipo, cantidad, motivo, fecha)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP) RETURNING *
        """, (movimiento.producto_inventario_id, movimiento.tipo,
              movimiento.cantidad, movimiento.motivo))
        
        conn.commit()
        nuevo_movimiento = cur.fetchone()
        return nuevo_movimiento
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@router.get("/{producto_id}/historial")
async def get_historial_movimientos(producto_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT m.*, p.nombre as producto_nombre, 
                   a.nombre as almacen_nombre, m.fecha
            FROM movimientos_almacen m
            JOIN productos_inventario pi ON m.producto_inventario_id = pi.id
            JOIN productos p ON pi.producto_id = p.id
            JOIN almacenes a ON pi.almacen_id = a.id
            WHERE pi.producto_id = %s
            ORDER BY m.fecha DESC
        """, (producto_id,))
        historial = cur.fetchall()
        return historial
    finally:
        cur.close()
        conn.close()