import streamlit as st
import sqlite3
import pandas as pd

# Configuración de la página
st.set_page_config(page_title="Sistema de Asistencia Docente", page_icon="📚", layout="wide")

# --- CONEXIÓN A LA BASE DE DATOS ---
def conectar_db():
    conn = sqlite3.connect("asistencia.db", check_same_thread=False)
    return conn

def inicializar_db():
    conn = conectar_db()
    cursor = conn.cursor()

    # Tabla de Alumnos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alumnos (
            dni TEXT PRIMARY KEY,
            nombre TEXT,
            telefono TEXT,
            estado TEXT
        )
    """)

    # Tabla de Asistencias
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS asistencias (
            clase TEXT,
            dni TEXT,
            presente INTEGER,
            PRIMARY KEY (clase, dni)
        )
    """)

    # Alumnos de ejemplo si la tabla está vacía
    cursor.execute("SELECT COUNT(*) FROM alumnos")
    if cursor.fetchone()[0] == 0:
        alumnos_iniciales = [
            ("35123456", "Pérez, Juan", "3884123456", "Activo"),
            ("32987654", "Gómez, María", "3884987654", "Activo"),
            ("38456123", "López, Carlos", "3884456123", "Activo")
        ]
        cursor.executemany("INSERT OR IGNORE INTO alumnos VALUES (?, ?, ?, ?)", alumnos_iniciales)

    conn.commit()
    conn.close()

inicializar_db()

# --- INTERFAZ VISUAL (TABS / PESTAÑAS) ---
st.title("📚 Sistema de Asistencia Docente")
st.markdown("Gestión integrada de alumnos, registro de clases y reportes visuales.")

tab1, tab2, tab3 = st.tabs(["👥 Gestión de Alumnos", "✅ Tomar Asistencia", "📊 Reportes y Gráficos"])

# ==========================================
# PESTAÑA 1: GESTIÓN DE ALUMNOS
# ==========================================
with tab1:
    st.header("Directorio de Alumnos")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Agregar o Actualizar Alumno")
        with st.form("form_alumno"):
            dni_in = st.text_input("DNI del Alumno").strip()
            nombre_in = st.text_input("Apellido y Nombre").strip()
            tel_in = st.text_input("Teléfono de contacto").strip()
            estado_in = st.selectbox("Estado", ["Activo", "Inactivo"])
            
            submit_alu = st.form_submit_button("Guardar Alumno")
            
            if submit_alu:
                if dni_in and nombre_in:
                    conn = conectar_db()
                    cursor = conn.cursor()
                    cursor.execute("INSERT OR REPLACE INTO alumnos VALUES (?, ?, ?, ?)", 
                                   (dni_in, nombre_in, tel_in, estado_in))
                    conn.commit()
                    conn.close()
                    st.success(f"¡Alumno {nombre_in} guardado con éxito!")
                    st.rerun()
                else:
                    st.error("Por favor completa al menos el DNI y el Nombre.")

    with col2:
        st.subheader("Listado Actual")
        conn = conectar_db()
        df_alumnos = pd.read_sql("SELECT dni AS DNI, nombre AS 'Apellido y Nombre', telefono AS Teléfono, estado AS Estado FROM alumnos", conn)
        conn.close()
        
        if not df_alumnos.empty:
            st.dataframe(df_alumnos, use_container_width=True)
            
            # Opción para eliminar alumno
            dni_del = st.selectbox("Seleccionar DNI para eliminar", options=[""] + list(df_alumnos["DNI"]))
            if dni_del:
                if st.button("🗑️ Eliminar Alumno Seleccionado"):
                    conn = conectar_db()
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM alumnos WHERE dni = ?", (dni_del,))
                    cursor.execute("DELETE FROM asistencias WHERE dni = ?", (dni_del,))
                    conn.commit()
                    conn.close()
                    st.warning(f"Alumno con DNI {dni_del} eliminado correctamente.")
                    st.rerun()
        else:
            st.info("No hay alumnos registrados.")

# ==========================================
# PESTAÑA 2: TOMAR ASISTENCIA
# ==========================================
with tab2:
    st.header("Registro de Asistencia por Clase")
    
    clase_sel = st.selectbox("Selecciona o escribe la clase:", ["Clase 1", "Clase 2", "Clase 3", "Clase 4", "Clase 5", "Clase 6"])
    
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT dni, nombre FROM alumnos WHERE estado = 'Activo'")
    alumnos_activos = cursor.fetchall()
    conn.close()
    
    if alumnos_activos:
        st.markdown(f"### Marcando asistencia para: **{clase_sel}**")
        with st.form("form_asistencia"):
            asistencias_dict = {}
            for dni, nombre in alumnos_activos:
                # Consultar estado previo
                conn = conectar_db()
                cursor = conn.cursor()
                cursor.execute("SELECT presente FROM asistencias WHERE clase = ? AND dni = ?", (clase_sel, dni))
                res = cursor.fetchone()
                conn.close()
                
                val_inicial = True if res and res[0] == 1 else False
                asistencias_dict[dni] = st.checkbox(f"{nombre} (DNI: {dni})", value=val_inicial)
                
            submit_asis = st.form_submit_button("💾 Guardar Asistencia de la Clase")
            
            if submit_asis:
                conn = conectar_db()
                cursor = conn.cursor()
                for dni, presente in asistencias_dict.items():
                    val = 1 if presente else 0
                    cursor.execute("INSERT OR REPLACE INTO asistencias (clase, dni, presente) VALUES (?, ?, ?)", 
                                   (clase_sel, dni, val))
                conn.commit()
                conn.close()
                st.success("¡Asistencias guardadas correctamente!")
    else:
        st.warning("No hay alumnos activos para registrar asistencia.")

# ==========================================
# PESTAÑA 3: REPORTES Y GRÁFICOS
# ==========================================
with tab3:
    st.header("Reportes y Estadísticas")
    
    conn = conectar_db()
    # Consulta general cruzando alumnos y asistencias
    query = """
        SELECT a.dni AS DNI, a.nombre AS 'Apellido y Nombre', asis.clase AS Clase, asis.presente AS Presente
        FROM alumnos a
        LEFT JOIN asistencias asis ON a.dni = asis.dni
        WHERE a.estado = 'Activo'
    """
    df_reporte = pd.read_sql(query, conn)
    conn.close()
    
    if not df_reporte.empty and df_reporte["Clase"].notna().any():
        # Tabla pivote para ver mejor el panorama
        df_pivot = df_reporte.pivot_table(index=["DNI", "Apellido y Nombre"], columns="Clase", values="Presente", fill_value=0)
        df_pivot = df_pivot.replace({1: "Presente ✅", 0: "Ausente ❌"})
        
        st.subheader("Planilla General de Asistencias")
        st.dataframe(df_pivot, use_container_width=True)
        
        # Gráfico simple de asistencia por clase
        st.subheader("📊 Porcentaje de Presentismo por Clase")
        df_grafico = df_reporte.groupby("Clase")["Presente"].mean() * 100
        st.bar_chart(df_grafico)
        
        # Botón para exportar a CSV descargable
        csv_data = df_pivot.to_csv().encode('utf-8')
        st.download_button(
            label="📥 Descargar Reporte en CSV",
            data=csv_data,
            file_name="reporte_asistencia_general.csv",
            mime="text/csv",
        )
    else:
        st.info("Aún no hay registros de asistencia cargados para mostrar reportes o gráficos.")