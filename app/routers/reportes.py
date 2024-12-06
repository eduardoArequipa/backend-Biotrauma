# app/routers/reportes.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from ..database.connection import get_db_connection
from datetime import datetime
import pandas as pd
from ..models.schemas import ReporteRequest, TipoReporte, FormatoReporte
import tempfile
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import os

router = APIRouter(
    prefix="/reportes",
    tags=["reportes"]
)
print()

@router.post("/generar")
async def generar_reporte(request: ReporteRequest):
    print(request)

    print("Datos recibidos:", request.dict())
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        data = []
        if request.tipo == TipoReporte.VENTAS:
            cur.execute("""
                SELECT 
                    p.fecha,
                    p.tipo_pedido,
                    p.estado,
                    COALESCE(c.nombre, pr.nombre) as cliente_proveedor,
                    p.subtotal,
                    p.impuestos,
                    p.total,
                    string_agg(CONCAT(prod.nombre, ' (', dp.cantidad, ')'), ', ') as productos
                FROM pedidos p
                LEFT JOIN clientes c ON p.cliente_id = c.id
                LEFT JOIN proveedores pr ON p.proveedor_id = pr.id
                LEFT JOIN detalles_pedido dp ON p.id = dp.pedido_id
                LEFT JOIN productos prod ON dp.producto_id = prod.id
                WHERE p.fecha BETWEEN '12-7-2024' AND '12-12-2024'
                GROUP BY p.id, p.fecha, p.tipo_pedido, p.estado, 
                         c.nombre, pr.nombre, p.subtotal, p.impuestos, p.total
                ORDER BY p.fecha DESC
            """, (request.fecha_inicio, request.fecha_fin))
            
            columns = ['Fecha', 'Tipo', 'Estado', 'Cliente/Proveedor', 
                      'Subtotal', 'Impuestos', 'Total', 'Productos']

        elif request.tipo == TipoReporte.INVENTARIO:
            cur.execute("""
                SELECT 
                    p.nombre as producto,
                    a.nombre as almacen,
                    pi.cantidad,
                    pi.stock_minimo,
                    pi.stock_maximo,
                    pi.precio_compra,
                    pi.precio_venta,
                    pi.ubicacion
                FROM productos_inventario pi
                JOIN productos p ON pi.producto_id = p.id
                JOIN almacenes a ON pi.almacen_id = a.id
                ORDER BY p.nombre, a.nombre
            """)
            
            columns = ['Producto', 'Almacén', 'Cantidad', 'Stock Mínimo', 
                      'Stock Máximo', 'Precio Compra', 'Precio Venta', 'Ubicación']

        elif request.tipo == TipoReporte.MOVIMIENTOS:
            cur.execute("""
                SELECT 
                    ma.fecha,
                    ma.tipo,
                    p.nombre as producto,
                    a.nombre as almacen,
                    ma.cantidad,
                    ma.motivo
                FROM movimientos_almacen ma
                JOIN productos_inventario pi ON ma.producto_inventario_id = pi.id
                JOIN productos p ON pi.producto_id = p.id
                JOIN almacenes a ON pi.almacen_id = a.id
                WHERE ma.fecha::date BETWEEN %s::date AND %s::date
                ORDER BY ma.fecha DESC
            """, (request.fecha_inicio, request.fecha_fin))
            
            columns = ['Fecha', 'Tipo', 'Producto', 'Almacén', 'Cantidad', 'Motivo']

        elif request.tipo == TipoReporte.GENERAL:
            # Resumen de Pedidos
            cur.execute("""
                SELECT 
                    COUNT(*) as total_pedidos,
                    SUM(CASE WHEN tipo_pedido = 'SALIDA' THEN total ELSE 0 END) as total_ventas,
                    SUM(CASE WHEN tipo_pedido = 'ENTRADA' THEN total ELSE 0 END) as total_compras
                FROM pedidos 
                WHERE fecha::date BETWEEN %s::date AND %s::date
            """, (request.fecha_inicio, request.fecha_fin))
            
            resumen_pedidos = cur.fetchone()

            # Productos más vendidos
            cur.execute("""
                SELECT 
                    p.nombre as producto,
                    SUM(dp.cantidad) as cantidad_vendida,
                    SUM(dp.total) as total_ventas
                FROM detalles_pedido dp
                JOIN productos p ON dp.producto_id = p.id
                JOIN pedidos ped ON dp.pedido_id = ped.id
                WHERE ped.tipo_pedido = 'SALIDA'
                AND ped.fecha::date BETWEEN %s::date AND %s::date
                GROUP BY p.nombre
                ORDER BY cantidad_vendida DESC
                LIMIT 5
            """, (request.fecha_inicio, request.fecha_fin))
            
            productos_vendidos = cur.fetchall()

            # Stock bajo
            cur.execute("""
                SELECT 
                    p.nombre as producto,
                    a.nombre as almacen,
                    pi.cantidad,
                    pi.stock_minimo
                FROM productos_inventario pi
                JOIN productos p ON pi.producto_id = p.id
                JOIN almacenes a ON pi.almacen_id = a.id
                WHERE pi.cantidad <= pi.stock_minimo
                ORDER BY p.nombre
            """)
            
            stock_bajo = cur.fetchall()

            # Crear DataFrame para el reporte general
            data = [{
                'Resumen de Operaciones': '',
                'Total Pedidos': resumen_pedidos['total_pedidos'],
                'Total Ventas': f"${resumen_pedidos['total_ventas']:.2f}",
                'Total Compras': f"${resumen_pedidos['total_compras']:.2f}",
                'Productos en Stock Bajo': len(stock_bajo)
            }]

            columns = ['Resumen de Operaciones', 'Total Pedidos', 'Total Ventas', 
                      'Total Compras', 'Productos en Stock Bajo']

        else:
            data = cur.fetchall()

        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{request.formato.lower()}') as temp_file:
            filename = temp_file.name
            
            if request.formato == FormatoReporte.EXCEL:
                df = pd.DataFrame(data)
                df.columns = columns
                df.to_excel(filename, index=False, engine='openpyxl')
                media_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            else:  # PDF
                doc = SimpleDocTemplate(filename, pagesize=letter)
                elements = []
                styles = getSampleStyleSheet()
                
                # Título
                elements.append(Paragraph(f"Reporte de {request.tipo.value}", styles['Heading1']))
                elements.append(Spacer(1, 20))
                
                if request.tipo == TipoReporte.GENERAL:
                    # Agregar secciones adicionales para el reporte general
                    elements.append(Paragraph("Top 5 Productos Más Vendidos", styles['Heading2']))
                    elements.append(Spacer(1, 10))
                    
                    productos_data = [['Producto', 'Cantidad', 'Total Ventas']]
                    for prod in productos_vendidos:
                        productos_data.append([
                            prod['producto'],
                            str(prod['cantidad_vendida']),
                            f"${prod['total_ventas']:.2f}"
                        ])
                    
                    t = Table(productos_data)
                    t.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)
                    ]))
                    elements.append(t)
                    elements.append(Spacer(1, 20))
                    
                    if stock_bajo:
                        elements.append(Paragraph("Productos con Stock Bajo", styles['Heading2']))
                        elements.append(Spacer(1, 10))
                        
                        stock_data = [['Producto', 'Almacén', 'Cantidad', 'Stock Mínimo']]
                        for stock in stock_bajo:
                            stock_data.append([
                                stock['producto'],
                                stock['almacen'],
                                str(stock['cantidad']),
                                str(stock['stock_minimo'])
                            ])
                        
                        t = Table(stock_data)
                        t.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black)
                        ]))
                        elements.append(t)
                else:
                    # Tabla normal para otros tipos de reportes
                    table_data = [columns]
                    for row in data:
                        table_data.append([str(cell) for cell in row.values()])
                    
                    t = Table(table_data)
                    t.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)
                    ]))
                    elements.append(t)
                
                doc.build(elements)
                media_type = 'application/pdf'

        return FileResponse(
            filename,
            media_type=media_type,
            filename=f'reporte_{request.tipo.value.lower()}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.{request.formato.value.lower()}'
        )

    except Exception as e:
        print("Error generando reporte:", str(e))
        raise HTTPException(status_code=500, detail=f"Error generando reporte: {str(e)}")
    finally:
        cur.close()
        conn.close()