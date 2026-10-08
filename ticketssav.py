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
    conn = sqlite3.connect('tickets_savio_v3.db', check_same_thread=False)
    c = conn.cursor()
    # Tabla actualizada para docentes (con nuevos campos)
    c.execute('''CREATE TABLE IF NOT EXISTS solicitudes 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, solicitante TEXT, 
                  nombre_completo TEXT, cargo TEXT, seccion TEXT, salon TEXT, 
                  problema TEXT, impacto TEXT, estado TEXT)''')
    # Tabla de administrador intacta
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
    # --- CONFIGURACIÓN DE IMAGEN DE FONDO GLOBAL ---
    # Reemplaza la URL entre comillas simples con tu link de imagen o GIF
    url_fondo = 'https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExeGJkZTZ4OTBwaWRkam85azNudGRmb3h2MzJjenBnd2Z1YW9paGtpcCZlcD12MV9naWZzX3NlYXJjaCZjdD1n/ec5iuhc2aM9o3uK64q/giphy.gif' 
    
    st.markdown(f"""
        <style>
        .stApp {{
            background-image: url('{url_fondo}');
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        /* Hace semi-transparente el recuadro del formulario para que el fondo resalte */
        [data-testid="stForm"] {{
            background-color: rgba(255, 255, 255, 0.85); 
            border-radius: 15px;
        }}
        </style>
        """, unsafe_allow_html=True)

    # --- CONFIGURACIÓN DEL LOGO/GIF EN EL INICIO DE SESIÓN ---
    # Reemplaza este link por tu GIF de Giphy (Usa el "GIF Link" directo que termina en .gif)
    url_gif = 'https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3cWlwN2wyang2MXcyMTBsMXlwb3U1cmswOHF6Z2xoYTFzNmZpdXN4dyZlcD12MV9naWZzX3NlYXJjaCZjdD1n/9vJCmAR3mfKdJCeNHM/giphy.gif'
    
    st.markdown("<h1 style='text-align: center; color: #1f2937;'>🏫 Sistema de Soporte</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # El CSS maxWidth: 100% asegura que el GIF nunca se salga del contenedor de la columna
        st.markdown(
            f'<div style="display: flex; justify-content: center; margin-bottom: 20px;">'
            f'<img src="{url_gif}" style="max-width: 100%; border-radius: 10px; box-shadow: 0px 4px 10px rgba(0,0,0,0.1);">'
            f'</div>', 
            unsafe_allow_html=True
        )
        
        with st.form("login_form"):
            usuario = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            
            if st.form_submit_button("Entrar", use_container_width=True):
                user_clean = usuario.strip().lower()
                pass_clean = password.strip()
                
                # Validación segura leyendo las contraseñas ocultas en secrets.toml
                if user_clean == "admin" and pass_clean == st.secrets["pass_admin"]:
                    st.session_state.update({'usuario': user_clean, 'rol': 'admin'})
                    st.rerun()
                elif user_clean == "docente" and pass_clean == st.secrets["pass_docente"]:
                    st.session_state.update({'usuario': user_clean, 'rol': 'solicitante'})
                    st.rerun()
                else:
                    st.error("Credenciales inválidas. Verifica mayúsculas y espacios.")

def vista_solicitante():
    st.title("🙋‍♂️ Centro de Apoyo Técnico")
    
    # Dividimos la vista en dos pestañas
    tab1, tab2 = st.tabs(["📝 Levantar Reporte y Mis Tickets", "👀 Fila de Espera Global"])
    
    # --- PESTAÑA 1: Formulario y tickets propios ---
    with tab1:
        st.write("Completa los datos para reportar la falla. El equipo de sistemas acudirá a revisar.")
        
        with st.container(border=True):
            with st.form("nueva_solicitud", clear_on_submit=True):
                st.subheader("Datos del Solicitante")
                c1, c2 = st.columns(2)
                nombre_completo = c1.text_input("Nombre y Apellido")
                cargo = c2.text_input("Cargo (Ej. Docente titular, Prefecto, etc.)")
                
                st.subheader("Ubicación y Detalle")
                c3, c4 = st.columns(2)
                seccion = c3.selectbox("Sección", ["Preescolar", "Primaria", "Secundaria", "Preparatoria", "Áreas Comunes", "Dirección"])
                salon = c4.text_input("Salón o Área (Ej. 6B, Laboratorio)")
                
                problema = st.text_area("Describe la falla (Ej. El proyector no enciende, no hay internet)")
                
                # --- ACTUALIZACIÓN: Tres niveles de urgencia ---
                impacto = st.radio("Nivel de Urgencia", [
                    "Bajo - Puede revisarse en el transcurso del día", 
                    "Medio - Interfiere parcialmente con las actividades",
                    "Alto - Afecta una clase en curso (Urgente)"
                ])
                
                st.markdown("---")
                foto = st.file_uploader("📸 Adjuntar fotografía de la falla (Opcional)", type=['jpg', 'jpeg', 'png'])
                
                if st.form_submit_button("Enviar Solicitud", type="primary"):
                    if not nombre_completo or not salon or not problema:
                        st.error("Por favor completa tu nombre, salón y descripción del problema.")
                    else:
                        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        texto_evidencia = f"\n[Evidencia adjunta: {foto.name}]" if foto else ""
                        problema_final = problema + texto_evidencia
                        
                        c.execute("""INSERT INTO solicitudes 
                                     (fecha, solicitante, nombre_completo, cargo, seccion, salon, problema, impacto, estado) 
                                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                  (fecha, st.session_state['usuario'], nombre_completo, cargo, seccion, salon, problema_final, impacto, 'Pendiente'))
                        conn.commit()
                        st.success("Tu solicitud ha sido enviada a sistemas.")
        
        st.subheader("Mis Solicitudes Recientes")
        df_mis_solicitudes = pd.read_sql_query(
            "SELECT fecha, seccion, salon, problema, impacto, estado FROM solicitudes WHERE solicitante = ?", 
            conn, params=(st.session_state['usuario'],)
        )
        
        if not df_mis_solicitudes.empty:
            def colorear_estado(val):
                if val == 'Pendiente':
                    return 'background-color: #ffcccc; color: #900000; font-weight: bold;'
                elif val == 'Atendida':
                    return 'background-color: #ccffcc; color: #006600; font-weight: bold;'
                return ''
                
            st.dataframe(
                df_mis_solicitudes.style.map(colorear_estado, subset=['estado']),
                use_container_width=True, 
                hide_index=True
            )
        else:
            st.info("No hay solicitudes recientes registradas.")

    # --- PESTAÑA 2: Fila de Espera Global ---
    with tab2:
        st.subheader("Fila de Espera Actual")
        st.write("Consulta los reportes que están pendientes de atención por el equipo de Sistemas.")
        
        df_cola = pd.read_sql_query(
            "SELECT id, fecha, seccion, salon, impacto, estado FROM solicitudes WHERE estado = 'Pendiente' ORDER BY id ASC", 
            conn
        )
        
        if not df_cola.empty:
            df_cola.insert(0, 'Turno en Fila', range(1, 1 + len(df_cola)))
            
            df_mis_pendientes = pd.read_sql_query(
                "SELECT id FROM solicitudes WHERE solicitante = ? AND estado = 'Pendiente'", 
                conn, params=(st.session_state['usuario'],)
            )
            
            if not df_mis_pendientes.empty:
                mis_ids = df_mis_pendientes['id'].tolist()
                posiciones = df_cola[df_cola['id'].isin(mis_ids)]['Turno en Fila'].tolist()
                pos_str = ", ".join(map(str, posiciones))
                st.info(f"📍 **Tus reportes activos se encuentran en las posiciones: {pos_str} de la fila.**")
            
            df_mostrar = df_cola[['Turno en Fila', 'fecha', 'seccion', 'salon', 'impacto', 'estado']]
            st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
            
        else:
            st.success("¡Excelente! No hay fila de espera en este momento. El equipo de sistemas está libre.")

    # --- PESTAÑA 2: Fila de Espera Global ---
    with tab2:
        st.subheader("Fila de Espera Actual")
        st.write("Consulta los reportes que están pendientes de atención por el equipo de Sistemas.")
        
        # Consultamos todos los tickets pendientes ordenados por ID (el más antiguo primero)
        df_cola = pd.read_sql_query(
            "SELECT id, fecha, seccion, salon, impacto, estado FROM solicitudes WHERE estado = 'Pendiente' ORDER BY id ASC", 
            conn
        )
        
        if not df_cola.empty:
            # Agregamos una columna que representa el turno/posición en la fila (1, 2, 3...)
            df_cola.insert(0, 'Turno en Fila', range(1, 1 + len(df_cola)))
            
            # Verificamos si el usuario actual tiene tickets en esta fila
            df_mis_pendientes = pd.read_sql_query(
                "SELECT id FROM solicitudes WHERE solicitante = ? AND estado = 'Pendiente'", 
                conn, params=(st.session_state['usuario'],)
            )
            
            if not df_mis_pendientes.empty:
                mis_ids = df_mis_pendientes['id'].tolist()
                # Extraemos qué turnos le corresponden al usuario actual
                posiciones = df_cola[df_cola['id'].isin(mis_ids)]['Turno en Fila'].tolist()
                pos_str = ", ".join(map(str, posiciones))
                st.info(f"📍 **Tus reportes activos se encuentran en las posiciones: {pos_str} de la fila.**")
            
            # Mostramos la tabla pública ocultando el ID real de la base de datos para no confundir
            df_mostrar = df_cola[['Turno en Fila', 'fecha', 'seccion', 'salon', 'impacto', 'estado']]
            st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
            
        else:
            st.success("¡Excelente! No hay fila de espera en este momento. El equipo de sistemas está libre.")
    
    # --- MEJORA: Coloreado condicional de la tabla ---
    if not df_mis_solicitudes.empty:
        def colorear_estado(val):
            if val == 'Pendiente':
                return 'background-color: #ffcccc; color: #900000; font-weight: bold;'
            elif val == 'Atendida':
                return 'background-color: #ccffcc; color: #006600; font-weight: bold;'
            return ''
            
        st.dataframe(
            df_mis_solicitudes.style.map(colorear_estado, subset=['estado']),
            use_container_width=True, 
            hide_index=True
        )
    else:
        st.info("No hay solicitudes recientes registradas.")

def vista_admin():
    st.title("⚙️ Panel de Administrador de Sistemas")
    
    menu = st.sidebar.radio("Navegación", [
        "Dashboard Analítico", 
        "Bandeja de Solicitudes", 
        "Realizar Inspección Técnica", 
        "Base de Datos de Inspecciones"
    ])
    
    if menu == "Dashboard Analítico":
        st.subheader("📊 Métricas de Soporte")
        df_sol = pd.read_sql_query("SELECT * FROM solicitudes", conn)
        
        if not df_sol.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Total", len(df_sol))
            c2.metric("🔴 Pendientes", len(df_sol[df_sol['estado'] == 'Pendiente']))
            c3.metric("🟢 Atendidas", len(df_sol[df_sol['estado'] == 'Atendida']))
            
            st.markdown("---")
            with st.expander("📈 Ver Gráficas Detalladas", expanded=True):
                col_chart1, col_chart2 = st.columns(2)
                with col_chart1:
                    st.write("**Reportes por Sección**")
                    st.bar_chart(df_sol['seccion'].value_counts())
                with col_chart2:
                    st.write("**Niveles de Urgencia**")
                    st.bar_chart(df_sol['impacto'].value_counts())
        else:
            st.info("Sin datos para mostrar métricas.")

    elif menu == "Bandeja de Solicitudes":
        st.subheader("Bandeja de Solicitudes (Docentes)")
        df_sol = pd.read_sql_query("SELECT * FROM solicitudes", conn)
        
        if not df_sol.empty:
            # Menú desplegable para filtros y descarga
            with st.expander("🔍 Filtros de Búsqueda y Descarga", expanded=False):
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    filtro_estado = st.multiselect("Estado", df_sol['estado'].unique(), default=["Atendida"] if "Atendida" in df_sol['estado'].values else df_sol['estado'].unique())
                with col2:
                    df_sol['fecha_dt'] = pd.to_datetime(df_sol['fecha']).dt.date
                    fecha_reporte = st.date_input("Fecha de Reporte", value=datetime.now().date())
                
                df_filtrado = df_sol[(df_sol['estado'].isin(filtro_estado)) & (df_sol['fecha_dt'] == fecha_reporte)]
                
                with col3:
                    st.write("") 
                    st.write("")
                    if not df_filtrado.empty:
                        output = BytesIO()
                        df_excel = df_filtrado.drop(columns=['fecha_dt'])
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            df_excel.to_excel(writer, index=False, sheet_name='Reporte Diario')
                        st.download_button("📥 Excel", data=output.getvalue(), file_name=f"reporte_{fecha_reporte}.xlsx", type="primary", use_container_width=True)

            # Menú desplegable para cerrar tickets
            pendientes = df_filtrado[df_filtrado['estado'] == 'Pendiente']['id'].tolist() if not df_filtrado.empty else []
            if pendientes:
                with st.expander("✅ Atender / Cerrar Reporte", expanded=True):
                    with st.form("cerrar_solicitud"):
                        col_a, col_b = st.columns([3, 1])
                        with col_a:
                            sid = st.selectbox("ID del reporte a cerrar:", pendientes, index=None)
                        with col_b:
                            st.write("") 
                            st.write("")
                            if st.form_submit_button("Marcar Atendido", type="primary", use_container_width=True) and sid:
                                c.execute("UPDATE solicitudes SET estado = 'Atendida' WHERE id = ?", (sid,))
                                conn.commit()
                                st.rerun()

            # Visualización de la tabla
            if not df_filtrado.empty:
                def colorear_estado(val):
                    if val == 'Pendiente': return 'background-color: #ffcccc; color: #900000; font-weight: bold;'
                    elif val == 'Atendida': return 'background-color: #ccffcc; color: #006600; font-weight: bold;'
                    return ''
                st.dataframe(df_filtrado.drop(columns=['fecha_dt']).style.map(colorear_estado, subset=['estado']), use_container_width=True, hide_index=True)
            else:
                st.info("No hay coincidencias con los filtros aplicados.")
        else:
            st.info("No hay solicitudes registradas.")

    elif menu == "Realizar Inspección Técnica":
        st.subheader("Formulario de Inspección Física")
        opciones_estado = ["Funciona Correctamente", "Presenta fallas o requiere reparación", "Requiere cambio de equipo", "Faltante"]
        
        with st.form("nuevo_reporte", clear_on_submit=True):
            st.write("### 📍 1. Ubicación")
            c1, c2 = st.columns(2)
            salon = c1.text_input("Número o nombre del salón")
            seccion = c2.selectbox("Sección o edificio", ["Preescolar", "Primaria", "Secundaria", "Preparatoria", "Áreas Comunes", "Dirección"])
            
            st.write("### 💻 2. Revisión de Equipos")
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
                
            st.write("### 🛠️ 3. Acciones de Mantenimiento")
            req_reparacion = st.radio("¿Requiere reparación o cambio?", ["No", "Si"], horizontal=True)
            detalle_falla = st.text_area("Especificar falla (si aplica)")
            
            c_inv, c_baja, c_prio = st.columns(3)
            num_inventario = c_inv.text_input("Núm. Inventario")
            baja_inventario = c_baja.radio("¿Baja del inventario?", ["No", "Si"], horizontal=True)
            prioridad = c_prio.selectbox("Prioridad", ["1 (Baja)", "2 (Media)", "3 (Alta)"])
            
            if st.form_submit_button("✅ Registrar Inspección", type="primary"):
                if salon:
                    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    # Se extrae solo el número de la prioridad
                    prioridad_num = prioridad.split(" ")[0] 
                    c.execute("""INSERT INTO inspecciones 
                                 (fecha, tecnico, salon, seccion, eq_proyector, eq_cable, eq_hdmi, eq_pared_hdmi, 
                                  eq_ethernet, eq_pc, eq_impresora, req_reparacion, detalle_falla, num_inventario, 
                                  baja_inventario, prioridad, estado) 
                                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                              (fecha, st.session_state['usuario'], salon, seccion, eq_proyector, eq_cable, eq_hdmi, 
                               eq_pared_hdmi, eq_ethernet, eq_pc, eq_impresora, req_reparacion, detalle_falla, 
                               num_inventario, baja_inventario, prioridad_num, 'En revisión'))
                    conn.commit()
                    st.success("Inspección guardada exitosamente.")
                else:
                    st.error("El nombre del salón es obligatorio.")

    elif menu == "Base de Datos de Inspecciones":
        st.subheader("Historial Técnico")
        df_insp = pd.read_sql_query("SELECT * FROM inspecciones", conn)
        
        if not df_insp.empty:
            df_insp['fecha_dt'] = pd.to_datetime(df_insp['fecha']).dt.date
            
            # Menú desplegable para filtrado y exportación de historiales
            with st.expander("📅 Filtrar y Exportar Historial", expanded=True):
                col1, col2 = st.columns([2, 1])
                with col1:
                    rango_fechas = st.date_input("Filtrar por rango de fechas", value=(df_insp['fecha_dt'].min(), df_insp['fecha_dt'].max()))
                
                if len(rango_fechas) == 2:
                    df_filtrado = df_insp[(df_insp['fecha_dt'] >= rango_fechas[0]) & (df_insp['fecha_dt'] <= rango_fechas[1])]
                    df_mostrar = df_filtrado.drop(columns=['fecha_dt'])
                else:
                    df_mostrar = df_insp.drop(columns=['fecha_dt'])

                with col2:
                    st.write("")
                    st.write("")
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_mostrar.to_excel(writer, index=False, sheet_name='Inspecciones')
                    st.download_button("📥 Descargar Reporte Excel", data=output.getvalue(), file_name="inspecciones.xlsx", type="primary", use_container_width=True)
            
            st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
        else:
            st.info("Sin inspecciones registradas.")

# Flujo Principal
# --- MEJORA: Función para envío de correos (Google Workspace / Gmail) ---
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def notificar_por_correo(destinatario, salon, estado):
    """Envía un correo cuando el ticket cambia de estado."""
    try:
        remitente = st.secrets["email_sistemas"]
        password = st.secrets["email_pass"] # Contraseña de aplicación de Google
        
        msg = MIMEMultipart()
        msg['From'] = remitente
        msg['To'] = destinatario
        msg['Subject'] = f"🚨 Actualización de Soporte Técnico - Salón {salon}"
        
        cuerpo = f"Hola.\n\nEl reporte de soporte técnico para el salón/área {salon} ha cambiado su estado a: {estado}.\n\nSaludos,\nDepartamento de Sistemas\nInstituto Domingo Savio."
        msg.attach(MIMEText(cuerpo, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remitente, password)
        server.sendmail(remitente, destinatario, msg.as_string())
        server.quit()
    except Exception as e:
        # Falla silenciosa para que no interrumpa el uso de la app si el correo falla
        pass

# --- BLOQUE 5: Flujo Principal y Enrutamiento UI ---
if not st.session_state.get('usuario'):
    login()
else:
    # Diseño mejorado del Sidebar (Menú lateral)
    with st.sidebar:
        st.markdown("### 🏫 Instituto Domingo Savio")
        st.markdown("---")
        
        st.write("👤 **Usuario Activo:**")
        st.info(f"{st.session_state['usuario'].upper()}")
        
        st.write("🔑 **Nivel de Acceso:**")
        if st.session_state['rol'] == 'admin':
            st.success("Administrador de Sistemas")
        else:
            st.warning("Docente / Solicitante")
            
        st.markdown("---")
        
        # Botón de cierre de sesión destacado
        if st.button("🚪 Cerrar Sesión", use_container_width=True, type="primary"):
            st.session_state.update({'usuario': None, 'rol': None})
            st.rerun()
            
        st.markdown("<br><br><br><br><center><small>Sistema de Soporte v3.0</small></center>", unsafe_allow_html=True)
        
    # Enrutamiento de vistas según el rol
    if st.session_state['rol'] == 'admin':
        vista_admin()
    else:
        vista_solicitante()
