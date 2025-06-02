from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import pandas as pd
import matplotlib.pyplot as plt
from abc import ABC
from typing import Optional, Dict, Any
from datetime import date
import os
import tempfile
from pathlib import Path
import logging
from typing import List
from pydantic import BaseModel
from conexion_bd import ConexionBD
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Image, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
import json
import tempfile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn.error")

# Modelos Pydantic
class Libro(BaseModel):
    id: int
    titulo: str
    autor: str
    disponible: bool

class LibroCreate(BaseModel):
    titulo: str
    autor: str
    disponible: bool

class Usuario(BaseModel):
    id: int
    nombre: str
    correo: str

class UsuarioCreate(BaseModel):
    nombre: str
    correo: str

class PrestamoCreate(BaseModel):
    id_libro: int
    id_usuario: int
    fecha_devolucion: date
    devuelto: bool = False

class PrestamoInfo(BaseModel):
    id: int
    libro: str
    usuario: str
    fecha_prestamo: date
    fecha_devolucion: date
    devuelto: bool

class ReporteConfig(BaseModel):
    tipo: str
    filtros: Optional[Dict[str, Any]] = None

class Notificacion(BaseModel):
    usuario_id: int
    mensaje: str

class TipoReporteCreate(BaseModel):
    descripcion: str

app = FastAPI()

# Configuración CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Archivos estáticos
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_path, html=True), name="static")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response: {response.status_code}")
    return response

@app.get("/")
async def read_root():
    return FileResponse("static/index.html")

# Instancia de ConexionBD
bd = ConexionBD()

# ---------------------------
# Implementación de Servicios
# ---------------------------

class ServicioCRUD:
    def __init__(self, tabla: str):
        self.tabla = tabla
        self.bd = bd

    def listar(self) -> List[dict]:
        with self.bd.obtener_cursor() as (cursor, _):
            cursor.execute(f"SELECT * FROM {self.tabla}")
            result = cursor.fetchall()
            if not result:
                return []
            if self.tabla == "libro":
                for row in result:
                    if 'disponible' in row:
                        row['disponible'] = bool(row['disponible'])
            return result

    def crear(self, datos: dict) -> dict:
        with self.bd.obtener_cursor() as (cursor, conexion):
            columnas = ", ".join(datos.keys())
            marcadores = ", ".join(["%s"] * len(datos))
            valores = tuple(datos.values())
            cursor.execute(f"INSERT INTO {self.tabla} ({columnas}) VALUES ({marcadores})", valores)
            conexion.commit()
            return {"mensaje": f"{self.tabla} creado exitosamente", "id": cursor.lastrowid}

    def actualizar(self, id: int, datos: dict) -> dict:
        with self.bd.obtener_cursor() as (cursor, conexion):
            set_clause = ", ".join([f"{k} = %s" for k in datos.keys()])
            valores = list(datos.values()) + [id]
            cursor.execute(f"UPDATE {self.tabla} SET {set_clause} WHERE id = %s", valores)
            conexion.commit()
            return {"mensaje": f"{self.tabla} actualizado"}

    def eliminar(self, id: int) -> dict:
        with self.bd.obtener_cursor() as (cursor, conexion):
            cursor.execute(f"DELETE FROM {self.tabla} WHERE id = %s", (id,))
            conexion.commit()
            return {"mensaje": f"{self.tabla} eliminado"}

class ServicioInventario:
    def __init__(self):
        self.bd = bd

    def obtener_disponibles(self) -> List[dict]:
        with self.bd.obtener_cursor() as (cursor, _):
            cursor.execute("SELECT id, titulo, autor, disponible FROM libro WHERE disponible = 1 AND disponible IS NOT NULL")
            result = cursor.fetchall()
            if not result:
                return []
            for row in result:
                if 'disponible' in row:
                    row['disponible'] = bool(row['disponible'])
            return result

class ServicioPrestamos:
    def __init__(self):
        self.bd = bd

def crear_prestamo(prestamo: PrestamoCreate):
    
    servicio_prestamos.crear(prestamo)
    
    
    servicio_libros.bd.ejecutar(
        "UPDATE libro SET disponible = %s WHERE id = %s",
        (False, prestamo.id_libro)
    )
    
    return {"mensaje": "Préstamo registrado y libro marcado como no disponible"}

    def listar_prestamos(self) -> List[dict]:
        with self.bd.obtener_cursor() as (cursor, _):
            cursor.execute("""
                SELECT p.id, l.titulo as libro, u.nombre as usuario, 
                       p.fecha_prestamo, p.fecha_devolucion, p.devuelto
                FROM prestamo p
                JOIN libro l ON p.id_libro = l.id
                JOIN usuario u ON p.id_usuario = u.id
            """)
            result = cursor.fetchall()
            if not result:
                return []
            for row in result:
                if 'devuelto' in row:
                    row['devuelto'] = bool(row['devuelto'])
            return result

