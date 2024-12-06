# app/routers/productos.py
from fastapi import APIRouter, HTTPException
from typing import List
from app.database.connection import get_db_connection
from app.models.schemas import Producto, ProductoCreate
router = APIRouter(
    prefix="/productos",
    tags=["productos"]
)

@router.get("/", response_model=List[Producto])
async def get_productos():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM productos ORDER BY id DESC")
        productos = cur.fetchall()
        return productos
    finally:
        cur.close()
        conn.close()

@router.post("/", response_model=Producto)
async def create_producto(producto: ProductoCreate):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO productos (nombre, descripcion, precio, codigo_barras, fecha_caducidad)
            VALUES (%s, %s, %s, %s, %s) RETURNING *
        """, (producto.nombre, producto.descripcion, producto.precio, 
              producto.codigo_barras, producto.fecha_caducidad))
        conn.commit()
        nuevo_producto = cur.fetchone()
        return nuevo_producto
    finally:
        cur.close()
        conn.close()

@router.get("/{producto_id}", response_model=Producto)
async def get_producto(producto_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM productos WHERE id = %s", (producto_id,))
        producto = cur.fetchone()
        if producto is None:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        return producto
    finally:
        cur.close()
        conn.close()

@router.put("/{producto_id}", response_model=Producto)
async def update_producto(producto_id: int, producto: ProductoCreate):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE productos 
            SET nombre = %s, descripcion = %s, precio = %s, 
                codigo_barras = %s, fecha_caducidad = %s
            WHERE id = %s RETURNING *
        """, (producto.nombre, producto.descripcion, producto.precio,
              producto.codigo_barras, producto.fecha_caducidad, producto_id))
        conn.commit()
        producto_actualizado = cur.fetchone()
        if producto_actualizado is None:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        return producto_actualizado
    finally:
        cur.close()
        conn.close()

@router.delete("/{producto_id}")
async def delete_producto(producto_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM productos WHERE id = %s RETURNING id", (producto_id,))
        conn.commit()
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        return {"message": "Producto eliminado exitosamente"}
    finally:
        cur.close()
        conn.close()