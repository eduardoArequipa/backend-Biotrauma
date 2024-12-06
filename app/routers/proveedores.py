# app/routers/proveedores.py
from fastapi import APIRouter, HTTPException
from typing import List
from app.database.connection import get_db_connection
from app.models.schemas import Proveedor, ProveedorCreate

router = APIRouter(
    prefix="/proveedores",
    tags=["proveedores"]
)

@router.get("/", response_model=List[Proveedor])
async def get_proveedores():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM proveedores ORDER BY nombre")
        proveedores = cur.fetchall()
        return proveedores
    finally:
        cur.close()
        conn.close()

@router.post("/", response_model=Proveedor)
async def create_proveedor(proveedor: ProveedorCreate):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO proveedores (nombre, contacto, direccion, telefono, email)
            VALUES (%s, %s, %s, %s, %s) RETURNING *
        """, (proveedor.nombre, proveedor.contacto, proveedor.direccion,
              proveedor.telefono, proveedor.email))
        conn.commit()
        nuevo_proveedor = cur.fetchone()
        return nuevo_proveedor
    finally:
        cur.close()
        conn.close()

@router.get("/{proveedor_id}", response_model=Proveedor)
async def get_proveedor(proveedor_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM proveedores WHERE id = %s", (proveedor_id,))
        proveedor = cur.fetchone()
        if proveedor is None:
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        return proveedor
    finally:
        cur.close()
        conn.close()

@router.get("/{proveedor_id}/productos")
async def get_productos_por_proveedor(proveedor_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT p.*, pp.precio_compra, pp.tiempo_entrega 
            FROM productos p
            JOIN proveedores_productos pp ON p.id = pp.producto_id
            WHERE pp.proveedor_id = %s
        """, (proveedor_id,))
        productos = cur.fetchall()
        return productos
    finally:
        cur.close()
        conn.close()

@router.put("/{proveedor_id}", response_model=Proveedor)
async def update_proveedor(proveedor_id: int, proveedor: ProveedorCreate):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE proveedores 
            SET nombre = %s, contacto = %s, direccion = %s, telefono = %s, email = %s
            WHERE id = %s RETURNING *
        """, (proveedor.nombre, proveedor.contacto, proveedor.direccion,
              proveedor.telefono, proveedor.email, proveedor_id))
        conn.commit()
        proveedor_actualizado = cur.fetchone()
        if proveedor_actualizado is None:
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        return proveedor_actualizado
    finally:
        cur.close()
        conn.close()

@router.delete("/{proveedor_id}")
async def delete_proveedor(proveedor_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Primero eliminar las relaciones en la tabla proveedores_productos
        cur.execute("DELETE FROM proveedores_productos WHERE proveedor_id = %s", (proveedor_id,))
        # Luego eliminar el proveedor
        cur.execute("DELETE FROM proveedores WHERE id = %s RETURNING id", (proveedor_id,))
        conn.commit()
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        return {"message": "Proveedor eliminado exitosamente"}
    finally:
        cur.close()
        conn.close()