class ServicioReportes(ABC):
    def __init__(self):
        self.bd = ConexionBD()
        self.template_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.tipos_reporte = self._cargar_tipos_reporte()

    def _cargar_tipos_reporte(self) -> Dict[str, int]:
        with self.bd.obtener_cursor() as (cursor, _):
            cursor.execute("SELECT id, descripcion FROM tipo_reporte")
            tipos = cursor.fetchall()
        return {tipo["descripcion"].lower(): tipo["id"] for tipo in tipos}

    def listar_tipos_reporte(self) -> List[Dict[str, Any]]:
        with self.bd.obtener_cursor() as (cursor, _):
            cursor.execute("SELECT id, descripcion FROM tipo_reporte")
            return cursor.fetchall()
        
    def crear_tipo_reporte(self, descripcion: str) -> int:
        descripcion = descripcion.lower()
        with self.bd.obtener_cursor() as (cursor, conexion):
            cursor.execute("SELECT id FROM tipo_reporte WHERE LOWER(descripcion) = %s", (descripcion,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail=f"El tipo de reporte '{descripcion}' ya existe")
            cursor.execute("INSERT INTO tipo_reporte (descripcion) VALUES (%s)", (descripcion,))
            conexion.commit()
            tipo_id = cursor.lastrowid
        self.tipos_reporte = self._cargar_tipos_reporte()
        return tipo_id

    def crear_reporte(self, tipo_reporte: str) -> int:
        tipo_reporte = tipo_reporte.lower()
        if tipo_reporte not in self.tipos_reporte:
            raise HTTPException(status_code=400, detail=f"Tipo de reporte no válido: {tipo_reporte}")
        tipo_reporte_id = self.tipos_reporte[tipo_reporte]
        with self.bd.obtener_cursor() as (cursor, conexion):
            cursor.execute(
                "INSERT INTO reporte (fecha, tipo_reporte) VALUES (CURRENT_TIMESTAMP, %s)",
                (tipo_reporte_id,)
            )
            conexion.commit()
            return cursor.lastrowid

    def listar_reportes(self) -> List[Dict[str, Any]]:
        with self.bd.obtener_cursor() as (cursor, _):
            cursor.execute("""
                SELECT r.id, r.fecha, tr.descripcion AS tipo_descripcion
                FROM reporte r
                JOIN tipo_reporte tr ON r.tipo_reporte = tr.id
                ORDER BY r.fecha DESC
            """)
            result = cursor.fetchall()
        return result

    def generar_reporte(self, tipo: str, filtros: Optional[Dict[str, Any]] = None) -> bytes:
        reporte_id = self.crear_reporte(tipo)
        print(f"Reporte registrado con ID: {reporte_id}")  # Depuración
        config = ReporteConfig(tipo=tipo.lower(), filtros=filtros)
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []

        styles = getSampleStyleSheet()
        title_style = styles['Heading1']
        normal_style = styles['Normal']

        if config.tipo == "tabla":
            self._generar_tabla_reporte(elements, config.filtros, title_style, normal_style)
        elif config.tipo == "grafico":
            self._generar_grafica_reporte(elements, config.filtros, title_style, normal_style)
        elif config.tipo == "comprobante":
            self._generar_comprobante_reporte(elements, config.filtros, title_style, normal_style)
        else:
            raise HTTPException(status_code=400, detail="Tipo de reporte no soportado")

        doc.build(elements)
        pdf_data = buffer.getvalue()
        buffer.close()
        return pdf_data

    def _generar_tabla_reporte(self, elements: List, filtros: Optional[Dict[str, Any]], title_style, normal_style) -> None:
        elements.append(Paragraph("Reporte de Tabla", title_style))
        elements.append(Spacer(1, 0.2 * inch))

        with self.bd.obtener_cursor() as (cursor, _):
            tabla = filtros.get('tabla', 'prestamos') if filtros else 'prestamos'
            if tabla == 'libros':
                cursor.execute("SELECT id, titulo, autor, disponible FROM libro")
                result = cursor.fetchall()
                data = [["ID", "Título", "Autor", "Disponible"]]
                for row in result:
                    disponible = "Sí" if row["disponible"] else "No"
                    data.append([str(row["id"]), row["titulo"], row["autor"], disponible])
            elif tabla == 'usuarios':
                cursor.execute("SELECT id, nombre, correo FROM usuario")
                result = cursor.fetchall()
                data = [["ID", "Nombre", "Correo"]]
                for row in result:
                    data.append([str(row["id"]), row["nombre"], row["correo"]])
            elif tabla == 'disponibles':
                cursor.execute("SELECT id, titulo, autor FROM libro WHERE disponible = 1 AND disponible IS NOT NULL")
                result = cursor.fetchall()
                data = [["ID", "Título", "Autor"]]
                for row in result:
                    data.append([str(row["id"]), row["titulo"], row["autor"]])
            elif tabla == 'prestamos':
                cursor.execute("""
                    SELECT p.id, l.titulo as libro, u.nombre as usuario, 
                        p.fecha_prestamo, p.fecha_devolucion, p.devuelto
                    FROM prestamo p
                    JOIN libro l ON p.id_libro = l.id
                    JOIN usuario u ON p.id_usuario = u.id
                """)
                result = cursor.fetchall()
                data = [["ID", "Libro", "Usuario", "Fecha Préstamo", "Fecha Devolución", "Devuelto"]]
                for row in result:
                    devuelto = "Sí" if row["devuelto"] else "No"
                    fecha_devolucion = row["fecha_devolucion"] or "N/A"
                    data.append([str(row["id"]), row["libro"], row["usuario"], str(row["fecha_prestamo"]), str(fecha_devolucion), devuelto])
            elif tabla == 'reportes':
                cursor.execute("""
                    SELECT r.id, r.fecha, tr.descripcion AS tipo_descripcion
                    FROM reporte r
                    JOIN tipo_reporte tr ON r.tipo_reporte = tr.id
                """)
                result = cursor.fetchall()
                data = [["ID", "Fecha", "Tipo"]]
                for row in result:
                    data.append([str(row["id"]), str(row["fecha"]), row["tipo_descripcion"]])
            else:
                raise HTTPException(status_code=400, detail=f"Tabla no soportada: {tabla}")

            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(table)

    def _generar_grafica_reporte(self, elements: List, filtros: Optional[Dict[str, Any]], title_style, normal_style) -> None:
        elements.append(Paragraph("Reporte de Análisis de Préstamos", title_style))
        elements.append(Spacer(1, 0.2 * inch))

        with self.bd.obtener_cursor() as (cursor, _):
            cursor.execute("""
                SELECT l.titulo, COUNT(p.id) as prestamos
                FROM prestamo p
                JOIN libro l ON p.id_libro = l.id
                GROUP BY p.id_libro, l.titulo
                ORDER BY prestamos DESC
                LIMIT 5
            """)
            libros_data = cursor.fetchall()

            cursor.execute("""
                SELECT DATE_FORMAT(p.fecha_prestamo, '%Y-%m') as mes, COUNT(p.id) as prestamos
                FROM prestamo p
                GROUP BY mes
                ORDER BY mes
            """)
            meses_data = cursor.fetchall()

        # Generar el gráfico
        plt.figure(figsize=(8, 5))
        plt.subplot(2, 1, 1)
        plt.bar([row["titulo"] for row in libros_data], [row["prestamos"] for row in libros_data])
        plt.title("Top 5 Libros Más Prestados")
        plt.xticks(rotation=45)
        plt.xlabel("Título del Libro")
        plt.ylabel("Número de Préstamos")

        plt.subplot(2, 1, 2)
        plt.plot([row["mes"] for row in meses_data], [row["prestamos"] for row in meses_data], marker='o')
        plt.title("Préstamos por Mes")
        plt.xlabel("Mes")
        plt.ylabel("Número de Préstamos")
        plt.xticks(rotation=45)

        plt.tight_layout()

        # En lugar de guardar en un archivo, guardar en un buffer de memoria
        import io
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches="tight")
        buf.seek(0)  # Volver al inicio del buffer
        plt.close()

        # Usar el buffer directamente con Image
        try:
            img = Image(buf, width=6*inch, height=4*inch)
            elements.append(img)
        except Exception as e:
            # Mantener el error más informativo
            import traceback
            error_details = traceback.format_exc()
            raise HTTPException(status_code=500, detail=f"Error al añadir la imagen al PDF: {str(e)}\n{error_details}")

    def _generar_comprobante_reporte(self, elements: List, filtros: Optional[Dict[str, Any]], title_style, normal_style) -> None:
        if not filtros or "id_prestamo" not in filtros:
            raise HTTPException(status_code=400, detail="Se requiere id_prestamo en los filtros")

        id_prestamo = filtros["id_prestamo"]
        with self.bd.obtener_cursor() as (cursor, _):
            cursor.execute("""
                SELECT p.id, l.titulo, l.autor, u.nombre, p.fecha_prestamo, p.fecha_devolucion
                FROM prestamo p
                JOIN libro l ON p.id_libro = l.id
                JOIN usuario u ON p.id_usuario = u.id
                WHERE p.id = %s
            """, (id_prestamo,))
            prestamo = cursor.fetchone()

        if not prestamo:
            raise HTTPException(status_code=404, detail="Préstamo no encontrado")

        elements.append(Paragraph("Comprobante de Préstamo", title_style))
        elements.append(Spacer(1, 0.2 * inch))
        elements.append(Paragraph(f"ID Préstamo: {prestamo['id']}", normal_style))
        elements.append(Paragraph(f"Libro: {prestamo['titulo']}", normal_style))
        elements.append(Paragraph(f"Autor: {prestamo['autor']}", normal_style))
        elements.append(Paragraph(f"Usuario: {prestamo['nombre']}", normal_style))
        elements.append(Paragraph(f"Fecha de Préstamo: {prestamo['fecha_prestamo']}", normal_style))
        elements.append(Paragraph(f"Fecha de Devolución: {prestamo['fecha_devolucion'] or 'N/A'}", normal_style))

