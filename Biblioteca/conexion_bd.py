import mysql.connector
import logging
from contextlib import contextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConexionBD:
    def __init__(self):
        self.config = {
            "host": "localhost",
            "user": "root",
            "password": "",
            "database": "biblioteca",
            "port": 3306
        }

    @contextmanager
    def obtener_conexion(self):
        conexion = None
        try:
            conexion = mysql.connector.connect(**self.config)
            logger.info("Conexión a MySQL exitosa")
            yield conexion
        except mysql.connector.Error as e:
            logger.error(f"Error al conectar a MySQL: {e}")
            raise
        finally:
            if conexion and conexion.is_connected():
                conexion.close()
                logger.info("Conexión a MySQL cerrada")

    @contextmanager
    def obtener_cursor(self):
        with self.obtener_conexion() as conexion:
            cursor = conexion.cursor(dictionary=True)
            try:
                yield cursor, conexion
            finally:
                cursor.close()