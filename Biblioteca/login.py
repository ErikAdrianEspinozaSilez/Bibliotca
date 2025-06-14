from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, select
from sqlalchemy.orm import sessionmaker
import bcrypt

# Configuración conexión MySQL
DATABASE_URL = "mysql+mysqlconnector://usuario:password@localhost:3306/tu_base"

engine = create_engine(DATABASE_URL)
metadata = MetaData()
SessionLocal = sessionmaker(bind=engine)

# Tabla usuarios (ajusta según tu BD)
users = Table(
    "users", metadata,
    Column("id", Integer, primary_key=True),
    Column("usuario", String(50), unique=True),
    Column("hashed_password", String(100)),
    Column("nombre", String(100)),
)

app = FastAPI()

class LoginRequest(BaseModel):
    usuario: str
    password: str

class LoginResponse(BaseModel):
    mensaje: str
    usuario: dict

@app.post("/login", response_model=LoginResponse)
def login(datos: LoginRequest):
    session = SessionLocal()
    try:
        query = select(users).where(users.c.usuario == datos.usuario)
        usuario_db = session.execute(query).fetchone()
        if not usuario_db:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o contraseña incorrectos")

        hashed_password = usuario_db.hashed_password.encode('utf-8')
        if not bcrypt.checkpw(datos.password.encode('utf-8'), hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o contraseña incorrectos")

        return LoginResponse(
            mensaje="Login exitoso",
            usuario={"id": usuario_db.id, "nombre": usuario_db.nombre, "usuario": usuario_db.usuario}
        )
    finally:
        session.close()
