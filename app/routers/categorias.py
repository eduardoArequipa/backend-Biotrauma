
# app/routers/categorias.py
from fastapi import APIRouter, HTTPException
from typing import List
from app.database.connection import get_db_connection
from app.models.schemas import Categoria, CategoriaCreate

router = APIRouter(
    prefix="/categorias",
    tags=["categorias"]
)

@router.get("/", response_model=List[Categoria])
async def get_categorias():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM categorias ORDER BY nombre")
        categorias = cur.fetchall()
        return categorias
    finally:
        cur.close()
        conn.close()

@router.post("/", response_model=Categoria)
async def create_categoria(categoria: CategoriaCreate):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO categorias (nombre, descripcion)
            VALUES (%s, %s) RETURNING *
        """, (categoria.nombre, categoria.descripcion))
        conn.commit()
        nueva_categoria = cur.fetchone()
        return nueva_categoria
    finally:
        cur.close()
        conn.close()

@router.get("/{categoria_id}", response_model=Categoria)
async def get_categoria(categoria_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM categorias WHERE id = %s", (categoria_id,))
        categoria = cur.fetchone()
        if categoria is None:
            raise HTTPException(status_code=404, detail="Categoría no encontrada")
        return categoria
    finally:
        cur.close()
        conn.close()

@router.get("/{categoria_id}/productos")
async def get_productos_por_categoria(categoria_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT p.* FROM productos p
            JOIN categorias_productos cp ON p.id = cp.producto_id
            WHERE cp.categoria_id = %s
        """, (categoria_id,))
        productos = cur.fetchall()
        return productos
    finally:
        cur.close()
        conn.close()

@router.put("/{categoria_id}", response_model=Categoria)
async def update_categoria(categoria_id: int, categoria: CategoriaCreate):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE categorias 
            SET nombre = %s, descripcion = %s
            WHERE id = %s RETURNING *
        """, (categoria.nombre, categoria.descripcion, categoria_id))
        conn.commit()
        categoria_actualizada = cur.fetchone()
        if categoria_actualizada is None:
            raise HTTPException(status_code=404, detail="Categoría no encontrada")
        return categoria_actualizada
    finally:
        cur.close()
        conn.close()

@router.delete("/{categoria_id}")
async def delete_categoria(categoria_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Primero eliminar las relaciones en la tabla categorias_productos
        cur.execute("DELETE FROM categorias_productos WHERE categoria_id = %s", (categoria_id,))
        # Luego eliminar la categoría
        cur.execute("DELETE FROM categorias WHERE id = %s RETURNING id", (categoria_id,))
        conn.commit()
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Categoría no encontrada")
        return {"message": "Categoría eliminada exitosamente"}
    finally:
        cur.close()
        conn.close()