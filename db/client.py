import streamlit
from pymongo import MongoClient
from threading import Lock
import os
import dotenv
dotenv.load_dotenv()

class MongoDBConnection:
    _instance = None
    _lock = Lock()  # Para asegurar que solo se cree una instancia en ambientes multihilos.

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    # Crear una nueva instancia de la conexión MongoDB
                    cls._instance = super(MongoDBConnection, cls).__new__(cls)
                    cls._instance._initialize_connection()
        return cls._instance

    def _initialize_connection(self):
        # Leer la variable de entorno MONGO_URL
        mongo_url = os.getenv('MONGO_URL')

        # Si no se encuentra la variable de entorno, intentar leerla del secreto de Streamlit Cloud
        if not mongo_url:
            try:
                mongo_url = streamlit.secrets["MONGO_URL"]
            except KeyError:
                raise ValueError("La variable de entorno MONGO_URL no está definida y no se encontró en los secretos de Streamlit Cloud.")


        # Conectar a MongoDB usando la URL
        self.client = MongoClient(mongo_url) 
        self.db = self.client['db_aliria_flow_desk']

    def get_database(self):
        return self.db