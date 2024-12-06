# schemas.py
from pydantic import BaseModel,EmailStr
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
# Definir enums para los tipos y estados de pedidos
class TipoPedido(str, Enum):
    ENTRADA = "ENTRADA"
    SALIDA = "SALIDA"

class EstadoPedido(str, Enum):
    EN_PROCESO = "EN_PROCESO"
    COMPLETADO = "COMPLETADO"
    CANCELADO = "CANCELADO"
    PENDIENTE = "PENDIENTE"


class TipoCliente(str, Enum):
    REGULAR = "REGULAR"
    VIP = "VIP"
    MAYORISTA = "MAYORISTA"
    MINORISTA = "MINORISTA"
    CORPORATIVO = "CORPORATIVO"

# Modelos para Producto
class ProductoBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    precio: Decimal
    codigo_barras: Optional[str] = None
    fecha_caducidad: Optional[date] = None

class ProductoCreate(ProductoBase):
    pass

class Producto(ProductoBase):
    id: int

    class Config:
        from_attributes = True

# Modelos para Categoría
class CategoriaBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None

class CategoriaCreate(CategoriaBase):
    pass

class Categoria(CategoriaBase):
    id: int

    class Config:
        from_attributes = True

# Modelos para Proveedor
class ProveedorBase(BaseModel):
    nombre: str
    contacto: Optional[str] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None

class ProveedorCreate(ProveedorBase):
    pass

class Proveedor(ProveedorBase):
    id: int

    class Config:
        from_attributes = True

# Modelos para Almacén
class AlmacenBase(BaseModel):
    nombre: str
    ubicacion: Optional[str] = None
    capacidad: Optional[int] = None

class AlmacenCreate(AlmacenBase):
    pass

class Almacen(AlmacenBase):
    id: int

    class Config:
        from_attributes = True

# Modelos para Inventario
class ProductoInventarioBase(BaseModel):
    producto_id: int
    almacen_id: int
    cantidad: int
    ubicacion: Optional[str] = None
    precio_compra: Optional[Decimal] = None
    precio_venta: Optional[Decimal] = None
    stock_minimo: Optional[int] = None
    stock_maximo: Optional[int] = None

class ProductoInventarioCreate(ProductoInventarioBase):
    pass

class ProductoInventario(ProductoInventarioBase):
    id: int

    class Config:
        from_attributes = True

# Modelos para Pedido
class DetallesPedidoBase(BaseModel):
    producto_id: int
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal
    descuento: Optional[Decimal] = Decimal('0')
    total: Decimal
    producto_nombre: Optional[str] = None

class DetallesPedidoCreate(DetallesPedidoBase):
    pass

class DetallesPedido(DetallesPedidoBase):
    id: int
    pedido_id: int

    class Config:
        from_attributes = True

class PedidoBase(BaseModel):
    cliente_id: Optional[int] = None
    proveedor_id: Optional[int] = None
    tipo_pedido: TipoPedido
    estado: EstadoPedido = EstadoPedido.PENDIENTE
    subtotal: Decimal
    impuestos: Decimal
    total: Decimal
    notas: Optional[str] = None

class PedidoCreate(PedidoBase):
    detalles: List[DetallesPedidoCreate]

class Pedido(PedidoBase):
    id: int
    fecha: datetime
    cliente_nombre: Optional[str] = None
    proveedor_nombre: Optional[str] = None
    detalles: List[DetallesPedido] = []

    class Config:
        from_attributes = True


# Modelos para Movimientos de Almacén
class TipoMovimiento(str, Enum):
    ENTRADA = "ENTRADA"
    SALIDA = "SALIDA"
    AJUSTE = "AJUSTE"
    TRASLADO = "TRASLADO"
    
class MovimientoAlmacenBase(BaseModel):
    tipo: TipoMovimiento  # "ENTRADA", "SALIDA", "AJUSTE", "TRASLADO"
    cantidad: int
    motivo: Optional[str] = None

class MovimientoAlmacenCreate(MovimientoAlmacenBase):
    pass

class MovimientoAlmacen(MovimientoAlmacenBase):
    id: int
    fecha: datetime


    class Config:

        from_attributes = True

# Modelos para Ajustes de Inventario
class AjusteInventarioBase(BaseModel):
    producto_inventario_id: int
    tipo: str  # "INCREMENTO", "DECREMENTO", "CORRECCION"
    cantidad_anterior: int
    cantidad_nueva: int
    motivo: str

class AjusteInventarioCreate(AjusteInventarioBase):
    pass

