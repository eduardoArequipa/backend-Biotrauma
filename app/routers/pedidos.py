# app/routers/pedidos.py
from fastapi import APIRouter, HTTPException
from typing import List
from app.database.connection import get_db_connection
from app.models.schemas import Pedido, PedidoCreate, DetallesPedido
from datetime import datetime

router = APIRouter(
    prefix="/pedidos",
    tags=["pedidos"]
)

@router.get("/", response_model=List[Pedido])
async def get_pedidos():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Obtenemos los pedidos con la información del cliente o proveedor
        cur.execute("""
            SELECT p.*, 
                   c.nombre as cliente_nombre,
                   pr.nombre as proveedor_nombre
            FROM pedidos p
            LEFT JOIN clientes c ON p.cliente_id = c.id
            LEFT JOIN proveedores pr ON p.proveedor_id = pr.id
            ORDER BY p.fecha DESC
        """)
        pedidos = cur.fetchall()
        
        # Para cada pedido, obtenemos sus detalles
        for pedido in pedidos:
            cur.execute("""
                SELECT d.*, p.nombre as producto_nombre 
                FROM detalles_pedido d
                JOIN productos p ON d.producto_id = p.id
                WHERE d.pedido_id = %s
            """, (pedido['id'],))
            detalles = cur.fetchall()
            pedido['detalles'] = detalles
            
        return pedidos
    finally:
        cur.close()
        conn.close()