# Servicio de notificaciones
class ServicioNotificaciones(ABC):
        def __init__(self):
            self.bd = bd

        def enviar_notificacion(self, id_usuario: int, mensaje: str) -> dict:
            return {
                "id_usuario": id_usuario,
                "mensaje": mensaje
        }

        def crear(self, usuario_id: int, mensaje: str) -> dict:
            with self.bd.obtener_cursor() as (cursor, conexion):
                cursor.execute("SELECT id FROM usuario WHERE id = %s", (usuario_id,))
                if not cursor.fetchone():
                    raise HTTPException(status_code=404, detail="Usuario no encontrado")
                
                cursor.execute(
                    "INSERT INTO notificaciones (usuario_id, mensaje, fecha) VALUES (%s, %s, CURRENT_TIMESTAMP)",
                    (usuario_id, mensaje)
                )
                conexion.commit()
                return {"mensaje": "Notificación creada", "id": cursor.lastrowid}

        def listar_todas(self) -> List[dict]:
            with self.bd.obtener_cursor() as (cursor, _):
                cursor.execute("""
                    SELECT n.id, n.usuario_id, u.nombre AS usuario, n.mensaje, n.fecha
                    FROM notificaciones n
                    JOIN usuario u ON n.usuario_id = u.id
                    ORDER BY n.fecha DESC
                """)
                return cursor.fetchall()

        def listar_por_usuario(self, id_usuario: int) -> List[dict]:
            with self.bd.obtener_cursor() as (cursor, _):
                cursor.execute("SELECT id FROM usuario WHERE id = %s", (id_usuario,))
                if not cursor.fetchone():
                    raise HTTPException(status_code=404, detail="Usuario no encontrado")
                
                cursor.execute("""
                    SELECT n.id, n.usuario_id, u.nombre AS usuario, n.mensaje, n.fecha
                    FROM notificaciones n
                    JOIN usuario u ON n.usuario_id = u.id
                    WHERE n.usuario_id = %s
                    ORDER BY n.fecha DESC
                """, (id_usuario,))
                return cursor.fetchall()

