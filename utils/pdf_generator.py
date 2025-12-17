from fpdf import FPDF
from datetime import datetime
import os
import streamlit as st
import pandas as pd
from PIL import Image

# --- DATOS FIJOS DEL CONTRATISTA (ALIRIA) ---
CONTRATISTA_NOMBRE = "ALIRIA CARMONA CARMONA"
CONTRATISTA_CC = "41.911.250"
CONTRATISTA_ROL = "Proveedora de Servicios de Mantenimiento"
# RUTA DE LA IMAGEN DE LA FIRMA: Definimos la ubicación en la carpeta 'assets'
FIRMA_IMAGE_PATH = "assets/firma_aliria.png" 

UPLOAD_BASE = "uploads/cuentas_cobro" 

# Estilos básicos
TITLE_FONT_SIZE = 16
HEADER_FONT_SIZE = 12
NORMAL_FONT_SIZE = 10
LINE_HEIGHT = 8
COLOR_HEADER = (200, 220, 255) # Azul claro para fondo de tablas/secciones

class PDFGenerator(FPDF):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_title("Cuenta de Cobro / Cotización")
        self.set_creator(CONTRATISTA_NOMBRE)
    
    def header(self):
        # 1. Información del Contratista (Izquierda Superior)
        self.set_xy(10, 10)
        self.set_font("Arial", "B", 10)
        self.cell(50, 5, CONTRATISTA_NOMBRE, 0, 0, "L")
        self.ln(5)
        self.set_font("Arial", "", 9)
        self.cell(50, 5, f"C.C. {CONTRATISTA_CC}", 0, 0, "L")
        self.ln(5)
        self.cell(50, 5, CONTRATISTA_ROL, 0, 0, "L")

        # 2. Título principal (Derecha Superior)
        self.set_xy(80, 10)
        self.set_font("Arial", "B", TITLE_FONT_SIZE)
        self.cell(0, 10, self.title_text, 0, 1, "R")
        self.ln(5)
        
        self.set_y(25) # Resetear posición Y después del encabezado
        self.line(10, 30, 200, 30) # Línea divisoria
        self.ln(5)


    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Página {self.page_no()}/{{nb}}", 0, 0, "C")

    def chapter_title(self, title):
        self.set_fill_color(*COLOR_HEADER)
        self.set_font("Arial", "B", HEADER_FONT_SIZE)
        self.cell(0, LINE_HEIGHT, title, 0, 1, "L", 1) 
        self.ln(2)

    def chapter_body(self, body):
        self.set_font("Arial", "", NORMAL_FONT_SIZE)
        
        try:
            from bs4 import BeautifulSoup
            import re
            
            # 1. Limpieza de entidades y preparación
            import html
            cleaned_html = html.unescape(body)
            
            # --- 2. USAMOS BEAUTIFUL SOUP PARA INYECTAR SEPARACIÓN ---
            soup = BeautifulSoup(cleaned_html, 'html.parser')

            # Asegurar que los títulos de sección (<strong>) tengan doble salto de línea antes
            for strong_tag in soup.find_all('strong'):
                # Inyectar doble salto de línea antes del strong
                strong_tag.insert_before('\n\n') 
                strong_tag.insert_after('\n') # Y un salto simple después

            # Asegurar la estructura de las listas: Iniciar con guion y salto de línea
            for ul_tag in soup.find_all('ul'):
                # Añadir un salto de línea antes y después de toda la lista
                ul_tag.insert_before('\n') 
                ul_tag.insert_after('\n')

            for li_tag in soup.find_all('li'):
                # Reemplazamos el tag li por el texto precedido por '- ' y un salto de línea
                li_tag.insert_before(f'- {li_tag.text.strip()}')
                li_tag.replace_with('\n') # Reemplazamos el tag li por un salto de línea para separar ítems


            # 3. Extraer el texto limpio (eliminando todos los tags restantes)
            # Usamos '\n' como separador para preservar los saltos inyectados
            clean_text = soup.get_text(separator='\n', strip=True)
            
            # 4. LIMPIEZA POST-EXTRACCIÓN
            
            # Normalizar los saltos de línea excesivos (mantener máximo dos para separación de párrafo)
            clean_text = re.sub(r'[\r\f\v]+', '', clean_text)
            clean_text = re.sub(r' {2,}', ' ', clean_text) # Normalizar múltiples espacios a uno solo
            
            # Reducir secuencias de 3 o más saltos de línea a dos (párrafo)
            clean_text = re.sub(r'\n{3,}', '\n\n', clean_text).strip()
            
            self.multi_cell(0, 5, clean_text)

        except Exception as e:
            # Fallback simple en caso de que Beautiful Soup falle
            self.set_text_color(255, 0, 0)
            self.multi_cell(0, 5, f"Error en la descripción: {e}")
            self.set_text_color(0, 0, 0)
            
            body = body.replace("<p>", "").replace("</p>", "\n\n").replace("<br>", "\n").strip()
            self.multi_cell(0, 5, body)
            
        self.ln(3)
        
    def add_line_item(self, label, value, bold=False):
        self.set_font("Arial", "B" if bold else "", NORMAL_FONT_SIZE)
        self.cell(40, LINE_HEIGHT, label + ":", 0, 0, "L")
        self.set_font("Arial", "", NORMAL_FONT_SIZE)
        self.cell(0, LINE_HEIGHT, str(value), 0, 1, "L")