@router.post("/", response_model=Pedido)
async def create_pedido(pedido: PedidoCreate):
    print("Datos recibidos:", pedido.dict())  # Para debug
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Iniciamos una transacción
        cur.execute("BEGIN")
        
        # Ajustamos los valores de cliente_id y proveedor_id según el tipo de pedido
        if pedido.tipo_pedido == "ENTRADA":
            cliente_id = None
            proveedor_id = pedido.proveedor_id
        else:  # SALIDA
            cliente_id = pedido.cliente_id
            proveedor_id = None
        
        # Insertamos el pedido
        cur.execute("""
            INSERT INTO pedidos (
                cliente_id, proveedor_id, tipo_pedido, estado,
                subtotal, impuestos, total, notas, fecha
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (
            cliente_id,
            proveedor_id,
            pedido.tipo_pedido,
            pedido.estado,
            pedido.subtotal,
            pedido.impuestos,
            pedido.total,
            pedido.notas,
            datetime.now()
        ))
        
        nuevo_pedido = dict(cur.fetchone())
        pedido_id = nuevo_pedido['id']
        
        # Insertamos los detalles del pedido
        detalles = []
        for detalle in pedido.detalles:
            cur.execute("""
                INSERT INTO detalles_pedido (
                    pedido_id, producto_id, cantidad, precio_unitario,
                    subtotal, descuento, total
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (
                pedido_id,
                detalle.producto_id,
                detalle.cantidad,
                detalle.precio_unitario,
                detalle.subtotal,
                detalle.descuento,
                detalle.total
            ))
            detalles.append(dict(cur.fetchone()))

        # Obtenemos el nombre del cliente o proveedor según corresponda
        if cliente_id:
            cur.execute("SELECT nombre FROM clientes WHERE id = %s", (cliente_id,))
            cliente = cur.fetchone()
            if cliente:
                nuevo_pedido['cliente_nombre'] = cliente['nombre']
        
        if proveedor_id:
            cur.execute("SELECT nombre FROM proveedores WHERE id = %s", (proveedor_id,))
            proveedor = cur.fetchone()
            if proveedor:
                nuevo_pedido['proveedor_nombre'] = proveedor['nombre']
        
        # Para cada detalle, obtenemos el nombre del producto
        for detalle in detalles:
            cur.execute("SELECT nombre FROM productos WHERE id = %s", (detalle['producto_id'],))
            producto = cur.fetchone()
            if producto:
                detalle['producto_nombre'] = producto['nombre']
        
        # Confirmamos la transacción
        cur.execute("COMMIT")
        
        # Agregamos los detalles al pedido para retornar
        nuevo_pedido['detalles'] = detalles
        return nuevo_pedido
        
    except Exception as e:
        cur.execute("ROLLBACK")
        print("Error en create_pedido:", str(e))  # Para debug
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close()
        conn.close()

@router.get("/{pedido_id}", response_model=Pedido)
async def get_pedido(pedido_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Obtenemos el pedido con información del cliente/proveedor
        cur.execute("""
            SELECT p.*, 
                   c.nombre as cliente_nombre,
                   pr.nombre as proveedor_nombre
            FROM pedidos p
            LEFT JOIN clientes c ON p.cliente_id = c.id
            LEFT JOIN proveedores pr ON p.proveedor_id = pr.id
            WHERE p.id = %s
        """, (pedido_id,))
        pedido = cur.fetchone()
        
        if pedido is None:
            raise HTTPException(status_code=404, detail="Pedido no encontrado")
        
        # Obtenemos los detalles del pedido
        cur.execute("""
            SELECT d.*, p.nombre as producto_nombre 
            FROM detalles_pedido d
            JOIN productos p ON d.producto_id = p.id
            WHERE d.pedido_id = %s
        """, (pedido_id,))
        detalles = cur.fetchall()
        pedido['detalles'] = detalles
        
        return pedido
    finally:
        cur.close()
        conn.close()

@router.put("/{pedido_id}", response_model=Pedido)
async def update_pedido(pedido_id: int, pedido: PedidoCreate):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Iniciamos una transacción
        cur.execute("BEGIN")
        
        # Ajustamos los valores según el tipo de pedido
        if pedido.tipo_pedido == "ENTRADA":
            cliente_id = None
            proveedor_id = pedido.proveedor_id
        else:  # SALIDA
            cliente_id = pedido.cliente_id
            proveedor_id = None
        
        # Actualizamos el pedido
        cur.execute("""
            UPDATE pedidos
            SET cliente_id = %s,
                proveedor_id = %s,
                tipo_pedido = %s,
                estado = %s,
                subtotal = %s,
                impuestos = %s,
                total = %s,
                notas = %s
            WHERE id = %s
            RETURNING *
        """, (
            cliente_id,
            proveedor_id,
            pedido.tipo_pedido,
            pedido.estado,
            pedido.subtotal,
            pedido.impuestos,
            pedido.total,
            pedido.notas,
            pedido_id
        ))
        
        pedido_actualizado = dict(cur.fetchone())
        if pedido_actualizado is None:
            cur.execute("ROLLBACK")
            raise HTTPException(status_code=404, detail="Pedido no encontrado")
        
        # Eliminamos los detalles anteriores
        cur.execute("DELETE FROM detalles_pedido WHERE pedido_id = %s", (pedido_id,))
        
        # Insertamos los nuevos detalles
        detalles = []
        for detalle in pedido.detalles:
            cur.execute("""
                INSERT INTO detalles_pedido (
                    pedido_id, producto_id, cantidad, precio_unitario,
                    subtotal, descuento, total
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (
                pedido_id,
                detalle.producto_id,
                detalle.cantidad,
                detalle.precio_unitario,
                detalle.subtotal,
                detalle.descuento,
                detalle.total
            ))
            detalles.append(dict(cur.fetchone()))

        # Obtenemos el nombre del cliente o proveedor según corresponda
        if cliente_id:
            cur.execute("SELECT nombre FROM clientes WHERE id = %s", (cliente_id,))
            cliente = cur.fetchone()
            if cliente:
                pedido_actualizado['cliente_nombre'] = cliente['nombre']
        
        if proveedor_id:
            cur.execute("SELECT nombre FROM proveedores WHERE id = %s", (proveedor_id,))
            proveedor = cur.fetchone()
            if proveedor:
                pedido_actualizado['proveedor_nombre'] = proveedor['nombre']

        # Para cada detalle, obtenemos el nombre del producto
        for detalle in detalles:
            cur.execute("SELECT nombre FROM productos WHERE id = %s", (detalle['producto_id'],))
            producto = cur.fetchone()
            if producto:
                detalle['producto_nombre'] = producto['nombre']
        
        # Confirmamos la transacción
        cur.execute("COMMIT")
        
        # Agregamos los detalles al pedido para retornar
        pedido_actualizado['detalles'] = detalles
        return pedido_actualizado
        
    except Exception as e:
        cur.execute("ROLLBACK")
        print("Error en update_pedido:", str(e))  # Para debug
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close()
        conn.close()

@router.delete("/{pedido_id}")
async def delete_pedido(pedido_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Iniciamos una transacción
        cur.execute("BEGIN")
        
        # Eliminamos primero los detalles
        cur.execute("DELETE FROM detalles_pedido WHERE pedido_id = %s", (pedido_id,))
        
        # Luego eliminamos el pedido
        cur.execute("DELETE FROM pedidos WHERE id = %s RETURNING id", (pedido_id,))
        
        if cur.fetchone() is None:
            cur.execute("ROLLBACK")
            raise HTTPException(status_code=404, detail="Pedido no encontrado")
            
        # Confirmamos la transacción
        cur.execute("COMMIT")
        return {"message": "Pedido eliminado exitosamente"}
        
    except Exception as e:
        cur.execute("ROLLBACK")
        print("Error en delete_pedido:", str(e))  # Para debug
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close()
        conn.close()