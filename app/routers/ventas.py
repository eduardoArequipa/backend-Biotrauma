from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.database.connection import get_db_connection
from app.models.schemas import Token, DatosToken,Usuario,VentaCreate,Venta,TipoVenta
from app.auth.auth_handler import verificar_token
from decimal import Decimal
from datetime import datetime
from typing import Optional
import traceback
from psycopg2.extras import RealDictCursor
import random
import psycopg2.extras
router = APIRouter(
    prefix="/ventas",
    tags=["ventas"]
)


from fastapi import HTTPException
from decimal import Decimal
from datetime import datetime
from typing import List


@router.post("/", response_model=Venta)
async def crear_venta(venta: VentaCreate):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        if not venta.items:
            raise HTTPException(status_code=400, detail="La venta debe contener al menos un item")

        subtotal = Decimal('0')
        total_descuento = Decimal('0')
        detalles_procesados = []

        for item in venta.items:            
            cur.execute("""
                SELECT pi.cantidad, p.nombre 
                FROM productos_inventario pi
                JOIN productos p ON p.id = pi.producto_id
                WHERE pi.producto_id = %s AND pi.almacen_id = %s
            """, (item.producto_id, item.almacen_id))
            
            result = cur.fetchone()
            
            if not result:
                raise HTTPException(
                    status_code=404,
                    detail=f"No se encontró el producto {item.producto_id} en el almacén {item.almacen_id}"
                )

            stock_actual = int(result['cantidad'])
            nombre_producto = result['nombre']

            if stock_actual < item.cantidad:
                raise HTTPException(
                    status_code=400,
                    detail=f"Stock insuficiente para '{nombre_producto}'. Disponible: {stock_actual}, Solicitado: {item.cantidad}"
                )

            item_subtotal = Decimal(str(item.cantidad)) * Decimal(str(item.precio_unitario))
            item_descuento = Decimal(str(item.cantidad)) * Decimal(str(item.descuento_unitario))
            
            subtotal += item_subtotal
            total_descuento += item_descuento

            detalles_procesados.append({
                "producto_id": item.producto_id,
                "cantidad": item.cantidad,
                "precio_unitario": float(item.precio_unitario),
                "descuento_unitario": float(item.descuento_unitario),
                "subtotal": float(item_subtotal),
                "total": float(item_subtotal - item_descuento),
                "almacen_id": item.almacen_id,
                "nombre_producto": nombre_producto
            })

        impuestos = subtotal * Decimal('0.16')
        total = subtotal - total_descuento + impuestos
        numero_venta = f"V-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        # Definir estado según tipo de venta
        estado_venta = 'PENDIENTE' if venta.tipo_venta.value == 'CREDITO' else 'COMPLETADA'

        cur.execute("""
            INSERT INTO ventas (
                numero_venta, cliente_id, usuario_id, tipo_venta,
                metodo_pago, estado, subtotal, descuento,
                impuestos, total, notas
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, fecha_venta, fecha_modificacion
        """, (
            numero_venta,
            venta.cliente_id,
            venta.usuario_id,
            venta.tipo_venta.value,
            venta.metodo_pago.value,
            estado_venta,
            float(subtotal),
            float(total_descuento),
            float(impuestos),
            float(total),
            venta.notas or ''
        ))

        venta_result = cur.fetchone()
        venta_id = venta_result['id']
        fecha_venta = venta_result['fecha_venta']
        fecha_modificacion = venta_result['fecha_modificacion']

        detalles_finales = []
        for detalle in detalles_procesados:
            cur.execute("""
                INSERT INTO detalles_venta (
                    venta_id, producto_id, cantidad,
                    precio_unitario, descuento_unitario,
                    subtotal, total, almacen_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                venta_id,
                detalle["producto_id"],
                detalle["cantidad"],
                detalle["precio_unitario"],
                detalle["descuento_unitario"],
                detalle["subtotal"],
                detalle["total"],
                detalle["almacen_id"]
            ))
            
            detalle_id = cur.fetchone()['id']
            
            cur.execute("""
                UPDATE productos_inventario
                SET cantidad = cantidad - %s
                WHERE producto_id = %s AND almacen_id = %s
            """, (
                detalle["cantidad"],
                detalle["producto_id"],
                detalle["almacen_id"]
            ))

            detalles_finales.append({
                "id": detalle_id,
                "venta_id": venta_id,
                **detalle
            })

        conn.commit()

        return {
            "id": venta_id,
            "numero_venta": numero_venta,
            "fecha_venta": fecha_venta,
            "cliente_id": venta.cliente_id,
            "usuario_id": venta.usuario_id,
            "tipo_venta": venta.tipo_venta,
            "metodo_pago": venta.metodo_pago,
            "estado": estado_venta,
            "subtotal": float(subtotal),
            "descuento": float(total_descuento),
            "impuestos": float(impuestos),
            "total": float(total),
            "notas": venta.notas,
            "fecha_modificacion": fecha_modificacion,
            "detalles": detalles_finales
        }

    except Exception as e:
        conn.rollback()
        print(f"Error en crear_venta: {type(e).__name__} - {str(e)}")
        print("Traceback completo:", traceback.format_exc())
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@router.get("/{venta_id}")
async def obtener_venta(
    venta_id: int,
  #  usuario_actual: Usuario = Depends(verificar_token)
):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Obtener venta
        cur.execute("""
            SELECT v.*, c.nombre as cliente_nombre, u.nombre_usuario as vendedor
            FROM ventas v
            LEFT JOIN clientes c ON v.cliente_id = c.id
            JOIN usuarios u ON v.usuario_id = u.id
            WHERE v.id = %s
        """, (venta_id,))
        venta = cur.fetchone()
        
        if not venta:
            raise HTTPException(status_code=404, detail="Venta no encontrada")
        
        # Obtener detalles
        cur.execute("""
            SELECT dv.*, p.nombre as producto_nombre
            FROM detalles_venta dv
            JOIN productos p ON dv.producto_id = p.id
            WHERE dv.venta_id = %s
        """, (venta_id,))
        detalles = cur.fetchall()
        
        return {**venta, "detalles": detalles}
    finally:
        cur.close()
        conn.close()

@router.get("/")
async def listar_ventas(
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        query = """
            SELECT v.*, c.nombre as cliente_nombre, u.nombre_usuario as vendedor
            FROM ventas v
            LEFT JOIN clientes c ON v.cliente_id = c.id
            JOIN usuarios u ON v.usuario_id = u.id
            WHERE 1=1
        """
        params = []
        
        if fecha_inicio:
            query += " AND v.fecha_venta >= %s"
            params.append(fecha_inicio)
        if fecha_fin:
            query += " AND v.fecha_venta <= %s"
            params.append(fecha_fin)
            
        query += " ORDER BY v.fecha_venta DESC"
        
        cur.execute(query, params)
        ventas = cur.fetchall()
        return ventas
    finally:
        cur.close()
        conn.close()

@router.put("/{venta_id}/cancelar")
async def cancelar_venta(venta_id: int):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # Verificar estado actual
        cur.execute("SELECT estado FROM ventas WHERE id = %s", (venta_id,))
        venta = cur.fetchone()
        if not venta:
            raise HTTPException(status_code=404, detail="Venta no encontrada")
        if venta['estado'] == 'CANCELADA':
            raise HTTPException(status_code=400, detail="Venta ya está cancelada")

        # Obtener detalles para restaurar inventario
        cur.execute("""
            SELECT producto_id, cantidad, almacen_id
            FROM detalles_venta
            WHERE venta_id = %s
        """, (venta_id,))
        detalles = cur.fetchall()

        # Restaurar inventario
        for detalle in detalles:
            cur.execute("""
                UPDATE productos_inventario
                SET cantidad = cantidad + %s
                WHERE producto_id = %s AND almacen_id = %s
            """, (detalle['cantidad'], detalle['producto_id'], detalle['almacen_id']))

        # Cancelar venta
        cur.execute("""
            UPDATE ventas
            SET estado = 'CANCELADA',
                fecha_modificacion = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, estado, fecha_modificacion
        """, (venta_id,))
        
        venta_actualizada = cur.fetchone()
        conn.commit()

        return {
            "id": venta_actualizada['id'],
            "estado": venta_actualizada['estado'],
            "fecha_modificacion": venta_actualizada['fecha_modificacion'],
            "message": "Venta cancelada exitosamente"
        }

    except Exception as e:
        conn.rollback()
        print(f"Error al cancelar venta: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close()
        conn.close()

@router.put("/{venta_id}/actualizar")
async def actualizar_venta(
    venta_id: int,
    tipo_venta: TipoVenta
):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # Verificar que la venta existe y no está cancelada
        cur.execute("""
            SELECT estado 
            FROM ventas 
            WHERE id = %s
        """, (venta_id,))
        
        venta = cur.fetchone()
        if not venta:
            raise HTTPException(status_code=404, detail="Venta no encontrada")
        if venta['estado'] == 'CANCELADA':
            raise HTTPException(status_code=400, detail="No se puede modificar una venta cancelada")

        # Actualizar tipo de venta
        cur.execute("""
            UPDATE ventas 
            SET tipo_venta = %s,
                fecha_modificacion = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, tipo_venta, fecha_modificacion
        """, (tipo_venta.value, venta_id))

        venta_actualizada = cur.fetchone()
        conn.commit()

        return {
            "id": venta_actualizada['id'],
            "tipo_venta": venta_actualizada['tipo_venta'],
            "fecha_modificacion": venta_actualizada['fecha_modificacion'],
            "message": "Tipo de venta actualizado exitosamente"
        }

    except Exception as e:
        conn.rollback()
        print(f"Error al actualizar venta: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close()
        conn.close()