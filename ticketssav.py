import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from io import BytesIO

# Configuración de página
st.set_page_config(page_title="Soporte Domingo Savio", page_icon="🚨", layout="wide")

# Conexión a Base de Datos
@st.cache_resource
def init_db():
    conn = sqlite3.connect('tickets_pc.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tickets 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT, categoria TEXT, descripcion TEXT, estado TEXT, fecha TEXT)''')
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# Control de Sesión
if 'usuario' not in st.session_state: st.session_state.update({'usuario': None, 'rol': None})

def login():
    st.markdown("<h2 style='text-align: center;'>🚨 Acceso al Sistema</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("login_form"):
            usuario = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                if usuario == "admin" and password == "admin123":
                    st.session_state.update({'usuario': usuario, 'rol': 'admin'})
                    st.rerun()
                elif usuario == "operador" and password == "operador123":
                    st.session_state.update({'usuario': usuario, 'rol': 'operador'})
                    st.rerun()
                else:
                    st.error("Credenciales inválidas")

def vista_operador():
    st.title("📝 Captura de Incidencias")
    categorias = ["GR1= Vivienda en riesgo", "GR2= Deslave", "GR3= Socavón", "GR4= Seguimiento del reporte"]
    
    with st.container(border=True):
        with st.form("nuevo_reporte", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1: categoria = st.selectbox("Clasificación", categorias)
            with col2: st.info("Verifica las coordenadas antes de enviar.")
            descripcion = st.text_area("Descripción y Georreferencia", height=100)
            
            if st.form_submit_button("Registrar Reporte", type="primary"):
                fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                c.execute("INSERT INTO tickets (usuario, categoria, descripcion, estado, fecha) VALUES (?, ?, ?, ?, ?)", 
                          (st.session_state['usuario'], categoria, descripcion, 'Abierto', fecha))
                conn.commit()
                st.success(f"Reporte {categoria[:3]} registrado.")

def vista_admin():
    st.title("📊 Panel de Control")
    df = pd.read_sql_query("SELECT * FROM tickets", conn)
    
    if not df.empty:
        # Métricas
        abiertos = len(df[df['estado'] == 'Abierto'])
        cerrados = len(df[df['estado'] == 'Cerrado'])
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Reportes", len(df))
        c2.metric("🟢 Abiertos", abiertos)
        c3.metric("🔴 Cerrados", cerrados)
        
        # Gestión
        st.subheader("Gestión Rápida")
        col_cerrar, col_descargar = st.columns(2)
        
        with col_cerrar:
            tickets_abiertos = df[df['estado'] == 'Abierto']['id'].tolist()
            with st.form("cerrar_ticket"):
                tid = st.selectbox("Folio a cerrar", tickets_abiertos, index=None)
                if st.form_submit_button("Cerrar Ticket") and tid:
                    c.execute("UPDATE tickets SET estado = 'Cerrado' WHERE id = ?", (tid,))
                    conn.commit()
                    st.rerun()
        
        with col_descargar:
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Reportes')
            st.download_button("📥 Descargar Excel", data=output.getvalue(), file_name="reportes.xlsx", mime="application/vnd.ms-excel")
        
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Sin datos registrados.")

# Flujo Principal
if not st.session_state['usuario']:
    login()
else:
    with st.sidebar:
        st.write(f"👤 **{st.session_state['usuario'].upper()}**")
        if st.button("Cerrar Sesión", use_container_width=True):
            st.session_state.update({'usuario': None, 'rol': None})
            st.rerun()
            
    if st.session_state['rol'] == 'admin': vista_admin()
    else: vista_operador()
