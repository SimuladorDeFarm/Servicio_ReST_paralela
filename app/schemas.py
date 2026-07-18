# Modelos Pydantic de request/response para /v1/estadisticas/ventas (alimentan Swagger).

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# Claves de filtro soportadas.
class TipoConsulta(str, Enum):
    GENERO = "GENERO"
    EDAD = "EDAD"
    CANAL = "CANAL"
    CODIGO_PRODUCTO = "CODIGO_PRODUCTO"
    ID_PERSONA = "ID_PERSONA"
    LOCAL = "LOCAL"
    FECHA_DESDE = "FECHA_DESDE"
    FECHA_HASTA = "FECHA_HASTA"


# Un filtro individual dentro de la lista `consultas` del POST.
class ConsultaFiltro(BaseModel):
    consulta: TipoConsulta = Field(..., description="Clave del filtro a aplicar")
    valor: str = Field(..., description="Valor textual exacto del filtro")

    model_config = {
        "extra": "forbid",
        "json_schema_extra": {
            "example": {"consulta": "GENERO", "valor": "Femenino"}
        },
    }


# Body del POST /v1/estadisticas/ventas.
class EstadisticasVentasRequest(BaseModel):
    consultas: List[ConsultaFiltro] = Field(
        ...,
        description="Filtros a combinar (AND). Debe contener al menos un filtro.",
    )

    @field_validator("consultas")
    @classmethod
    def consultas_no_vacia(cls, v: List[ConsultaFiltro]) -> List[ConsultaFiltro]:
        if not v:
            raise ValueError("consultas no puede ser una lista vacía")
        return v

    model_config = {
        "extra": "forbid",
        "json_schema_extra": {
            "example": {
                "consultas": [
                    {"consulta": "GENERO", "valor": "Femenino"},
                    {"consulta": "EDAD", "valor": "31"},
                    {"consulta": "CANAL", "valor": "POS"},
                ]
            }
        },
    }


# Filtros predeterminados del GET (query params), todos opcionales.
# Nombres en mayúsculas tal como los define la pauta.
class EstadisticasVentasQueryParams(BaseModel):
    GENERO: Optional[str] = Field(None, description="Femenino, Masculino, Otro, No especificado")
    EDAD: Optional[int] = Field(None, description="Edad exacta del cliente")
    CANAL: Optional[str] = Field(None, description="POS, WEB, APP, CCT, APR, WPR")
    CODIGO_PRODUCTO: Optional[str] = Field(None, description="Identificador único del producto (SKU)")
    ID_PERSONA: Optional[str] = Field(None, description="UUID del cliente")
    LOCAL: Optional[int] = Field(None, description="Número de local")
    FECHA_DESDE: Optional[str] = Field(None, description="Fecha ISO-8601, límite inferior")
    FECHA_HASTA: Optional[str] = Field(None, description="Fecha ISO-8601, límite superior")


# Respuesta exitosa (GET y POST): las 7 métricas calculadas sobre MONTO_APLICADO.
class EstadisticasVentasResponse(BaseModel):
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


# Formato exacto de error para 400 y 500.
class ErrorResponse(BaseModel):
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
