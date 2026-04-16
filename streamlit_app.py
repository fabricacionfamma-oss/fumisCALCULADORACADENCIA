import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import tempfile
from fpdf import FPDF
from datetime import datetime

# ==========================================
# 0. DICCIONARIO DE MÁQUINAS FUMISCOR
# ==========================================
MAQUINAS_MAP = {
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
# FUNCIÓN DE LIMPIEZA DE TEXTO PARA PDF
# ==========================================
def clean_text(text):
    """Limpia caracteres que FPDF no soporta (emojis, etc.)"""
    if pd.isna(text): return "-"
    return str(text).encode('latin-1', 'replace').decode('latin-1')

# ==========================================
# CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(page_title="Generador de Reportes de Producción", layout="centered", page_icon="📊")
st.title("📊 Generador de Reportes (Producción y Auditoría)")

# ==========================================
# 1. FUNCIÓN DE EXTRACCIÓN SQL
# ==========================================
@st.cache_data(ttl=300)
def fetch_produccion_diaria(fecha_ini, fecha_fin):
    conn = st.connection("wii_bi", type="sql")
    ini_str = fecha_ini.strftime('%Y-%m-%d')
    fin_str = fecha_fin.strftime('%Y-%m-%d')

    try:
        query_piezas = f"""
            SELECT 
                p.Date as Fecha,
                c.Name as Máquina,
                pr.Code as [Código Producto],
                MAX(p.CycleTime) as [Tiempo Ciclo],
                SUM(p.Good) as Buenas,
                SUM(p.Rework) as Retrabajo,
                SUM(p.Scrap) as Observadas
            FROM PROD_D_01 p 
            JOIN CELL c ON p.CellId = c.CellId
            JOIN PRODUCT pr ON p.ProductId = pr.ProductId
            WHERE p.Date BETWEEN '{ini_str}' AND '{fin_str}'
            GROUP BY p.Date, c.Name, pr.Code
        """
        df_pzs = conn.query(query_piezas)

        query_tiempos = f"""
            SELECT 
                p.Date as Fecha,
                c.Name as Máquina,
                SUM(p.ProductiveTime) as [Tiempo Producción (Min)]
            FROM PROD_D_03 p 
            JOIN CELL c ON p.CellId = c.CellId
            WHERE p.Date BETWEEN '{ini_str}' AND '{fin_str}'
            GROUP BY p.Date, c.Name
        """
        df_times = conn.query(query_tiempos)

        if df_pzs.empty:
            return pd.DataFrame(), None

        df_merged = pd.merge(df_pzs, df_times, on=['Fecha', 'Máquina'], how='left')
        df_merged['Tiempo Producción (Min)'] = df_merged['Tiempo Producción (Min)'].fillna(0)
        
        return df_merged, None
        
    except Exception as e:
        return pd.DataFrame(), str(e)

# ==========================================
# 2. FILTROS Y EJECUCIÓN
# ==========================================
st.markdown("### Configuración del Reporte")

today = pd.to_datetime("today").date()
rango_fechas = st.date_input(
    "📅 1. Selecciona el rango de fechas:",
    value=(today - pd.Timedelta(days=7), today),
    max_value=today
)

if len(rango_fechas) == 2:
    inicio, fin = rango_fechas
    
    with st.spinner("Conectando a SQL Server..."):
        df_raw, status_error = fetch_produccion_diaria(inicio, fin)

    if status_error:
        st.error(f"❌ Error de SQL Server: {status_error}")
        st.stop()

    if df_raw.empty:
        st.warning("No hay datos de producción para estas fechas.")
        st.stop()

    # Pre-procesamiento
    df_raw['Fecha'] = pd.to_datetime(df_raw['Fecha'], errors='coerce')
    df_raw = df_raw.dropna(subset=['Fecha', 'Máquina'])
    
    mapa_limpio = {str(k).strip().upper(): k for k in MAQUINAS_MAP.keys()}
    df_raw['Máquina_Upper'] = df_raw['Máquina'].astype(str).str.strip().str.upper()
    df_raw = df_raw[df_raw['Máquina_Upper'].isin(mapa_limpio.keys())].copy()
    df_raw['Máquina'] = df_raw['Máquina_Upper'].map(mapa_limpio)

    lista_maquinas = sorted(df_raw['Máquina'].unique().tolist())
    
    maquinas_seleccionadas = st.multiselect(
        "⚙️ 2. Selecciona la(s) Máquina(s) a procesar:", 
        options=lista_maquinas,
        default=lista_maquinas
    )

    if not maquinas_seleccionadas:
        st.warning("Por favor, selecciona al menos una máquina.")
        st.stop()

    df = df_raw[df_raw['Máquina'].isin(maquinas_seleccionadas)].copy()
    st.success(f"Datos listos para procesar ({len(df)} registros validados).")
    st.divider()

    # ==========================================
    # 3. CÁLCULOS BASE (REPORTE EJECUTIVO)
    # ==========================================
    with st.spinner("Calculando métricas..."):
        columnas_num = ['Buenas', 'Retrabajo', 'Observadas', 'Tiempo Producción (Min)', 'Tiempo Ciclo']
        for col in columnas_num:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        df_calc = df[df['Tiempo Producción (Min)'] > 0].copy()
        df_calc['Total_Piezas_Fabricadas'] = df_calc['Buenas'] + df_calc['Retrabajo'] + df_calc['Observadas']
        df_calc['Horas_Decimal'] = df_calc['Tiempo Producción (Min)'] / 60

        def calcular_sub_bloque(g):
            if g.empty: return pd.Series({'Total_Piezas': 0.0, 'Total_Horas': 0.0, 'Cantidad_Productos': 0})
            total_piezas = float(g['Total_Piezas_Fabricadas'].sum())
            cantidad_productos = int(g['Código Producto'].nunique())
            total_horas = float(g['Horas_Decimal'].iloc[0]) if not g.empty else 0.0
            return pd.Series([total_piezas, total_horas, cantidad_productos], 
                             index=['Total_Piezas', 'Total_Horas', 'Cantidad_Productos'])

        despliegue_dia = df_calc.groupby(['Fecha', 'Máquina']).apply(calcular_sub_bloque).reset_index()
        despliegue_dia = despliegue_dia.dropna(subset=['Total_Piezas', 'Total_Horas', 'Cantidad_Productos'])
        
        despliegue_dia['Pzs_Hora_Promedio'] = np.where(despliegue_dia['Total_Horas'] > 0, despliegue_dia['Total_Piezas'] / despliegue_dia['Total_Horas'], 0)
        despliegue_dia = despliegue_dia[(despliegue_dia['Cantidad_Productos'] > 0) & (despliegue_dia['Total_Horas'] > 0) & (despliegue_dia['Pzs_Hora_Promedio'] > 0)]

        resumen_general = despliegue_dia.groupby(['Máquina', 'Cantidad_Productos']).agg(
            Promedio_Pzs_Hora=('Pzs_Hora_Promedio', 'mean')
        ).reset_index().round(2)

        comp_prod = df_calc.groupby(['Máquina', 'Código Producto']).agg(
            Suma_Piezas=('Total_Piezas_Fabricadas', 'sum'),
            Suma_Horas=('Horas_Decimal', 'sum'),
            Tiempo_Ciclo_DB=('Tiempo Ciclo', 'mean')
        ).reset_index().dropna()

        comp_prod = comp_prod[comp_prod['Suma_Horas'] > 0]
        comp_prod['Real_Pzs_Hora'] = comp_prod['Suma_Piezas'] / comp_prod['Suma_Horas']
        comp_prod['Estimado_Pzs_Hora'] = np.where(comp_prod['Tiempo_Ciclo_DB'] > 0, 60 / comp_prod['Tiempo_Ciclo_DB'], 0)
        comp_prod = comp_prod[['Máquina', 'Código Producto', 'Tiempo_Ciclo_DB', 'Real_Pzs_Hora', 'Estimado_Pzs_Hora']].round(3)

        prom_d = despliegue_dia[['Máquina', 'Fecha', 'Pzs_Hora_Promedio', 'Cantidad_Productos']].copy()
        prom_d.rename(columns={'Pzs_Hora_Promedio': 'P'}, inplace=True)
        prom_d = prom_d.sort_values('Fecha')

    # ==========================================
    # 4. GENERACIÓN DE PDF - REPORTE EJECUTIVO
    # ==========================================
    def generar_pdf_ejecutivo():
        pdf = FPDF()
        AZUL_TITULO = (0, 51, 102)
        AZUL_FONDO = (204, 229, 255)

        pdf.add_page()
        pdf.set_font("Arial", "B", 18)
        pdf.set_text_color(*AZUL_TITULO)
        pdf.cell(190, 10, clean_text("REPORTE DE PRODUCCION EJECUTIVO"), 0, 1, 'C')
        
        pdf.set_font("Arial", "I", 11)
        pdf.set_text_color(100, 100, 100)
        texto_maquinas = "Multiples Seleccionadas" if len(maquinas_seleccionadas) > 1 else maquinas_seleccionadas[0]
        pdf.cell(190, 8, clean_text(f"Periodo: {inicio} al {fin} | Maquina(s): {texto_maquinas}"), 0, 1, 'C')
        pdf.ln(5)

        # ---- SECCIÓN 1: Rendimiento General ----
        pdf.set_font("Arial", "B", 12)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(190, 10, clean_text("1. Rendimiento General (Por Cantidad de Productos)"), 0, 1)
        
        pdf.set_font("Arial", "B", 10)
        pdf.set_fill_color(*AZUL_FONDO)
        pdf.cell(80, 8, "Maquina", 1, 0, 'C', True)
        pdf.cell(50, 8, "N. Productos Simultaneos", 1, 0, 'C', True)
        pdf.cell(60, 8, "Promedio (Pzs/h)", 1, 1, 'C', True)
        
        pdf.set_font("Arial", "", 9)
        for _, r in resumen_general.iterrows():
            pdf.cell(80, 7, clean_text(r['Máquina'])[:35], 1)
            pdf.cell(50, 7, str(int(r['Cantidad_Productos'])), 1, 0, 'C')
            pdf.cell(60, 7, f"{r['Promedio_Pzs_Hora']:.2f}", 1, 1, 'C')
        pdf.ln(5)

        # ---- SECCIÓN 2: Rendimiento Real por Producto ----
        pdf.set_font("Arial", "B", 12)
        pdf.cell(190, 10, clean_text("2. Rendimiento por Producto (Validacion TC vs DB)"), 0, 1)
        
        pdf.set_font("Arial", "B", 8)
        pdf.set_fill_color(*AZUL_FONDO)
        pdf.cell(45, 8, "Maquina", 1, 0, 'C', True)
        pdf.cell(65, 8, "Codigo Producto", 1, 0, 'C', True)
        pdf.cell(20, 8, "TC DB(min)", 1, 0, 'C', True)
        pdf.cell(30, 8, "Real (Pzs/h)", 1, 0, 'C', True)
        pdf.cell(30, 8, "Est. (Pzs/h)", 1, 1, 'C', True)
        
        pdf.set_font("Arial", "", 8)
        for _, r in comp_prod.iterrows():
            pdf.cell(45, 7, clean_text(r['Máquina'])[:22], 1)
            pdf.cell(65, 7, clean_text(r['Código Producto'])[:35], 1)
            pdf.cell(20, 7, f"{r['Tiempo_Ciclo_DB']:.3f}", 1, 0, 'C')
            pdf.cell(30, 7, f"{r['Real_Pzs_Hora']:.2f}", 1, 0, 'C')
            pdf.cell(30, 7, f"{r['Estimado_Pzs_Hora']:.2f}", 1, 1, 'C')
        pdf.ln(5)

        # ---- SECCIÓN 3: Histórico Diario ----
        for m_id in maquinas_seleccionadas:
            dat_pdf = prom_d[prom_d['Máquina'] == m_id]
            if dat_pdf.empty: continue

            pdf.add_page()
            pdf.set_font("Arial", "B", 12)
            pdf.cell(190, 10, clean_text(f"3. Rendimiento Historico Diario: {m_id}"), 0, 1)
            
            pdf.set_font("Arial", "B", 10)
            pdf.set_fill_color(*AZUL_FONDO)
            pdf.cell(60, 8, "Maquina", 1, 0, 'C', True)
            pdf.cell(40, 8, "Fecha", 1, 0, 'C', True)
            pdf.cell(40, 8, "Cant. Productos", 1, 0, 'C', True)
            pdf.cell(50, 8, "Promedio Diario", 1, 1, 'C', True)
            
            pdf.set_font("Arial", "", 9)
            for _, r in dat_pdf.iterrows():
                fecha_format = r['Fecha'].strftime('%d/%m/%Y')
                pdf.cell(60, 7, clean_text(r['Máquina'])[:28], 1, 0, 'C')
                pdf.cell(40, 7, fecha_format, 1, 0, 'C')
                pdf.cell(40, 7, str(int(r['Cantidad_Productos'])), 1, 0, 'C')
                pdf.cell(50, 7, f"{r['P']:.2f}", 1, 1, 'C')
            
            fig_t, ax_t = plt.subplots(figsize=(10, 3.5))
            ax_t.plot(dat_pdf['Fecha'].dt.strftime('%d/%m'), dat_pdf['P'], marker='o', color='#00509E')
            ax_t.set_title(clean_text(f"Tendencia Diaria - {m_id}"))
            ax_t.set_ylabel("Promedio (Pzs/h)")
            ax_t.grid(True, linestyle='--', alpha=0.6)
            plt.xticks(rotation=45)
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_img:
                fig_t.savefig(tmp_img.name, bbox_inches='tight')
                t_name = tmp_img.name
            plt.close(fig_t)
            
            pdf.ln(5)
            pdf.image(t_name, x=15, w=180)
            if os.path.exists(t_name): os.remove(t_name)

        fecha_str = f"{inicio.strftime('%d%m%y')}_al_{fin.strftime('%d%m%y')}"
        nombre_pdf = f"Reporte_Produccion_{fecha_str}.pdf"
        pdf.output(nombre_pdf)
        return nombre_pdf

    # ==========================================
    # 5. GENERACIÓN DE PDF - AUDITORÍA DE TC
    # ==========================================
    def generar_pdf_auditoria(df_base):
        df_audit = df_base[['Fecha', 'Máquina', 'Código Producto', 'Tiempo Ciclo']].copy()
        df_audit = df_audit.dropna(subset=['Tiempo Ciclo'])
        df_audit = df_audit.sort_values(by=['Máquina', 'Código Producto', 'Fecha'])
        
        df_audit['TC_Anterior'] = df_audit.groupby(['Máquina', 'Código Producto'])['Tiempo Ciclo'].shift(1)
        df_audit['Hubo_Cambio'] = (df_audit['TC_Anterior'].notna()) & (df_audit['Tiempo Ciclo'] != df_audit['TC_Anterior'])
        
        df_imprimir = df_audit[df_audit['TC_Anterior'].isna() | df_audit['Hubo_Cambio']].copy()

        pdf = FPDF(orientation='L')
        AZUL_TITULO = (0, 51, 102)
        AZUL_FONDO = (204, 229, 255)
        ROJO_ALERTA = (255, 204, 204)

        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.set_text_color(*AZUL_TITULO)
        pdf.cell(277, 10, clean_text("REPORTE DE AUDITORIA: VARIACIONES EN TIEMPO DE CICLO"), 0, 1, 'C')
        
        pdf.set_font("Arial", "I", 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(277, 6, clean_text(f"Periodo: {inicio.strftime('%d/%m/%Y')} al {fin.strftime('%d/%m/%Y')}"), 0, 1, 'C')
        pdf.ln(5)

        pdf.set_font("Arial", "B", 9)
        pdf.set_fill_color(*AZUL_FONDO)
        pdf.set_text_color(0, 0, 0)
        
        pdf.cell(35, 8, "Fecha", 1, 0, 'C', True)
        pdf.cell(50, 8, "Maquina", 1, 0, 'C', True)
        pdf.cell(80, 8, "Codigo Producto", 1, 0, 'C', True)
        pdf.cell(35, 8, "TC Anterior (min)", 1, 0, 'C', True)
        pdf.cell(35, 8, "TC Reportado (min)", 1, 0, 'C', True)
        pdf.cell(42, 8, "Estado / Alerta", 1, 1, 'C', True)

        pdf.set_font("Arial", "", 8)

        for _, row in df_imprimir.iterrows():
            if pdf.get_y() > 180:
                pdf.add_page()
                pdf.set_font("Arial", "B", 9)
                pdf.set_fill_color(*AZUL_FONDO)
                pdf.cell(35, 8, "Fecha", 1, 0, 'C', True)
                pdf.cell(50, 8, "Maquina", 1, 0, 'C', True)
                pdf.cell(80, 8, "Codigo Producto", 1, 0, 'C', True)
                pdf.cell(35, 8, "TC Anterior (min)", 1, 0, 'C', True)
                pdf.cell(35, 8, "TC Reportado (min)", 1, 0, 'C', True)
                pdf.cell(42, 8, "Estado / Alerta", 1, 1, 'C', True)
                pdf.set_font("Arial", "", 8)

            es_alerta = row['Hubo_Cambio']
            if es_alerta:
                pdf.set_fill_color(*ROJO_ALERTA)
                pdf.set_font("Arial", "B", 8)
                # Se eliminó el emoji para evitar el UnicodeEncodeError
                estado = "CAMBIO DETECTADO" 
            else:
                pdf.set_fill_color(255, 255, 255)
                pdf.set_font("Arial", "", 8)
                estado = "Valor Inicial"

            tc_ant = f"{row['TC_Anterior']:.3f}" if pd.notna(row['TC_Anterior']) else "-"
            tc_act = f"{row['Tiempo Ciclo']:.3f}"
            fecha_str = row['Fecha'].strftime('%d/%m/%Y')

            pdf.cell(35, 7, fecha_str, 1, 0, 'C', fill=es_alerta)
            pdf.cell(50, 7, clean_text(row['Máquina'])[:25], 1, 0, 'L', fill=es_alerta)
            pdf.cell(80, 7, clean_text(row['Código Producto'])[:45], 1, 0, 'L', fill=es_alerta)
            pdf.cell(35, 7, tc_ant, 1, 0, 'C', fill=es_alerta)
            pdf.cell(35, 7, tc_act, 1, 0, 'C', fill=es_alerta)
            pdf.cell(42, 7, estado, 1, 1, 'C', fill=es_alerta)

        fecha_str = f"{inicio.strftime('%d%m%y')}_al_{fin.strftime('%d%m%y')}"
        nombre_pdf = f"Auditoria_TC_{fecha_str}.pdf"
        pdf.output(nombre_pdf)
        return nombre_pdf

    # ==========================================
    # 6. BOTONES DE DESCARGA EN INTERFAZ
    # ==========================================
    with st.spinner("Renderizando documentos PDF..."):
        file_ejecutivo = generar_pdf_ejecutivo()
        file_auditoria = generar_pdf_auditoria(df)

    st.write("### 📥 Descarga de Reportes")
    col_btn1, col_btn2 = st.columns(2)

    with col_btn1:
        with open(file_ejecutivo, "rb") as f_ej:
            st.download_button(
                label="📊 Descargar Reporte Ejecutivo (Producción)", 
                data=f_ej, 
                file_name=file_ejecutivo,
                mime="application/pdf",
                use_container_width=True,
                type="primary"
            )

    with col_btn2:
        with open(file_auditoria, "rb") as f_au:
            st.download_button(
                label="🕵️ Descargar Auditoría de Cambios de TC", 
                data=f_au, 
                file_name=file_auditoria,
                mime="application/pdf",
                use_container_width=True,
                type="secondary"
            )

    if os.path.exists(file_ejecutivo): os.remove(file_ejecutivo)
    if os.path.exists(file_auditoria): os.remove(file_auditoria)

else:
    st.warning("Por favor, selecciona un rango de fechas completo (Inicio y Fin).")
