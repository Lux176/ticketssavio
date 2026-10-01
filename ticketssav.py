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
    conn = sqlite3.connect('tickets_savio_v2.db', check_same_thread=False)
    c = conn.cursor()
    # Tabla para docentes/usuarios regulares
    c.execute('''CREATE TABLE IF NOT EXISTS solicitudes 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, solicitante TEXT, salon TEXT, problema TEXT, estado TEXT)''')
    # Tabla exclusiva de administrador (Inspección técnica detallada)
    c.execute('''CREATE TABLE IF NOT EXISTS inspecciones 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, tecnico TEXT, salon TEXT, seccion TEXT, 
                  eq_proyector TEXT, eq_cable TEXT, eq_hdmi TEXT, eq_pared_hdmi TEXT, eq_ethernet TEXT, 
                  eq_pc TEXT, eq_impresora TEXT, req_reparacion TEXT, detalle_falla TEXT, num_inventario TEXT, 
                  baja_inventario TEXT, prioridad TEXT, estado TEXT)''')
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

if 'usuario' not in st.session_state: st.session_state.update({'usuario': None, 'rol': None})

def login():
    st.markdown("<h2 style='text-align: center;'>🏫 Acceso al Sistema de Soporte</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("login_form"):
            usuario = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                if usuario == "admin" and password == "savio2026":
                    st.session_state.update({'usuario': usuario, 'rol': 'admin'})
                    st.rerun()
                elif usuario == "docente" and password == "docente123":
                    st.session_state.update({'usuario': usuario, 'rol': 'solicitante'})
                    st.rerun()
                else:
                    st.error("Credenciales inválidas")

def vista_solicitante():
    st.title("🙋‍♂️ Solicitar Apoyo Técnico")
    st.write("Usa este formulario para reportar fallas en tu salón. El equipo de sistemas acudirá a revisar.")
    
    with st.container(border=True):
        with st.form("nueva_solicitud", clear_on_submit=True):
            salon = st.text_input("Salón o Área (Ej. 6B, Laboratorio)")
            problema = st.text_area("Describe la falla (Ej. El proyector no enciende, no hay internet)")
            
            if st.form_submit_button("Enviar Solicitud", type="primary"):
                if not salon or not problema:
                    st.error("Por favor completa ambos campos.")
                else:
                    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    c.execute("INSERT INTO solicitudes (fecha, solicitante, salon, problema, estado) VALUES (?, ?, ?, ?, ?)",
                              (fecha, st.session_state['usuario'], salon, problema, 'Pendiente'))
                    conn.commit()
                    st.success("Tu solicitud ha sido enviada a sistemas.")
    
    st.subheader("Mis Solicitudes Recientes")
    df_mis_solicitudes = pd.read_sql_query("SELECT fecha, salon, problema, estado FROM solicitudes WHERE solicitante = ?", conn, params=(st.session_state['usuario'],))
    st.dataframe(df_mis_solicitudes, use_container_width=True, hide_index=True)

def vista_admin():
    st.title("⚙️ Panel de Administrador de Sistemas")
    
    # Menú lateral exclusivo para el admin
    menu = st.sidebar.radio("Navegación", ["Bandeja de Solicitudes", "Realizar Inspección Técnica", "Base de Datos de Inspecciones"])
    
    if menu == "Bandeja de Solicitudes":
        st.subheader("Bandeja de Solicitudes (Docentes)")
        df_sol = pd.read_sql_query("SELECT * FROM solicitudes", conn)
        
        if not df_sol.empty:
            pendientes = df_sol[df_sol['estado'] == 'Pendiente']['id'].tolist()
            with st.form("cerrar_solicitud"):
                sid = st.selectbox("Selecciona ID de solicitud para marcar como Atendida", pendientes, index=None)
                if st.form_submit_button("Marcar como Atendida") and sid:
                    c.execute("UPDATE solicitudes SET estado = 'Atendida' WHERE id = ?", (sid,))
                    conn.commit()
                    st.rerun()
            st.dataframe(df_sol, use_container_width=True, hide_index=True)
        else:
            st.info("No hay solicitudes pendientes.")
            
    elif menu == "Realizar Inspección Técnica":
        st.subheader("Formulario de Inspección Física")
        opciones_estado = ["Funciona Correctamente", "Presenta fallas o requiere reparación", "Requiere cambio de equipo", "Faltante"]
        
        with st.form("nuevo_reporte", clear_on_submit=True):
            c1, c2 = st.columns(2)
            salon = c1.text_input("Número o nombre del salón")
            seccion = c2.selectbox("Sección o edificio", ["Preescolar", "Primaria", "Secundaria", "Preparatoria"])
            
            st.markdown("---")
            col_a, col_b = st.columns(2)
            with col_a:
                eq_proyector = st.selectbox("Proyector", opciones_estado)
                eq_hdmi = st.selectbox("Cable HDMI", opciones_estado)
                eq_ethernet = st.selectbox("Pared Ethernet", opciones_estado)
                eq_impresora = st.selectbox("Impresora", opciones_estado)
            with col_b:
                eq_cable = st.selectbox("Corriente proyector", opciones_estado)
                eq_pared_hdmi = st.selectbox("Pared HDMI", opciones_estado)
                eq_pc = st.selectbox("PC/Laptop", opciones_estado)
                
            st.markdown("---")
            req_reparacion = st.radio("¿Requiere reparación o cambio?", ["No", "Si"])
            detalle_falla = st.text_area("Especificar falla (si aplica)")
            
            c_inv, c_baja, c_prio = st.columns(3)
            num_inventario = c_inv.text_input("Núm. Inventario")
            baja_inventario = c_baja.radio("¿Baja del inventario?", ["No", "Si"])
            prioridad = c_prio.selectbox("Prioridad", ["1", "2", "3"])
            
            if st.form_submit_button("Registrar Inspección", type="primary"):
                if salon:
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
                    st.success("Inspección guardada.")
                else:
                    st.error("El salón es obligatorio.")

    elif menu == "Base de Datos de Inspecciones":
        st.subheader("Historial Técnico y Exportación")
        df_insp = pd.read_sql_query("SELECT * FROM inspecciones", conn)
        if not df_insp.empty:
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_insp.to_excel(writer, index=False, sheet_name='Inspecciones')
            st.download_button("📥 Descargar Reporte Excel", data=output.getvalue(), file_name="inspecciones_salones.xlsx")
            st.dataframe(df_insp, use_container_width=True, hide_index=True)
        else:
            st.info("Sin inspecciones registradas.")

# Flujo Principal
if not st.session_state['usuario']:
    login()
else:
    with st.sidebar:
        st.write(f"👤 Activo: **{st.session_state['usuario'].upper()}**")
        st.write(f"Rol: *{st.session_state['rol']}*")
        if st.button("Cerrar Sesión", use_container_width=True):
            st.session_state.update({'usuario': None, 'rol': None})
            st.rerun()
            
    if st.session_state['rol'] == 'admin':
        vista_admin()
    else:
        vista_solicitante()