# Instancias de servicios
servicio_libros = ServicioCRUD("libro")
servicio_usuarios = ServicioCRUD("usuario")
servicio_inventario = ServicioInventario()
servicio_prestamos = ServicioPrestamos()
servicio_notificaciones = ServicioNotificaciones()
servicio_reportes = ServicioReportes()

# -------------------
# Endpoints API REST
# -------------------

# Libros
@app.get("/libros/", response_model=List[Libro])
def listar_libros():
    return servicio_libros.listar()

@app.post("/libros/")
def crear_libro(libro: LibroCreate):
    return servicio_libros.crear({
        "titulo": libro.titulo,
        "autor": libro.autor,
        "disponible": libro.disponible
    })

@app.put("/libros/{id}")
def editar_libro(id: int, libro: LibroCreate):
    if not libro.titulo.strip() or not libro.autor.strip():
        raise HTTPException(status_code=400, detail="Título y autor no pueden estar vacíos.")
    
    servicio_libros.bd.ejecutar(
        "UPDATE libro SET titulo = %s, autor = %s WHERE id = %s",
        (libro.titulo.strip(), libro.autor.strip(), id)
    )
    
    return {"mensaje": "Libro actualizado correctamente"}
@app.delete("/libros/{id}")
def eliminar_libro(id: int):
    return servicio_libros.eliminar(id)