def generate_pdf(data, doc_type="Cotización"):
    
    pdf = PDFGenerator("P", "mm", "A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.alias_nb_pages()
    
    pdf.title_text = f"{doc_type} N° {data.get('numero_cotizacion', 'N/A')}"
    pdf.add_page()
    
    # ------------------ DATOS GENERALES ------------------
    pdf.chapter_title("Detalles del Documento")
    
    fecha_dt = data.get("fecha", datetime.now())

    pdf.add_line_item("Cliente", data.get("nombre_cliente", "N/A"))
    
    if isinstance(fecha_dt, datetime):
        pdf.add_line_item("Fecha", fecha_dt.strftime("%d/%m/%Y"))
    
    pdf.add_line_item("Título", data.get("titulo", "N/A"))
    pdf.ln(5)

    # ------------------ DESCRIPCIÓN ------------------
    pdf.chapter_title("Descripción del Trabajo")
    pdf.chapter_body(data.get("descripcion", "Sin descripción."))
    pdf.ln(5)

    # ------------------ LISTADO DE MATERIALES ------------------
    pdf.chapter_title("Materiales")

    materiales_lista = data.get("materiales_lista", [])
    
    if materiales_lista:
        df = pd.DataFrame(materiales_lista)
        df = df.rename(columns={
            "unidad": "Unidad",
            "material": "Material",
            "cantidad": "Cantidad",
            "valor_unitario": "V. Unitario ($)",
            "total": "Total ($)"
        })
        
        col_widths = [20, 70, 20, 30, 30] 
        headers = df.columns.tolist()

        # Encabezado de la tabla (con fondo de color)
        pdf.set_fill_color(*COLOR_HEADER)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "B", NORMAL_FONT_SIZE)
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], LINE_HEIGHT, header, 1, 0, "C", 1) 
        pdf.ln(LINE_HEIGHT)

        # Contenido de la tabla
        pdf.set_font("Arial", "", NORMAL_FONT_SIZE)
        pdf.set_fill_color(240, 240, 240) 
        fill = False
        for index, row in df.iterrows():
            pdf.cell(col_widths[0], LINE_HEIGHT, str(row["Unidad"]), 1, 0, "L", fill)
            pdf.cell(col_widths[1], LINE_HEIGHT, str(row["Material"]), 1, 0, "L", fill)
            pdf.cell(col_widths[2], LINE_HEIGHT, f'{row["Cantidad"]:.2f}', 1, 0, "R", fill)
            pdf.cell(col_widths[3], LINE_HEIGHT, f'{row["V. Unitario ($)"]:,.0f}', 1, 0, "R", fill)
            pdf.cell(col_widths[4], LINE_HEIGHT, f'{row["Total ($)"]:,.0f}', 1, 0, "R", fill)
            pdf.ln(LINE_HEIGHT)
            fill = not fill
        pdf.ln(5)
    else:
        pdf.set_font("Arial", "I", NORMAL_FONT_SIZE)
        pdf.cell(0, LINE_HEIGHT, "No hay desglose de materiales.", 0, 1, "L")
        pdf.ln(5)

    # ------------------ TOTALES ------------------
    pdf.chapter_title("Resumen de Costos")
    
    total_key = "total" if doc_type == "Cuenta de Cobro" else "total_general"
    total_value = data.get(total_key, 0)
    
    pdf.set_font("Arial", "", NORMAL_FONT_SIZE)
    pdf.cell(140, LINE_HEIGHT, "Mano de Obra:", 0, 0, "R")
    pdf.cell(0, LINE_HEIGHT, f'${data.get("mano_obra", 0):,.0f}', 0, 1, "R")
    
    pdf.cell(140, LINE_HEIGHT, "Total Materiales:", 0, 0, "R")
    pdf.cell(0, LINE_HEIGHT, f'${data.get("materiales_total", 0):,.0f}', 0, 1, "R")
    
    pdf.ln(2)
    pdf.set_font("Arial", "B", HEADER_FONT_SIZE)
    pdf.cell(140, LINE_HEIGHT, "TOTAL GENERAL:", 'T', 0, "R")
    pdf.cell(0, LINE_HEIGHT, f'${total_value:,.0f}', 'T', 1, "R")
    pdf.ln(5)

    # ------------------ FIRMA (SOLO CUENTA DE COBRO) ------------------
    if doc_type == "Cuenta de Cobro":
        pdf.ln(10)
        
        # Intentar agregar la firma
        if os.path.exists(FIRMA_IMAGE_PATH):
            try:
                # Centrar la firma (suponiendo 40mm de ancho)
                x_center = (pdf.w - 40) / 2
                pdf.image(FIRMA_IMAGE_PATH, x=x_center, y=pdf.get_y(), w=40)
                pdf.set_y(pdf.get_y() + 25) 
            except Exception as e:
                pdf.set_text_color(255, 0, 0)
                pdf.cell(0, LINE_HEIGHT, f"ERROR: No se pudo cargar la imagen de la firma desde {FIRMA_IMAGE_PATH}", 0, 1, "C")
                pdf.set_text_color(0, 0, 0)
                pdf.ln(5)
        
        pdf.set_font("Arial", "B", NORMAL_FONT_SIZE)
        pdf.cell(0, LINE_HEIGHT, f"___________________________", 0, 1, "C")
        pdf.cell(0, LINE_HEIGHT, CONTRATISTA_NOMBRE, 0, 1, "C")
        pdf.cell(0, LINE_HEIGHT, f"C.C. {CONTRATISTA_CC}", 0, 1, "C")
        pdf.ln(5)


    # ------------------ SOPORTES (SOLO CUENTA DE COBRO) - ADJUNTOS AL PDF ------------------
    if doc_type == "Cuenta de Cobro":
        soportes = data.get("soportes", [])
        
        if soportes:
            for i, ruta in enumerate(soportes):
                nombre_archivo = os.path.basename(ruta)
                pdf.add_page()
                pdf.chapter_title(f"Soporte Adjunto N° {i+1}: {nombre_archivo}")
                
                if os.path.splitext(ruta)[1].lower() in ['.jpg', '.jpeg', '.png']:
                    try:
                        page_width = 180 
                        img = Image.open(ruta)
                        img_width, img_height = img.size
                        
                        # Cálculo de escala para ajustarse a la página (con máximo de 250mm de altura)
                        scale_factor = page_width / img_width
                        new_height = img_height * scale_factor
                        max_height = 250
                        
                        if new_height > max_height:
                            scale_factor = max_height / img_height
                            new_height = max_height
                            new_width = img_width * scale_factor
                        else:
                            new_width = page_width

                        # Centrar la imagen en la página
                        x_pos = (pdf.w - new_width) / 2
                        
                        pdf.image(ruta, x=x_pos, y=pdf.get_y() + 5, w=new_width, h=new_height)
                        pdf.ln(new_height + 10)
                        
                    except Exception as e:
                        pdf.set_text_color(255, 0, 0)
                        pdf.multi_cell(0, LINE_HEIGHT, f"ERROR al cargar soporte ({nombre_archivo}): {e}")
                        pdf.set_text_color(0, 0, 0)
                else:
                    pdf.set_font("Arial", "I", NORMAL_FONT_SIZE)
                    pdf.cell(0, LINE_HEIGHT, f"El soporte {nombre_archivo} no es una imagen válida (.jpg/.png) y no puede ser incrustado.", 0, 1, "L")
                pdf.ln(5)


    # Generar el nombre de archivo
    numero = data.get('numero_cotizacion', 'sindato')
    if doc_type == "Cotización":
        filename = f"Cotizacion_{numero}.pdf"
    else:
        filename = f"CuentaCobro_{numero}.pdf"

    pdf_bytes = bytes(pdf.output(dest="S"))
    
    return pdf_bytes, filename