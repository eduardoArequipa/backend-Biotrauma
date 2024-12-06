# app/routers/clientes.py
from fastapi import APIRouter, HTTPException
from typing import List
from app.database.connection import get_db_connection
from app.models.schemas import Cliente, ClienteCreate

router = APIRouter(
    prefix="/clientes",
    tags=["clientes"]
)

@router.get("/", response_model=List[Cliente])
async def get_clientes():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, nombre, contacto, direccion, telefono, email, rfc, tipo_cliente 
            FROM clientes 
            ORDER BY nombre
        """)
        clientes = cur.fetchall()
        return clientes
    finally:
        cur.close()
        conn.close()

@router.post("/", response_model=Cliente)
async def create_cliente(cliente: ClienteCreate):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO clientes (nombre, contacto, direccion, telefono, email, rfc, tipo_cliente)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (
            cliente.nombre,
            cliente.contacto,
            cliente.direccion,
            cliente.telefono,
            cliente.email,
            cliente.rfc,
            cliente.tipo_cliente
        ))
        conn.commit()
        nuevo_cliente = cur.fetchone()
        return nuevo_cliente
    finally:
        cur.close()
        conn.close()

@router.get("/{cliente_id}", response_model=Cliente)
async def get_cliente(cliente_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM clientes WHERE id = %s", (cliente_id,))
        cliente = cur.fetchone()
        if cliente is None:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        return cliente
    finally:
        cur.close()
        conn.close()

@router.put("/{cliente_id}", response_model=Cliente)
async def update_cliente(cliente_id: int, cliente: ClienteCreate):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE clientes
            SET nombre = %s, contacto = %s, direccion = %s, 
                telefono = %s, email = %s, rfc = %s, tipo_cliente = %s
            WHERE id = %s
            RETURNING *
        """, (
            cliente.nombre,
            cliente.contacto,
            cliente.direccion,
            cliente.telefono,
            cliente.email,
            cliente.rfc,
            cliente.tipo_cliente,
            cliente_id
        ))
        conn.commit()
        cliente_actualizado = cur.fetchone()
        if cliente_actualizado is None:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        return cliente_actualizado
    finally:
        cur.close()
        conn.close()

@router.delete("/{cliente_id}")
async def delete_cliente(cliente_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM clientes WHERE id = %s RETURNING id", (cliente_id,))
        conn.commit()
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        return {"message": "Cliente eliminado exitosamente"}
    finally:
        cur.close()
        conn.close()