class AjusteInventario(AjusteInventarioBase):
    id: int
    fecha: datetime

    class Config:
        from_attributes = True

# Modelos para Cliente
class ClienteBase(BaseModel):
    nombre: str
    contacto: Optional[str] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    rfc: Optional[str] = None
    tipo_cliente: Optional[TipoCliente] = TipoCliente.REGULAR

class ClienteCreate(ClienteBase):
    pass

class Cliente(ClienteBase):
    id: int

    class Config:
        from_attributes = True


# En schemas.py agregar:
# En app/models/schemas.py, agregar:

from enum import Enum

class TipoReporte(str, Enum):
    VENTAS = "VENTAS"
    INVENTARIO = "INVENTARIO"
    MOVIMIENTOS = "MOVIMIENTOS"
    GENERAL = "GENERAL"

class FormatoReporte(str, Enum):
    PDF = "PDF"
    EXCEL = "EXCEL"

class ReporteRequest(BaseModel):
    fecha_fin: str
    fecha_inicio: str
    formato: FormatoReporte
    tipo: TipoReporte

# modelo usuario


class RolUsuario(str, Enum):
    ADMINISTRADOR = "ADMINISTRADOR"
    TECNICO_EJECUTIVO = "TECNICO_EJECUTIVO"

class UsuarioBase(BaseModel):
    nombre_usuario: str
    nombre_completo: str
    correo: EmailStr
    rol: RolUsuario

class CrearUsuario(UsuarioBase):
    contrasena: str

class ActualizarUsuario(BaseModel):
    nombre_completo: Optional[str] = None
    correo: Optional[EmailStr] = None
    contrasena: Optional[str] = None

class Usuario(UsuarioBase):
    id: int
    activo: bool
    fecha_creacion: datetime
    ultimo_acceso: Optional[datetime]

    class Config:
        from_attributes = True

class Token(BaseModel):
    token_acceso: str
    tipo_token: str = "bearer"

class DatosToken(BaseModel):
    nombre_usuario: str
    rol: RolUsuario    




# En schemas.py
class TipoVenta(str, Enum):
    CONTADO = "CONTADO"
    CREDITO = "CREDITO"

class EstadoVenta(str, Enum):
    COMPLETADA = "COMPLETADA" 
    CANCELADA = "CANCELADA"
    PENDIENTE = "PENDIENTE"

class MetodoPago(str, Enum):
    EFECTIVO = "EFECTIVO"
    TARJETA = "TARJETA"
    TRANSFERENCIA = "TRANSFERENCIA"

class DetalleVentaBase(BaseModel):
    producto_id: int
    cantidad: int
    precio_unitario: Decimal
    descuento_unitario: Decimal = Decimal('0')
    almacen_id: int
    subtotal: Decimal
    total: Decimal

class DetalleVentaCreate(BaseModel):
    producto_id: int
    cantidad: int
    precio_unitario: Decimal
    descuento_unitario: Decimal = Decimal('0')
    almacen_id: int

class VentaCreate(BaseModel):
    cliente_id: Optional[int] = None
    usuario_id: int
    tipo_venta: TipoVenta
    metodo_pago: MetodoPago
    estado: EstadoVenta = EstadoVenta.COMPLETADA
    items: List[DetalleVentaCreate]
    notas: Optional[str] = None


class VentaBase(BaseModel):
    cliente_id: Optional[int]
    usuario_id: int
    tipo_venta: TipoVenta
    metodo_pago: MetodoPago
    estado: EstadoVenta = EstadoVenta.COMPLETADA
    subtotal: Decimal
    descuento: Decimal = Decimal('0')
    impuestos: Decimal
    total: Decimal
    notas: Optional[str] = None


class DetalleVenta(DetalleVentaCreate):
    id: int
    venta_id: int
    subtotal: Decimal
    total: Decimal
    producto_nombre: Optional[str] = None

    class Config:
        from_attributes = True


class DetalleVentaInput(BaseModel):
    producto_id: int
    cantidad: int
    precio_unitario: Decimal
    descuento_unitario: Decimal = Decimal('0')
    almacen_id: int





class Venta(BaseModel):
    id: int
    numero_venta: str
    fecha_venta: datetime
    cliente_id: Optional[int]
    usuario_id: int
    tipo_venta: TipoVenta
    metodo_pago: MetodoPago
    estado: EstadoVenta
    subtotal: Decimal
    descuento: Decimal
    impuestos: Decimal
    total: Decimal
    notas: Optional[str]
    fecha_modificacion: datetime
    detalles: List[DetalleVenta] = []

    class Config:
        from_attributes = True
        