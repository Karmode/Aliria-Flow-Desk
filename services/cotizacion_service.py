from datetime import datetime

from bson import ObjectId

from db.client import MongoDBConnection
from utils.calculos import total_cotizacion, formatear_numero_cotizacion

ESTADOS = ["Aprobada", "Rechazada", "Pendiente", "Por Cobrar", "Pagada"]


class CotizacionService:
    def __init__(self, db=None):
        self.mongo = MongoDBConnection()
        self.db = db if db is not None else self.mongo.get_database()
        self.col = self.db["cotizaciones"]
        self.clientes = self.db["clientes"]
        self.contadores = self.db["contadores"]

    @staticmethod
    def construir_query(filtros):
        filtros = filtros or {}
        query = {}
        estado = filtros.get("estado")
        if estado and estado != "Todas":
            query["estado"] = estado
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

    def clientes_dict(self):
        lista = self.clientes.find({}, {"_id": 1, "nombre": 1}).sort("nombre", 1)
        return {c["nombre"]: c["_id"] for c in lista}

    def crear(self, datos):
        fecha = datos["fecha"]
        with self.mongo.client.start_session() as session:
            with session.start_transaction():
                cliente_doc = self.clientes.find_one(
                    {"_id": datos["cliente_id"]}, session=session
                )
                direccion = cliente_doc.get("direccion", "") if cliente_doc else ""

                contador = self.contadores.find_one_and_update(
                    {"nombre": "cotizaciones", "año": fecha.year},
                    {
                        "$inc": {"secuencia": 1},
                        "$setOnInsert": {"nombre": "cotizaciones", "año": fecha.year},
                    },
                    upsert=True,
                    return_document=True,
                    session=session,
                )
                secuencia = contador["secuencia"]
                numero = formatear_numero_cotizacion(fecha.year, secuencia)

                totales = total_cotizacion(
                    datos["mano_obra"], datos["materiales_total"],
                    datos.get("descuento", 0),
                )
                doc = {
                    "cliente_id": datos["cliente_id"],
                    "nombre_cliente": datos["nombre_cliente"],
                    "direccion_cliente": direccion,
                    "fecha": fecha,
                    "titulo": datos["titulo"],
                    "descripcion": datos["descripcion"],
                    "mano_obra": float(datos["mano_obra"]),
                    "materiales_total": float(datos["materiales_total"]),
                    "subtotal": totales["subtotal"],
                    "descuento": totales["descuento"],
                    "total_general": totales["total_general"],
                    "anticipo": float(datos.get("anticipo", 0) or 0),
                    "estado": datos.get("estado", "Pendiente"),
                    "secuencia": secuencia,
                    "numero_cotizacion": numero,
                    "tiene_cuenta_cobro": False,
                    "created_at": datetime.now(),
                }
                if datos.get("materiales_lista"):
                    doc["materiales_lista"] = datos["materiales_lista"]

                self.col.insert_one(doc, session=session)
        return numero

    def actualizar(self, id_str, datos):
        totales = total_cotizacion(
            datos["mano_obra"], datos["materiales_total"], datos.get("descuento", 0)
        )
        cliente_doc = self.clientes.find_one({"_id": datos["cliente_id"]})
        direccion = cliente_doc.get("direccion", "") if cliente_doc else ""
        update = {
            "cliente_id": datos["cliente_id"],
            "nombre_cliente": datos["nombre_cliente"],
            "direccion_cliente": direccion,
            "fecha": datos["fecha"],
            "titulo": datos["titulo"],
            "descripcion": datos["descripcion"],
            "mano_obra": float(datos["mano_obra"]),
            "materiales_total": float(datos["materiales_total"]),
            "subtotal": totales["subtotal"],
            "descuento": totales["descuento"],
            "total_general": totales["total_general"],
            "anticipo": float(datos.get("anticipo", 0) or 0),
            "estado": datos["estado"],
            "materiales_lista": datos.get("materiales_lista") or None,
            "updated_at": datetime.now(),
        }
        self.col.update_one({"_id": ObjectId(id_str)}, {"$set": update})

    def cambiar_estado(self, id_str, estado):
        self.col.update_one(
            {"_id": ObjectId(id_str)},
            {"$set": {"estado": estado, "updated_at": datetime.now()}},
        )
