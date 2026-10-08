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
            c1.metric("Total de Solicitudes", len(df_sol))
            c2.metric("🔴 Pendientes", len(df_sol[df_sol['estado'] == 'Pendiente']))
            c3.metric("🟢 Atendidas", len(df_sol[df_sol['estado'] == 'Atendida']))
            
            st.markdown("---")
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                st.write("**Solicitudes por Sección (Edificios)**")
                conteo_seccion = df_sol['seccion'].value_counts()
                st.bar_chart(conteo_seccion)
                
            with col_chart2:
                st.write("**Nivel de Urgencia de los Reportes**")
                conteo_urgencia = df_sol['impacto'].value_counts()
                st.bar_chart(conteo_urgencia)
        else:
            st.info("No hay datos suficientes para mostrar métricas.")

    elif menu == "Bandeja de Solicitudes":
        st.subheader("Bandeja de Solicitudes (Docentes)")
        df_sol = pd.read_sql_query("SELECT * FROM solicitudes", conn)
        
        if not df_sol.empty:
            # Filtros para el reporte diario
            col1, col2 = st.columns(2)
            with col1:
                filtro_estado = st.multiselect(
                    "Filtrar por Estado", 
                    options=df_sol['estado'].unique(), 
                    default=["Atendida"] if "Atendida" in df_sol['estado'].values else df_sol['estado'].unique()
                )
            with col2:
                df_sol['fecha_dt'] = pd.to_datetime(df_sol['fecha']).dt.date
                fecha_reporte = st.date_input("Filtrar por Fecha (Reporte Diario)", value=datetime.now().date())
            
            # Aplicar filtros de búsqueda
            df_filtrado = df_sol[(df_sol['estado'].isin(filtro_estado)) & (df_sol['fecha_dt'] == fecha_reporte)]
            
            # Gestión para cerrar tickets pendientes
            pendientes = df_filtrado[df_filtrado['estado'] == 'Pendiente']['id'].tolist()
            if pendientes:
                with st.form("cerrar_solicitud"):
                    sid = st.selectbox("Selecciona ID de solicitud para marcar como Atendida", pendientes, index=None)
                    if st.form_submit_button("Marcar como Atendida") and sid:
                        c.execute("UPDATE solicitudes SET estado = 'Atendida' WHERE id = ?", (sid,))
                        conn.commit()
                        st.rerun()
            
            # Descarga del reporte en Excel
            if not df_filtrado.empty:
                output = BytesIO()
                df_excel = df_filtrado.drop(columns=['fecha_dt']) # Eliminamos la columna temporal
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_excel.to_excel(writer, index=False, sheet_name='Reporte Diario')
                
                st.download_button(
                    label=f"📥 Descargar Reporte Excel ({fecha_reporte})", 
                    data=output.getvalue(), 
                    file_name=f"reporte_tickets_{fecha_reporte}.xlsx",
                    mime="application/vnd.ms-excel"
                )
            
            def colorear_estado(val):
                if val == 'Pendiente':
                    return 'background-color: #ffcccc; color: #900000; font-weight: bold;'
                elif val == 'Atendida':
                    return 'background-color: #ccffcc; color: #006600; font-weight: bold;'
                return ''
                
            # Mostrar la tabla en pantalla
            st.dataframe(
                df_filtrado.drop(columns=['fecha_dt']).style.map(colorear_estado, subset=['estado']), 
                use_container_width=True, 
                hide_index=True
            )
        else:
            st.info("No hay solicitudes registradas en la base de datos.")

    elif menu == "Realizar Inspección Técnica":
        st.subheader("Formulario de Inspección Física")
        opciones_estado = ["Funciona Correctamente", "Presenta fallas o requiere reparación", "Requiere cambio de equipo", "Faltante"]
        
        with st.form("nuevo_reporte", clear_on_submit=True):
            c1, c2 = st.columns(2)
            salon = c1.text_input("Número o nombre del salón")
            seccion = c2.selectbox("Sección o edificio", ["Preescolar", "Primaria", "Secundaria", "Preparatoria", "Áreas Comunes", "Dirección"])
            
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
            # Convertimos la fecha de texto a un formato de fecha real para poder filtrar
            df_insp['fecha_dt'] = pd.to_datetime(df_insp['fecha']).dt.date
            
            # Selector de rango de fechas
            rango_fechas = st.date_input(
                "Filtrar por rango de fechas", 
                value=(df_insp['fecha_dt'].min(), df_insp['fecha_dt'].max())
            )
            
            # Validamos que el usuario haya seleccionado inicio y fin
            if len(rango_fechas) == 2:
                df_filtrado = df_insp[(df_insp['fecha_dt'] >= rango_fechas[0]) & (df_insp['fecha_dt'] <= rango_fechas[1])]
                df_mostrar = df_filtrado.drop(columns=['fecha_dt']) # Ocultamos la columna temporal
            else:
                df_mostrar = df_insp.drop(columns=['fecha_dt'])

            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_mostrar.to_excel(writer, index=False, sheet_name='Inspecciones')
            
            st.download_button(
                "📥 Descargar Reporte Excel", 
                data=output.getvalue(), 
                file_name="inspecciones_salones.xlsx"
            )
            
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
