import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from io import BytesIO

# Configuración de página
st.set_page_config(page_title="Soporte Domingo Savio", page_icon="🏫", layout="wide")

# Conexión a Base de Datos
@st.cache_resource
def init_db():
    conn = sqlite3.connect('tickets_savio.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS inspecciones 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  fecha TEXT, 
                  tecnico TEXT, 
                  salon TEXT, 
                  seccion TEXT, 
                  eq_proyector TEXT, 
                  eq_cable TEXT, 
                  eq_hdmi TEXT, 
                  eq_pared_hdmi TEXT, 
                  eq_ethernet TEXT, 
                  eq_pc TEXT, 
                  eq_impresora TEXT, 
                  req_reparacion TEXT, 
                  detalle_falla TEXT, 
                  num_inventario TEXT, 
                  baja_inventario TEXT, 
                  prioridad TEXT, 
                  estado TEXT)''')
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# Control de Sesión
if 'usuario' not in st.session_state: st.session_state.update({'usuario': None, 'rol': None})

def login():
    st.markdown("<h2 style='text-align: center;'>🏫 Acceso al Sistema de Aulas</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("login_form"):
            usuario = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                if usuario == "admin" and password == "savio2026":
                    st.session_state.update({'usuario': usuario, 'rol': 'admin'})
                    st.rerun()
                elif usuario == "soporte" and password == "soporte":
                    st.session_state.update({'usuario': usuario, 'rol': 'operador'})
                    st.rerun()
                else:
                    st.error("Credenciales inválidas")

def vista_operador():
    st.title("📝 Estatus de Salones")
    
    opciones_estado = [
        "Funciona Correctamente", 
        "Presenta fallas o requiere reparación", 
        "Requiere cambio de equipo o daño total", 
        "Faltante o no está en el salón"
    ]
    
    with st.container(border=True):
        with st.form("nuevo_reporte", clear_on_submit=True):
            st.subheader("Datos de Ubicación")
            col1, col2 = st.columns(2)
            with col1:
                salon = st.text_input("Número o nombre del salón")
            with col2:
                seccion = st.selectbox("Sección o edificio", ["Preescolar", "Primaria", "Secundaria", "Preparatoria"])
            
            st.subheader("Inspección de Equipos de Sistemas")
            c1, c2 = st.columns(2)
            with c1:
                eq_proyector = st.selectbox("Proyector", opciones_estado)
                eq_hdmi = st.selectbox("Cable HDMI", opciones_estado)
                eq_ethernet = st.selectbox("Conector de pared Ethernet", opciones_estado)
                eq_impresora = st.selectbox("Impresora", opciones_estado)
            with c2:
                eq_cable = st.selectbox("Cable de corriente del proyector", opciones_estado)
                eq_pared_hdmi = st.selectbox("Conector de pared HDMI", opciones_estado)
                eq_pc = st.selectbox("Laptop o computadora", opciones_estado)
                
            st.subheader("Detalles de Reparación y Prioridad")
            req_reparacion = st.radio("¿Algún equipo requiere reparación o cambio?", ["No", "Si"])
            detalle_falla = st.text_area("Si es afirmativa, especifica equipo y falla")
            
            col_inv, col_baja, col_prio = st.columns(3)
            with col_inv:
                num_inventario = st.text_input("Número de serie/inventario")
            with col_baja:
                baja_inventario = st.radio("¿Requiere baja del inventario?", ["No", "Si"])
            with col_prio:
                prioridad = st.selectbox("Prioridad", ["1", "2", "3"])
            
            if st.form_submit_button("Registrar Inspección", type="primary"):
                if not salon:
                    st.error("El nombre del salón es obligatorio.")
                else:
                    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    c.execute("""INSERT INTO inspecciones 
                                 (fecha, tecnico, salon, seccion, eq_proyector, eq_cable, eq_hdmi, eq_pared_hdmi, 
                                  eq_ethernet, eq_pc, eq_impresora, req_reparacion, detalle_falla, num_inventario, 
                                  baja_inventario, prioridad, estado) 
                                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                              (fecha, st.session_state['usuario'], salon, seccion, eq_proyector, eq_cable, eq_hdmi, 
                               eq_pared_hdmi, eq_ethernet, eq_pc, eq_impresora, req_reparacion, detalle_falla, 
                               num_inventario, baja_inventario, prioridad, 'En revisión'))
                    conn.commit()
                    st.success(f"Inspección del salón {salon} registrada correctamente.")

def vista_admin():
    st.title("📊 Panel de Control - Aulas")
    df = pd.read_sql_query("SELECT * FROM inspecciones", conn)
    
    if not df.empty:
        # Métricas
        revision = len(df[df['estado'] == 'En revisión'])
        terminados = len(df[df['estado'] == 'Terminado'])
        c1, c2, c3 = st.columns(3)
        c1.metric("Total de Inspecciones", len(df))
        c2.metric("🟡 En Revisión", revision)
        c3.metric("🟢 Terminados", terminados)
        
        # Gestión
        st.subheader("Gestión de Estatus")
        col_cerrar, col_descargar = st.columns(2)
        
        with col_cerrar:
            tickets_abiertos = df[df['estado'] == 'En revisión']['id'].tolist()
            with st.form("cerrar_ticket"):
                tid = st.selectbox("Folio a marcar como Terminado", tickets_abiertos, index=None)
                if st.form_submit_button("Actualizar Estatus") and tid:
                    c.execute("UPDATE inspecciones SET estado = 'Terminado' WHERE id = ?", (tid,))
                    conn.commit()
                    st.rerun()
        
        with col_descargar:
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Estatus Salones')
            st.download_button("📥 Descargar Reporte Excel", data=output.getvalue(), file_name="estatus_salones.xlsx", mime="application/vnd.ms-excel")
        
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Sin inspecciones registradas.")

# Flujo Principal
if not st.session_state['usuario']:
    login()
else:
    with st.sidebar:
        st.write(f"👤 **Técnico:** {st.session_state['usuario'].upper()}")
        if st.button("Cerrar Sesión", use_container_width=True):
            st.session_state.update({'usuario': None, 'rol': None})
            st.rerun()
            
    if st.session_state['rol'] == 'admin': vista_admin()
    else: vista_operador()
