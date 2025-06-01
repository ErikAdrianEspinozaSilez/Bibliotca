from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import date

# Interfaz para servicios CRUD
class IServicioCRUD(ABC):
    @abstractmethod
    def listar(self):
        pass

    @abstractmethod
    def crear(self, datos: dict):
        pass

    @abstractmethod
    def actualizar(self, id: int, datos: dict):
        pass

    @abstractmethod
    def eliminar(self, id: int):
        pass

# Interfaz para servicio de inventario
class IServicioInventario(ABC):
    @abstractmethod
    def obtener_disponibles(self):
        pass

# Interfaz para servicio de prestamos
class IServicioPrestamos(ABC):
    @abstractmethod
    def crear_prestamo(self, id_libro: int, id_usuario: int):
        pass

#Interfaz para servicio de reportes tiene su docstring para saber que hace
class IServicioReportes(ABC):
    @abstractmethod
    def generar_reporte(self, tipo_reporte: str, filtros: Optional[Dict[str, Any]] = None) -> bytes:
        """
        Genera un reporte en formato PDF segun el tipo de reporte y filtros especificados.
        
        Args:
            tipo_reporte (str): Tipo de reporte a generar ('tabla', 'grafica', 'comprobante').
            filtros (Dict[str, Any], optional): Filtros para personalizar el reporte (por ejemplo, id_libro, fecha, etc.).
        
        Returns:
            bytes: Contenido del archivo PDF generado.
        """
        pass
# Interfaz para servicio de notificaciones
class IServicioNotificaciones(ABC):
    @abstractmethod
    def enviar_notificacion(self, id_usuario: int, mensaje: str) -> dict:
        pass

    @abstractmethod
    def listar_todas(self) -> List[dict]:
        pass

    @abstractmethod
    def listar_por_usuario(self, id_usuario: int) -> List[dict]:
        pass

    @abstractmethod
    def crear(self, usuario_id: int, mensaje: str) -> dict:
        pass