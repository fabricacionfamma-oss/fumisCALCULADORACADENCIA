¡Me parece una idea genial! Agregar un cuadro resumen con la Cadencia Neta Total (Piezas totales ÷ Horas totales) al principio del reporte le da mucho más impacto a nivel gerencial, porque te permite ver la eficiencia real de la máquina de un solo vistazo.

Hice los siguientes ajustes en el código:

Agregué los cálculos para sumar todas las piezas producidas y todas las horas trabajadas por máquina.

Agregué una nueva tabla al inicio del PDF (ahora es el punto 1) que muestra la Máquina, Total Piezas, Total Horas y la Cadencia (Pzs/h).

Añadí una fila resaltada al final de la tabla con el TOTAL GLOBAL, sumando todo para sacar la cadencia promedio neta de todas las máquinas seleccionadas juntas.

Desplacé la numeración de los demás puntos (el rendimiento general pasó a ser el 2, etc.).

Aquí tienes el código completo y actualizado. Cópialo y reemplázalo en tu archivo app.py:

Python
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from fpdf import FPDF
from datetime import datetime

# ==========================================
# 0. DICCIONARIO DE MÁQUINAS FUMISCOR
# ==========================================
MAQUINAS_MAP = {
    # === ESTAMPADO ===
    "P-023": "PRENSAS PROGRESIVAS", "P-024": "PRENSAS PROGRESIVAS", "P-025": "PRENSAS PROGRESIVAS",
    "P-026": "PRENSAS PROGRESIVAS GRANDES", "P-027": "PRENSAS PROGRESIVAS GRANDES",
    "P-028": "PRENSAS PROGRESIVAS GRANDES", "P-029": "PRENSAS PROGRESIVAS GRANDES", "P-030": "PRENSAS PROGRESIVAS GRANDES",
    "BAL-002": "BALANCIN", "BAL-003": "BALANCIN", "BAL-005": "BALANCIN", "BAL-006": "BALANCIN",
    "BAL-007": "BALANCIN", "BAL-008": "BALANCIN", "BAL-009": "BALANCIN", "BAL-010": "BALANCIN",
    "BAL-011": "BALANCIN", "BAL-012": "BALANCIN", "BAL-013": "BALANCIN", "BAL-014": "BALANCIN", "BAL-015": "BALANCIN",
    "P-011": "HIDRAULICAS", "P-016": "HIDRAULICAS", "P-017": "HIDRAULICAS", "P-018": "HIDRAULICAS",
    "P-012": "HIDRAULICAS", "P-013": "HIDRAULICAS", "P-014": "HIDRAULICAS",
    "P-015": "MECANICAS", "P-019": "MECANICAS", "P-020": "MECANICAS", "P-021": "MECANICAS", "P-022": "MECANICAS",
    "GOF01": "Gofradora",
    # === SOLDADURA ===
    "SOP-003": "PRP", "SOP-005": "PRP", "SOP-008": "PRP", "SOP-009": "PRP", "SOP-010": "PRP",
    "SOP-017": "PRP", "SOP-018": "PRP", "SOP-019": "PRP", "SOP-020": "PRP", "SOP-022": "PRP",
    "SOP-023": "PRP", "SOP-024": "PRP", "SOP-025": "PRP",
    "SOP-026": "PRP", "SOP-027": "PRP", "SOP-028": "PRP", "SOP-029": "PRP", "SOP-030": "PRP",
    "DOB-001": "DOBLADORA", "DOB-002": "DOBLADORA", "DOB-003": "DOBLADORA", "DOB-004": "DOBLADORA",
    "DOB-005": "DOBLADORA", "DOB-006": "DOBLADORA",
    "DOB-007": "DOBLADORA", "DOB-008": "DOBLADORA", "DOB-009": "DOBLADORA", "DOB-010": "DOBLADORA",
    "Cel1 - Rob13 - RUEDA AUX.": "CELDA SOLDADURA", "Cel2 - Rob1 - ALMOHADON": "CELDA SOLDADURA",
    "Cel3 - Rob14 - HANGERS": "CELDA SOLDADURA", "Cel4 - Rob6 - DOB TORCHA": "CELDA SOLDADURA",
    "Cel5 - Rob4 - Respaldo 60/40": "CELDA SOLDADURA", "HANGERS NISSAN": "CELDA SOLDADURA",
    "Celda 01 Fumis": "CELDA SOLDADURA RENAULT", "Celda 02 Fumis": "CELDA SOLDADURA RENAULT",
    "Celda 03 Fumis": "CELDA SOLDADURA RENAULT", "Celda 04 Fumis": "CELDA SOLDADURA RENAULT",
    "Celda 05 Fumis": "CELDA SOLDADURA RENAULT", "Celda 06 Fumis": "CELDA SOLDADURA RENAULT",
    "Celda 07 Fumis": "CELDA SOLDADURA RENAULT", "Celda 08 Fumis": "CELDA SOLDADURA RENAULT",
    "Celda 09 Fumis": "CELDA SOLDADURA RENAULT", "Celda 10 Fumis": "CELDA SOLDADURA RENAULT",
    "Celda 11 Fumis": "CELDA SOLDADURA RENAULT", "Celda 12 Fumis": "CELDA SOLDADURA RENAULT",
    "Celda 13 Fumis": "CELDA SOLDADURA RENAULT", "Celda 14 Fumis": "CELDA SOLDADURA RENAULT",
    "Celda 15 Fumis": "CELDA SOLDADURA RENAULT"
}

