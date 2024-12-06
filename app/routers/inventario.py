# app/routers/inventario.py
from fastapi import APIRouter, HTTPException
from typing import List
from ..database.connection import get_db_connection
from ..models.schemas import MovimientoAlmacenCreate, ProductoInventario, ProductoInventarioCreate

router = APIRouter(
    prefix="/inventario",
    tags=["inventario"]
)

@router.get("/", response_model=List[ProductoInventario])
async def get_inventario():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT
                pi.id,
                pi.producto_id,
                pi.almacen_id,
                p.nombre as producto_nombre,
                a.nombre as almacen_nombre,
                pi.cantidad,
                pi.stock_minimo,
                pi.stock_maximo,
                pi.precio_compra,
                pi.precio_venta
            FROM productos_inventario pi
            JOIN productos p ON pi.producto_id = p.id
            JOIN almacenes a ON pi.almacen_id = a.id
            ORDER BY p.nombre
        """)
        inventario = cur.fetchall()
        return inventario
    finally:
        cur.close()
        conn.close()

@router.get("/bajo-stock", response_model=List[ProductoInventario])
async def get_bajo_stock():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT
                pi.*,
                p.nombre as producto_nombre,
                a.nombre as almacen_nombre
            FROM productos_inventario pi
            JOIN productos p ON pi.producto_id = p.id
            JOIN almacenes a ON pi.almacen_id = a.id
            WHERE pi.cantidad <= pi.stock_minimo
        """)
        productos_bajo_stock = cur.fetchall()
        return productos_bajo_stock
    finally:
        cur.close()
        conn.close()

@router.post("/inicializar", response_model=ProductoInventario)
async def inicializar_producto_inventario(producto: ProductoInventarioCreate):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Verificar si ya existe el producto en el inventario
        cur.execute("""
            SELECT id FROM productos_inventario
            WHERE producto_id = %s AND almacen_id = %s
        """, (producto.producto_id, producto.almacen_id))
        
        if cur.fetchone():
            raise HTTPException(
                status_code=400, 
                detail="El producto ya está inicializado en este almacén"
            )

        # Crear registro en inventario
        cur.execute("""
            INSERT INTO productos_inventario
            (producto_id, almacen_id, cantidad, stock_minimo, stock_maximo, 
             precio_compra, precio_venta, ubicacion)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (
            producto.producto_id,
            producto.almacen_id,
            producto.cantidad,
            producto.stock_minimo,
            producto.stock_maximo,
            producto.precio_compra,
            producto.precio_venta,
            producto.ubicacion
        ))
        
        conn.commit()
        nuevo_inventario = cur.fetchone()

        # Obtener datos completos incluyendo nombres
        cur.execute("""
            SELECT 
                pi.*,
                p.nombre as producto_nombre,
                a.nombre as almacen_nombre
            FROM productos_inventario pi
            JOIN productos p ON pi.producto_id = p.id
            JOIN almacenes a ON pi.almacen_id = a.id
            WHERE pi.id = %s
        """, (nuevo_inventario['id'],))
        
        resultado = cur.fetchone()
        return resultado

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close()
        conn.close()

@router.get("/{id}", response_model=ProductoInventario)
async def get_inventario_by_id(id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT
                pi.*,
                p.nombre as producto_nombre,
                a.nombre as almacen_nombre
            FROM productos_inventario pi
            JOIN productos p ON pi.producto_id = p.id
            JOIN almacenes a ON pi.almacen_id = a.id
            WHERE pi.id = %s
        """, (id,))
        inventario = cur.fetchone()
        if not inventario:
            raise HTTPException(
                status_code=404, 
                detail="Producto en inventario no encontrado"
            )
        return inventario
    finally:
        cur.close()
        conn.close()

@router.post("/{inventario_id}/movimiento", response_model=ProductoInventario)
async def create_movimiento(
    inventario_id: int,
    movimiento: MovimientoAlmacenCreate
):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN")

        # Verificar inventario existente
        cur.execute("""
            SELECT cantidad, stock_minimo, stock_maximo
            FROM productos_inventario
            WHERE id = %s
        """, (inventario_id,))
        
        inventario = cur.fetchone()
        if not inventario:
            raise HTTPException(status_code=404, detail="Inventario no encontrado")

        cantidad_actual = inventario['cantidad']
        nueva_cantidad = (cantidad_actual + movimiento.cantidad 
                        if movimiento.tipo == 'ENTRADA' 
                        else cantidad_actual - movimiento.cantidad)

        if movimiento.tipo == 'SALIDA' and nueva_cantidad < 0:
            raise HTTPException(status_code=400, detail="Stock insuficiente")

        # Actualizar inventario
        cur.execute("""
            UPDATE productos_inventario
            SET cantidad = %s
            WHERE id = %s
            RETURNING *
        """, (nueva_cantidad, inventario_id))

        # Registrar movimiento
        cur.execute("""
            INSERT INTO movimientos_almacen (
                producto_inventario_id,
                tipo,
                cantidad,
                motivo,
                fecha
            ) VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            RETURNING id
        """, (
            inventario_id,
            movimiento.tipo,
            movimiento.cantidad,
            movimiento.motivo
        ))

        # Obtener inventario actualizado
        cur.execute("""
            SELECT 
                pi.*,
                p.nombre as producto_nombre,
                a.nombre as almacen_nombre
            FROM productos_inventario pi
            JOIN productos p ON pi.producto_id = p.id
            JOIN almacenes a ON pi.almacen_id = a.id
            WHERE pi.id = %s
        """, (inventario_id,))
        
        resultado = cur.fetchone()
        cur.execute("COMMIT")
        return resultado

    except Exception as e:
        cur.execute("ROLLBACK")
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close()
        conn.close()