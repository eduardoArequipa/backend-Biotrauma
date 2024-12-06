
# app/routers/almacenes.py
from fastapi import APIRouter, HTTPException
from typing import List
from app.database.connection import get_db_connection
from app.models.schemas import Almacen, AlmacenCreate,ProductoInventario
router = APIRouter(
    prefix="/almacenes",
    tags=["almacenes"]
)

@router.get("/", response_model=List[Almacen])
async def get_almacenes():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM almacenes ORDER BY nombre")
        almacenes = cur.fetchall()
        return almacenes
    finally:
        cur.close()
        conn.close()

@router.post("/", response_model=Almacen)
async def create_almacen(almacen: AlmacenCreate):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO almacenes (nombre, ubicacion, capacidad)
            VALUES (%s, %s, %s) RETURNING *
        """, (almacen.nombre, almacen.ubicacion, almacen.capacidad))
        conn.commit()
        nuevo_almacen = cur.fetchone()
        return nuevo_almacen
    finally:
        cur.close()
        conn.close()

@router.get("/{almacen_id}", response_model=Almacen)
async def get_almacen(almacen_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM almacenes WHERE id = %s", (almacen_id,))
        almacen = cur.fetchone()
        if almacen is None:
            raise HTTPException(status_code=404, detail="Almacén no encontrado")
        return almacen
    finally:
        cur.close()
        conn.close()

# En app/routers/inventario.py, agregar:

@router.get("/almacen/{almacen_id}", response_model=List[ProductoInventario])
async def get_inventario_por_almacen(almacen_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT 
                pi.*,
                p.nombre as producto_nombre
            FROM productos_inventario pi
            JOIN productos p ON pi.producto_id = p.id
            WHERE pi.almacen_id = %s
            ORDER BY p.nombre
        """, (almacen_id,))
        
        inventario = cur.fetchall()
        return inventario
    finally:
        cur.close()
        conn.close()


@router.get("/{almacen_id}/inventario")
async def get_inventario_almacen(almacen_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT p.*, pi.cantidad, pi.ubicacion, pi.precio_compra, pi.precio_venta
            FROM productos p
            JOIN productos_inventario pi ON p.id = pi.producto_id
            WHERE pi.almacen_id = %s
        """, (almacen_id,))
        inventario = cur.fetchall()
        return inventario
    finally:
        cur.close()
        conn.close()