# ==========================================
# CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(page_title="Generador de Reportes de Producción", layout="centered")
st.title("📊 Generador de Reporte Ejecutivo (PDF)")

# ==========================================
# 1. FUENTE DE DATOS FIJA (FUMISCOR)
# ==========================================
SHEET_ID = "1wegxZJDFb4_cawUN8cz0RS9oStUFCeg94w72LUHzGsw"
GID = "315437448"
url_csv = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(ttl=600)
def cargar_datos(url):
    return pd.read_csv(url)

try:
    st.info("Obteniendo datos de producción de Fumiscor desde Google Sheets...")
    df_raw = cargar_datos(url_csv)
    
    # Pre-procesamiento de fechas
    df_raw['Fecha'] = pd.to_datetime(df_raw['Fecha'], errors='coerce')
    df_raw = df_raw.dropna(subset=['Fecha'])

    # ==========================================
    # 2. FILTROS (FECHA Y MÁQUINA MÚLTIPLE)
    # ==========================================
    st.markdown("### Configuración del Reporte")
    
    fecha_min = df_raw['Fecha'].min().date()
    fecha_max = df_raw['Fecha'].max().date()
    
    rango_fechas = st.date_input(
        "📅 1. Selecciona el rango de fechas:",
        value=(fecha_min, fecha_max),
        min_value=fecha_min,
        max_value=fecha_max
    )

    if len(rango_fechas) == 2:
        inicio, fin = rango_fechas
        mask = (df_raw['Fecha'].dt.date >= inicio) & (df_raw['Fecha'].dt.date <= fin)
        df_filtrado_fecha = df_raw.loc[mask].copy()
    else:
        st.warning("Por favor, selecciona un rango de fechas completo (Inicio y Fin).")
        st.stop()

    # --- LIMPIEZA Y FILTRADO ESTRICTO DE MÁQUINAS (SOLO FUMISCOR) ---
    df_filtrado_fecha = df_filtrado_fecha.dropna(subset=['Máquina'])
    
    mapa_limpio = {str(k).strip().upper(): k for k in MAQUINAS_MAP.keys()}
    df_filtrado_fecha['Máquina_Upper'] = df_filtrado_fecha['Máquina'].astype(str).str.strip().str.upper()
    df_filtrado_fecha = df_filtrado_fecha[df_filtrado_fecha['Máquina_Upper'].isin(mapa_limpio.keys())].copy()
    df_filtrado_fecha['Máquina'] = df_filtrado_fecha['Máquina_Upper'].map(mapa_limpio)

    lista_maquinas = sorted(df_filtrado_fecha['Máquina'].unique().tolist())
    
    maquinas_seleccionadas = st.multiselect(
        "⚙️ 2. Selecciona la(s) Máquina(s) a incluir en el PDF:", 
        options=lista_maquinas,
        default=lista_maquinas
    )

    if not maquinas_seleccionadas:
        st.warning("Por favor, selecciona al menos una máquina para generar el reporte.")
        st.stop()

    df = df_filtrado_fecha[df_filtrado_fecha['Máquina'].isin(maquinas_seleccionadas)].copy()

    st.success(f"Datos listos para procesar ({len(df)} registros encontrados para Fumiscor).")
    st.divider()

    # ==========================================
    # 3. CÁLCULOS BASE (Ocultos)
    # ==========================================
    with st.spinner("Procesando datos y calculando métricas..."):
        columnas_num = ['Buenas', 'Retrabajo', 'Observadas', 'Tiempo Producción (Min)', 'Tiempo Ciclo', 'Hora']
        for col in columnas_num:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        df = df[df['Tiempo Producción (Min)'] > 0]
        df['Hora_Real'] = df['Hora'].astype(int)
        df['Orden_Hora'] = df['Hora_Real'].apply(lambda x: x if x >= 6 else x + 24)
        df['Total_Piezas_Fabricadas'] = df['Buenas'] + df['Retrabajo'] + df['Observadas']
        df['Horas_Decimal'] = df['Tiempo Producción (Min)'] / 60

        # --- NUEVO CÁLCULO: CADENCIA TOTAL NETA ---
        resumen_cadencia = df.groupby('Máquina').agg(
            Total_Piezas=('Total_Piezas_Fabricadas', 'sum'),
            Total_Horas=('Horas_Decimal', 'sum')
        ).reset_index()
        resumen_cadencia = resumen_cadencia[resumen_cadencia['Total_Horas'] > 0]
        resumen_cadencia['Cadencia_Neta'] = resumen_cadencia['Total_Piezas'] / resumen_cadencia['Total_Horas']
        
        # Totales globales para la cadencia
        total_pzs_global = resumen_cadencia['Total_Piezas'].sum()
        total_hrs_global = resumen_cadencia['Total_Horas'].sum()
        cadencia_global = total_pzs_global / total_hrs_global if total_hrs_global > 0 else 0

        # --- CÁLCULOS ANTERIORES DE RENDIMIENTO ---
        def calcular_sub_bloque(g):
            if g.empty: return pd.Series({'Total_Piezas': 0.0, 'Total_Horas': 0.0, 'Cantidad_Productos': 0, 'Ciclos_Maquina': 0.0})
            total_piezas = float(g['Total_Piezas_Fabricadas'].sum())
            cantidad_productos = int(g['Código Producto'].nunique())
            total_horas = float(g['Horas_Decimal'].iloc[0]) if not g.empty else 0.0
            ciclos_maquina = total_piezas / cantidad_productos if cantidad_productos > 0 else 0.0
            return pd.Series([total_piezas, total_horas, cantidad_productos, ciclos_maquina], 
                             index=['Total_Piezas', 'Total_Horas', 'Cantidad_Productos', 'Ciclos_Maquina'])

        despliegue_hora = df.groupby(['Fecha', 'Máquina', 'Hora_Real', 'Orden_Hora', 'Horas_Decimal']).apply(calcular_sub_bloque).reset_index()
        despliegue_hora = despliegue_hora.dropna(subset=['Total_Piezas', 'Total_Horas', 'Cantidad_Productos'])
        despliegue_hora['Pzs_Hora_Bloque'] = np.where(despliegue_hora['Total_Horas'] > 0, despliegue_hora['Total_Piezas'] / despliegue_hora['Total_Horas'], 0)
        despliegue_hora['Ciclos_Hora_Bloque'] = np.where(despliegue_hora['Total_Horas'] > 0, despliegue_hora['Ciclos_Maquina'] / despliegue_hora['Total_Horas'], 0)
        despliegue_hora = despliegue_hora[(despliegue_hora['Cantidad_Productos'] > 0) & (despliegue_hora['Total_Horas'] > 0) & (despliegue_hora['Pzs_Hora_Bloque'] > 0)]

        resumen_general = despliegue_hora.groupby(['Máquina', 'Cantidad_Productos']).agg(
            Promedio_Pzs_Hora=('Pzs_Hora_Bloque', 'mean')
        ).reset_index().round(2)

        comp_prod = df.groupby(['Máquina', 'Código Producto']).agg(
            Suma_Piezas=('Total_Piezas_Fabricadas', 'sum'),
            Suma_Horas=('Horas_Decimal', 'sum'),
            Promedio_Tiempo_Ciclo=('Tiempo Ciclo', 'mean')
        ).reset_index().dropna()

        comp_prod = comp_prod[comp_prod['Suma_Horas'] > 0]
        comp_prod['Real_Pzs_Hora'] = comp_prod['Suma_Piezas'] / comp_prod['Suma_Horas']
        comp_prod['Estimado_Pzs_Hora'] = np.where(comp_prod['Promedio_Tiempo_Ciclo'] > 0, 60 / comp_prod['Promedio_Tiempo_Ciclo'], 0)
        comp_prod['Diferencia'] = comp_prod['Real_Pzs_Hora'] - comp_prod['Estimado_Pzs_Hora']
        comp_prod = comp_prod[['Máquina', 'Código Producto', 'Real_Pzs_Hora', 'Estimado_Pzs_Hora', 'Diferencia']].round(2)

        prom_h = despliegue_hora.groupby(['Máquina', 'Hora_Real', 'Orden_Hora']).agg(P=('Pzs_Hora_Bloque', 'mean')).reset_index().sort_values('Orden_Hora')

    # ==========================================
    # 4. GENERACIÓN DEL PDF EJECUTIVO
    # ==========================================
    with st.spinner("Armando el documento PDF..."):
        pdf = FPDF()
        AZUL_TITULO = (0, 51, 102)
        AZUL_FONDO = (204, 229, 255)

        pdf.add_page()
        pdf.set_font("Arial", "B", 18)
        pdf.set_text_color(*AZUL_TITULO)
        pdf.cell(190, 10, "REPORTE DE PRODUCCION EJECUTIVO", 0, 1, 'C')
        
        pdf.set_font("Arial", "I", 11)
        pdf.set_text_color(100, 100, 100)
        
        texto_maquinas = "Multiples Seleccionadas" if len(maquinas_seleccionadas) > 1 else maquinas_seleccionadas[0]
        pdf.cell(190, 8, f"Periodo: {inicio} al {fin} | Maquina(s): {texto_maquinas}", 0, 1, 'C')
        pdf.ln(5)

        # ---- SECCIÓN 1: CADENCIA NETA TOTAL (NUEVA SECCIÓN) ----
        pdf.set_font("Arial", "B", 12)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(190, 10, "1. Cadencia Total Neta (Por Maquina)", 0, 1)
        
        pdf.set_font("Arial", "B", 10)
        pdf.set_fill_color(*AZUL_FONDO)
        pdf.cell(70, 8, "Maquina", 1, 0, 'C', True)
        pdf.cell(40, 8, "Total Piezas", 1, 0, 'C', True)
        pdf.cell(40, 8, "Total Horas", 1, 0, 'C', True)
        pdf.cell(40, 8, "Cadencia Neta (Pzs/h)", 1, 1, 'C', True)
        
        pdf.set_font("Arial", "", 9)
        for _, r in resumen_cadencia.iterrows():
            pdf.cell(70, 7, str(r['Máquina'])[:30], 1)
            pdf.cell(40, 7, f"{int(r['Total_Piezas'])}", 1, 0, 'C')
            pdf.cell(40, 7, f"{r['Total_Horas']:.2f}", 1, 0, 'C')
            pdf.cell(40, 7, f"{r['Cadencia_Neta']:.2f}", 1, 1, 'C')
        
        # Fila de Total Global
        pdf.set_font("Arial", "B", 9)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(70, 7, "TOTAL GLOBAL", 1, 0, 'R', True)
        pdf.cell(40, 7, f"{int(total_pzs_global)}", 1, 0, 'C', True)
        pdf.cell(40, 7, f"{total_hrs_global:.2f}", 1, 0, 'C', True)
        pdf.cell(40, 7, f"{cadencia_global:.2f}", 1, 1, 'C', True)
        pdf.ln(5)

        # ---- SECCIÓN 2: Rendimiento General (Ahora es el punto 2) ----
        pdf.set_font("Arial", "B", 12)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(190, 10, "2. Rendimiento General (Por Cantidad de Productos)", 0, 1)
        
        pdf.set_font("Arial", "B", 10)
        pdf.set_fill_color(*AZUL_FONDO)
        pdf.cell(80, 8, "Maquina", 1, 0, 'C', True)
        pdf.cell(50, 8, "N. Productos Simultaneos", 1, 0, 'C', True)
        pdf.cell(60, 8, "Promedio (Pzs/h)", 1, 1, 'C', True)
        
        pdf.set_font("Arial", "", 9)
        for _, r in resumen_general.iterrows():
            pdf.cell(80, 7, str(r['Máquina'])[:35], 1)
            pdf.cell(50, 7, str(int(r['Cantidad_Productos'])), 1, 0, 'C')
            pdf.cell(60, 7, f"{r['Promedio_Pzs_Hora']:.2f}", 1, 1, 'C')
        pdf.ln(5)

        # ---- SECCIÓN 3: Real vs Estimado (Ahora es el punto 3) ----
        pdf.set_font("Arial", "B", 12)
        pdf.cell(190, 10, "3. Rendimiento por Producto (Real vs Estimado)", 0, 1)
        
        pdf.set_font("Arial", "B", 9)
        pdf.set_fill_color(*AZUL_FONDO)
        pdf.cell(50, 8, "Maquina", 1, 0, 'C', True)
        pdf.cell(65, 8, "Codigo Producto", 1, 0, 'C', True)
        pdf.cell(25, 8, "Real", 1, 0, 'C', True)
        pdf.cell(25, 8, "Estimado", 1, 0, 'C', True)
        pdf.cell(25, 8, "Diferencia", 1, 1, 'C', True)
        
        pdf.set_font("Arial", "", 9)
        for _, r in comp_prod.iterrows():
            pdf.cell(50, 7, str(r['Máquina'])[:25], 1)
            pdf.cell(65, 7, str(r['Código Producto'])[:30], 1)
            pdf.cell(25, 7, f"{r['Real_Pzs_Hora']:.2f}", 1, 0, 'C')
            pdf.cell(25, 7, f"{r['Estimado_Pzs_Hora']:.2f}", 1, 0, 'C')
            
            # Color en Diferencia
            if r['Diferencia'] > 0:
                pdf.set_text_color(0, 150, 0)
                diff_text = f"+{r['Diferencia']:.2f}"
            else:
                pdf.set_text_color(200, 0, 0)
                diff_text = f"{r['Diferencia']:.2f}"
                
            pdf.cell(25, 7, diff_text, 1, 1, 'C')
            pdf.set_text_color(0,0,0)
        pdf.ln(5)

        # ---- SECCIÓN 4: Histórico Diario (Ahora es el punto 4) ----
        for m_id in maquinas_seleccionadas:
            dat_pdf = prom_h[prom_h['Máquina'] == m_id]
            if dat_pdf.empty: continue

            pdf.add_page()
            pdf.set_font("Arial", "B", 12)
            pdf.cell(190, 10, f"4. Rendimiento Historico Diario: {m_id}", 0, 1)
            
            # Tabla del histórico
            pdf.set_font("Arial", "B", 10)
            pdf.set_fill_color(*AZUL_FONDO)
            pdf.cell(70, 8, "Maquina", 1, 0, 'C', True)
            pdf.cell(50, 8, "Hora", 1, 0, 'C', True)
            pdf.cell(70, 8, "Promedio (Pzs/h)", 1, 1, 'C', True)
            
            pdf.set_font("Arial", "", 9)
            for _, r in dat_pdf.iterrows():
                pdf.cell(70, 7, str(r['Máquina'])[:30], 1, 0, 'C')
                pdf.cell(50, 7, f"{r['Hora_Real']}:00", 1, 0, 'C')
                pdf.cell(70, 7, f"{r['P']:.2f}", 1, 1, 'C')
            
            # Gráfico temporal
            fig_t, ax_t = plt.subplots(figsize=(10, 3.5))
            ax_t.plot(dat_pdf['Hora_Real'].astype(str) + ":00", dat_pdf['P'], marker='o', color='#00509E')
            ax_t.set_title(f"Tendencia - {m_id}")
            ax_t.set_ylabel("Promedio (Pzs/h)")
            ax_t.grid(True, linestyle='--', alpha=0.6)
            
            t_name = f"t_{m_id}.png".replace(" ","").replace("/","")
            fig_t.savefig(t_name, bbox_inches='tight')
            plt.close(fig_t)
            
            pdf.ln(5)
            pdf.image(t_name, x=15, w=180)
            if os.path.exists(t_name):
                os.remove(t_name)

        # ==========================================
        # DESCARGA DEL ARCHIVO (CON FECHAS DINÁMICAS)
        # ==========================================
        # Formateamos las fechas de YYYY-MM-DD a un string limpio
        fecha_str = f"{inicio.strftime('%d%m%y')}_al_{fin.strftime('%d%m%y')}"
        
        if len(maquinas_seleccionadas) > 1:
            nombre_archivo = f"Reporte_Produccion_Multi_{fecha_str}.pdf"
        else:
            nombre_limpio = maquinas_seleccionadas[0].replace(' ', '_')
            nombre_archivo = f"Reporte_Produccion_{nombre_limpio}_{fecha_str}.pdf"
            
        pdf.output(nombre_archivo)

    # Botón gigante y claro para la descarga final
    with open(nombre_archivo, "rb") as f:
        st.download_button(
            label="📥 Descargar Reporte Ejecutivo en PDF", 
            data=f, 
            file_name=nombre_archivo,
            mime="application/pdf",
            use_container_width=True
        )

    if os.path.exists(nombre_archivo):
        os.remove(nombre_archivo)

except Exception as e:
    st.error(f"Error de procesamiento: {e}")
