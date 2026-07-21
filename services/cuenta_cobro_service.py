import os
from datetime import datetime

from bson import ObjectId

from db.client import MongoDBConnection
from utils.calculos import total_cuenta_cobro

UPLOAD_BASE = "uploads/cuentas_cobro"


class CuentaCobroService:
    def __init__(self, db=None):
        self.mongo = MongoDBConnection()
        self.db = db if db is not None else self.mongo.get_database()
        self.col = self.db["cuentas_cobro"]
        self.cotizaciones = self.db["cotizaciones"]

    @staticmethod
    def construir_query(filtros):
        filtros = filtros or {}
        query = {}
        anio = filtros.get("anio")
        if anio:
            query["fecha"] = {
                "$gte": datetime(anio, 1, 1),
                "$lte": datetime(anio, 12, 31, 23, 59, 59),
            }
        buscar = (filtros.get("buscar") or "").strip()
        if buscar:
            query["$or"] = [
                {"nombre_cliente": {"$regex": buscar, "$options": "i"}},
                {"numero_cotizacion": {"$regex": buscar, "$options": "i"}},
            ]
        return query

    def listar(self, filtros=None):
        return list(
            self.col.find(self.construir_query(filtros)).sort("numero_cotizacion", -1)
        )

    def buscar_por_id(self, id_str):
        return self.col.find_one({"_id": ObjectId(id_str)})

    def guardar_soportes(self, numero_cotizacion, archivos):
        ruta = os.path.join(UPLOAD_BASE, f"cc_{numero_cotizacion}")
        os.makedirs(ruta, exist_ok=True)
        rutas = []
        for f in (archivos or []):
            path = os.path.join(ruta, f.name)
            with open(path, "wb") as out:
                out.write(f.read())
            rutas.append(path)
        return rutas

    def _doc_desde_datos(self, datos):
        totales = total_cuenta_cobro(
            datos["mano_obra"], datos["materiales_total"],
            anticipo=datos.get("anticipo", 0),
            descuento_cotizacion=datos.get("descuento_cotizacion", 0),
            descuento_adicional=datos.get("descuento_adicional", 0),
        )
        return {
            "fecha": datos["fecha"],
            "titulo": datos["titulo"],
            "descripcion": datos["descripcion"],
            "mano_obra": int(datos["mano_obra"]),
            "materiales_total": float(datos["materiales_total"]),
            "anticipo": float(datos.get("anticipo", 0) or 0),
            "descuento_cotizacion": float(datos.get("descuento_cotizacion", 0) or 0),
            "descuento_adicional": float(datos.get("descuento_adicional", 0) or 0),
            "descuento_total": totales["descuento_total"],
            "total_sin_descuentos": totales["total_sin_descuentos"],
            "total": totales["total"],
        }, totales

    def crear_desde_cotizacion(self, cotizacion, datos, rutas_soportes):
        base, _ = self._doc_desde_datos(datos)
        doc = {
            "cotizacion_id": cotizacion["_id"],
            "numero_cotizacion": cotizacion["numero_cotizacion"],
            "cliente_id": cotizacion["cliente_id"],
            "nombre_cliente": cotizacion["nombre_cliente"],
            "direccion_cliente": cotizacion.get("direccion_cliente", ""),
            "anticipo_original": float(cotizacion.get("anticipo", 0) or 0),
            "descuento_cotizacion_original": float(cotizacion.get("descuento", 0) or 0),
            "soportes": rutas_soportes,
            "created_at": datetime.now(),
            **base,
        }
        if datos.get("materiales_lista"):
            doc["materiales_lista"] = datos["materiales_lista"]

        result = self.col.insert_one(doc)
        self.cotizaciones.update_one(
            {"_id": cotizacion["_id"]},
            {"$set": {"tiene_cuenta_cobro": True, "cuenta_cobro_id": result.inserted_id}},
        )
        return result.inserted_id

    def actualizar(self, id_str, datos):
        base, _ = self._doc_desde_datos(datos)
        base["materiales_lista"] = datos.get("materiales_lista") or None
        base["updated_at"] = datetime.now()
        self.col.update_one({"_id": ObjectId(id_str)}, {"$set": base})