# Usuarios
@app.get("/usuarios/", response_model=List[Usuario])
def listar_usuarios():
    return servicio_usuarios.listar()

@app.post("/usuarios/")
def crear_usuario(usuario: UsuarioCreate):
    return servicio_usuarios.crear({
        "nombre": usuario.nombre,
        "correo": usuario.correo
    })
@app.put("/usuarios/{id}")
def actualizar_usuario(id: int, usuario: UsuarioCreate):
    usuarios = servicio_usuarios.listar()
    if not any(u["id"] == id for u in usuarios):
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    servicio_usuarios.bd.ejecutar(
        "UPDATE usuario SET nombre = %s, correo = %s WHERE id = %s",
        (usuario.nombre, usuario.correo, id)
    )
    return {"mensaje": "Usuario actualizado correctamente"}

@app.delete("/usuarios/{id}")
def eliminar_usuario(id: int):
    usuarios = servicio_usuarios.listar()
    if not any(u["id"] == id for u in usuarios):
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    servicio_usuarios.bd.ejecutar("DELETE FROM usuario WHERE id = %s", (id,))
    return {"mensaje": "Usuario eliminado correctamente"}

# Inventario
@app.get("/inventario/disponibles/", response_model=List[Libro])
def obtener_disponibles():
    return servicio_inventario.obtener_disponibles()

# Préstamos
@app.post("/prestamos/")
def crear_prestamo(prestamo: PrestamoCreate):
    return servicio_prestamos.crear_prestamo(prestamo)

@app.get("/prestamos/", response_model=List[PrestamoInfo])
def listar_prestamos():
    return servicio_prestamos.listar_prestamos()

# Reportes
@app.get("/reportes/", response_class=FileResponse)
async def generar_reporte(tipo: str, filtros: Optional[str] = None):
    try:
        filtros_dict = None
        if filtros:
            filtros_dict = json.loads(filtros)
        
        pdf_data = servicio_reportes.generar_reporte(tipo, filtros_dict)
        
        # Determinar el nombre del archivo según el tipo de reporte
        if tipo.lower() == "tabla":
            tabla = filtros_dict.get('tabla', 'prestamos') if filtros_dict else 'prestamos'
            filename = f"reporte_{tabla}.pdf"
        elif tipo.lower() == "grafico":
            parametro = filtros_dict.get('parametro', 'libro_mas_solicitado') if filtros_dict else 'libro_mas_solicitado'
            filename = f"{parametro}.pdf"
        elif tipo.lower() == "comprobante":
            # Generar un número incremental simple para el nombre (sin guardar en BD)
            with servicio_reportes.bd.obtener_cursor() as (cursor, _):
                cursor.execute("SELECT COUNT(*) as count FROM reporte WHERE tipo_reporte = (SELECT id FROM tipo_reporte WHERE LOWER(descripcion) = 'comprobante')")
                count = cursor.fetchone()['count'] + 1
            filename = f"comprobante_{count}.pdf"
        else:
            filename = "reporte.pdf"

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
            temp_pdf.write(pdf_data)
            response = FileResponse(temp_pdf.name, filename=filename, media_type="application/pdf")
            response.headers["Content-Disposition"] = f"attachment; filename={filename}"
            return response
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar reporte: {str(e)}")

@app.get("/reportes/listar/", response_model=List[Dict[str, Any]])
async def listar_reportes():
    return servicio_reportes.listar_reportes()

@app.get("/tipos_reporte/", response_model=List[Dict[str, Any]])
async def listar_tipos_reporte():
    return servicio_reportes.listar_tipos_reporte()

@app.post("/tipos_reporte/", response_model=int)
async def crear_tipo_reporte(tipo: TipoReporteCreate):
    return servicio_reportes.crear_tipo_reporte(tipo.descripcion)

# Notificaciones
@app.post("/notificaciones/")
def crear_notificacion(notificacion: Notificacion):
    return servicio_notificaciones.crear(notificacion.usuario_id, notificacion.mensaje)

@app.get("/notificaciones/", response_model=List[Dict[str, Any]])
def listar_notificaciones():
    return servicio_notificaciones.listar_todas()

@app.get("/notificaciones/usuario/{id_usuario}", response_model=List[Dict[str, Any]])
def listar_notificaciones_usuario(id_usuario: int):
    return servicio_notificaciones.listar_por_usuario(id_usuario)


@app.post("/notificaciones/enviar/")
def enviar_notificacion(notificacion: Notificacion):
    return servicio_notificaciones.enviar_notificacion(notificacion.usuario_id, notificacion.mensaje)