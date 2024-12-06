from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import productos, categorias, proveedores, almacenes, inventario, pedidos, movimientos, ajustes, clientes, reportes,autenticacion
# En main.py
from app.routers import ventas  # Importar el router de ventas

app = FastAPI(title="Sistema de Inventario API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(ventas.router)  # Incluir el router

app.include_router(productos.router)
app.include_router(categorias.router)
app.include_router(proveedores.router)
app.include_router(almacenes.router)
app.include_router(inventario.router)
app.include_router(pedidos.router)
app.include_router(movimientos.router)
app.include_router(ajustes.router)
app.include_router(clientes.router)  # Agregar esta línea
app.include_router(reportes.router)
app.include_router(autenticacion.router)

@app.get("/")
async def root():
    return {"message": "Sistema de Inventario API"}