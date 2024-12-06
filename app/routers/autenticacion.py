from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
from app.database.connection import get_db_connection
from app.models.schemas import Usuario, Token, DatosToken, CrearUsuario, RolUsuario
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(
    prefix="/autenticacion",
    tags=["autenticación"]
)

# Configuración
CLAVE_SECRETA = os.getenv("CLAVE_SECRETA", "tu_clave_secreta_muy_segura")
ALGORITMO = "HS256"
MINUTOS_EXPIRACION_TOKEN = 1440  # 24 horas

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="autenticacion/login")

# Funciones de utilidad
def verificar_contrasena(contrasena_texto, contrasena_hash):
    return pwd_context.verify(contrasena_texto, contrasena_hash)

def crear_hash_contrasena(contrasena):
    return pwd_context.hash(contrasena)




def crear_token_acceso(datos: dict, tiempo_expiracion: Optional[timedelta] = None):
    datos_codificar = datos.copy()
    if not tiempo_expiracion:
        tiempo_expiracion = timedelta(minutes=MINUTOS_EXPIRACION_TOKEN)  # Usar el valor de 24 horas si no se proporciona
    expiracion = datetime.utcnow() + tiempo_expiracion
    datos_codificar.update({"exp": expiracion})
    token_jwt = jwt.encode(datos_codificar, CLAVE_SECRETA, algorithm=ALGORITMO)
    return token_jwt


async def obtener_usuario_actual(token: str = Depends(oauth2_scheme)):
    credenciales_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, CLAVE_SECRETA, algorithms=[ALGORITMO])
        nombre_usuario: str = payload.get("sub")
        if nombre_usuario is None:
            raise credenciales_exception
        datos_token = DatosToken(nombre_usuario=nombre_usuario, rol=payload.get("rol"))
    except JWTError:
        raise credenciales_exception

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM usuarios WHERE nombre_usuario = %s", (nombre_usuario,))
        usuario = cur.fetchone()
        if usuario is None:
            raise credenciales_exception
        return Usuario(**usuario)
    finally:
        cur.close()
        conn.close()

# Rutas
@router.post("/login", response_model=Token)
async def login(datos_formulario: OAuth2PasswordRequestForm = Depends()):
    print(f"Username: {datos_formulario.username}, Password: {datos_formulario.password}")  # Agrega este print
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT * FROM usuarios WHERE nombre_usuario = %s AND activo = true",
            (datos_formulario.username,)
        )
        usuario = cur.fetchone()

        if not usuario or not verificar_contrasena(datos_formulario.password, usuario["contrasena"]):
            print(f"Usuario o contraseña incorrectos: {datos_formulario.username}")  # Agrega este print
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario o contraseña incorrectos",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Actualizar último acceso
        cur.execute(
            "UPDATE usuarios SET ultimo_acceso = CURRENT_TIMESTAMP WHERE id = %s",
            (usuario["id"],)
        )
        conn.commit()

        expiracion = timedelta(minutes=MINUTOS_EXPIRACION_TOKEN)
        token_acceso = crear_token_acceso(
            datos={
                "sub": usuario["nombre_usuario"],
                "rol": usuario["rol"],
                "nombre": usuario["nombre_completo"]
            },
            tiempo_expiracion=expiracion
        )
        return {"token_acceso": token_acceso, "tipo_token": "bearer"}
    finally:
        cur.close()
        conn.close()


@router.post("/registrar", response_model=Usuario)
async def registrar(usuario: CrearUsuario, usuario_actual: Usuario = Depends(obtener_usuario_actual)):
    # Solo administrador puede crear usuarios
    if usuario_actual.rol != RolUsuario.ADMINISTRADOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para crear usuarios"
        )

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Verificar si el usuario ya existe
        cur.execute(
            "SELECT id FROM usuarios WHERE nombre_usuario = %s OR correo = %s",
            (usuario.nombre_usuario, usuario.correo)
        )
        if cur.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El usuario o correo ya existe"
            )

        # Crear nuevo usuario
        hash_contrasena = crear_hash_contrasena(usuario.contrasena)
        cur.execute("""
            INSERT INTO usuarios (
                nombre_usuario, contrasena, nombre_completo, 
                correo, rol, activo
            ) VALUES (%s, %s, %s, %s, %s, true)
            RETURNING *
        """, (
            usuario.nombre_usuario,
            hash_contrasena,
            usuario.nombre_completo,
            usuario.correo,
            usuario.rol
        ))
        conn.commit()
        nuevo_usuario = cur.fetchone()
        return Usuario(**nuevo_usuario)
    finally:
        cur.close()
        conn.close()

@router.get("/usuarios/me", response_model=Usuario)
async def leer_usuario_actual(usuario_actual: Usuario = Depends(obtener_usuario_actual)):
    return usuario_actual
