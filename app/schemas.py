"""Modelos Pydantic de request/response para `/v1/estadisticas/ventas`.

Alimentan tanto la validación de FastAPI como la documentación Swagger
(OpenAPI) generada automáticamente. Los nombres y formatos siguen el
enunciado (CLAUDE.md §7): filtros soportados, cuerpo del POST y forma exacta
de la respuesta y de los errores.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class TipoConsulta(str, Enum):
    """Claves de filtro soportadas (CLAUDE.md §7, tabla de filtros)."""

    GENERO = "GENERO"
    EDAD = "EDAD"
    CANAL = "CANAL"
    CODIGO_PRODUCTO = "CODIGO_PRODUCTO"
    ID_PERSONA = "ID_PERSONA"
    LOCAL = "LOCAL"
    FECHA_DESDE = "FECHA_DESDE"
    FECHA_HASTA = "FECHA_HASTA"


class ConsultaFiltro(BaseModel):
    """Un filtro individual dentro de la lista `consultas` del POST."""

    consulta: TipoConsulta = Field(..., description="Clave del filtro a aplicar")
    valor: str = Field(..., description="Valor textual exacto del filtro")

    model_config = {
        "json_schema_extra": {
            "example": {"consulta": "GENERO", "valor": "Femenino"}
        }
    }


class EstadisticasVentasRequest(BaseModel):
    """Body del `POST /v1/estadisticas/ventas`."""

    consultas: List[ConsultaFiltro] = Field(
        default_factory=list,
        description=(
            "Filtros a combinar (AND). Puede venir vacía: en ese caso se "
            "calculan las estadísticas sobre el total de ventas sin filtrar."
        ),
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "consultas": [
                    {"consulta": "GENERO", "valor": "Femenino"},
                    {"consulta": "EDAD", "valor": "31"},
                    {"consulta": "CANAL", "valor": "POS"},
                ]
            }
        }
    }


class EstadisticasVentasQueryParams(BaseModel):
    """Filtros predeterminados del `GET /v1/estadisticas/ventas` (query params).

    Todos son opcionales; se combinan igual que los `consultas` del POST.
    """

    genero: Optional[str] = Field(None, description="Femenino, Masculino, Otro, No especificado")
    edad: Optional[int] = Field(None, description="Edad exacta del cliente")
    canal: Optional[str] = Field(None, description="POS, WEB, APP, CCT, APR, WPR")
    codigo_producto: Optional[str] = Field(None, description="Identificador único del producto (SKU)")
    id_persona: Optional[str] = Field(None, description="UUID del cliente")
    local: Optional[int] = Field(None, description="Número de local")
    fecha_desde: Optional[str] = Field(None, description="Fecha ISO-8601, límite inferior")
    fecha_hasta: Optional[str] = Field(None, description="Fecha ISO-8601, límite superior")


class EstadisticasVentasResponse(BaseModel):
    """Respuesta exitosa (ambos métodos), fórmulas en CLAUDE.md §7."""

    suma: float
    conteo: int
    promedio: float
    minimo: float
    maximo: float
    mediana: float
    desviacion_estandar: float

    model_config = {
        "json_schema_extra": {
            "example": {
                "suma": 1500.5,
                "conteo": 42,
                "promedio": 35.73,
                "minimo": 10.0,
                "maximo": 100.0,
                "mediana": 30.0,
                "desviacion_estandar": 25.4,
            }
        }
    }


class ErrorResponse(BaseModel):
    """Formato exacto de error para 400 y 500 (CLAUDE.md §7)."""

    detail: str
    instance: str
    status: int
    title: str
    type: str
    timestamp: str
    errorCode: str
    errorLabel: str
    method: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "detail": "Descripción detallada del error",
                "instance": "/v1/estadisticas/ventas",
                "status": 400,
                "title": "Bad Request",
                "type": "https://developer.mozilla.org/es/docs/Web/HTTP/Reference/Status/400",
                "timestamp": "2026-06-30T20:44:49.201437123Z",
                "errorCode": "VF",
                "errorLabel": "Validación Fallida",
                "method": "POST",
            }
        }
    }
