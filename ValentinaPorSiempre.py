import streamlit as st
import pandas as pd
from datetime import date, datetime
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment, PatternFill
from pathlib import Path
import base64, os
from supabase import create_client
from dotenv import load_dotenv

# ==========================================================
#                 LOAD ENVIRONMENT VARIABLES
# ==========================================================
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://uumezwowrtumbonsotyc.supabase.co")
SUPABASE_KEY = os.getenv(
    "SUPABASE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================================
#           ENSURE last_edit TABLE EXISTS
# ==========================================================
def ensure_last_edit_table():
    try:
        supabase.table("last_edit").select("id").limit(1).execute()
    except Exception:
        try:
            supabase.rpc("execute_sql", {
                "sql": """
                create table if not exists public.last_edit (
                    id bigint primary key,
                    user_name text,
                    timestamp timestamptz default now()
                );
                """
            }).execute()
        except Exception as e:
            st.warning(f"No se pudo verificar/crear la tabla last_edit: {e}")

ensure_last_edit_table()

# ==========================================================
#               PAGE CONFIGURATION
# ==========================================================
st.set_page_config(
    page_title="Valentina por Siempre",
    page_icon="VxS_logo.png",
    layout="wide"
)

# ==========================================================
#               LAST EDIT HELPERS
# ==========================================================
def update_last_edit(user_name):
    try:
        now = datetime.now().isoformat()
        supabase.table("last_edit").upsert({
            "id": 1, "user_name": user_name, "timestamp": now
        }).execute()
    except Exception as e:
        st.warning(f"⚠️ No se pudo actualizar el registro de edición en Supabase: {e}")

def get_last_edit():
    try:
        result = supabase.table("last_edit").select("*").eq("id", 1).execute()
        if result.data:
            rec = result.data[0]
            return rec.get("user_name"), rec.get("timestamp")
    except Exception:
        pass
    return None, None

# ==========================================================
#                 ACCESS CONTROL (LOGIN)
# ==========================================================
if "authenticated" not in st.session_state:
    st.session_state.update({"authenticated": False, "user_name": ""})

if not st.session_state.authenticated:
    st.sidebar.title("🔐 Ingreso")
    user_key = st.sidebar.text_input("Introduce tu clave de acceso:", type="password")

    AUTHORIZED_KEYS = {"equipo_vxs": None, "valentina_master": "Andrea"}

    if user_key not in AUTHORIZED_KEYS:
        st.warning("Por favor, introduce la clave de acceso para continuar.")
        st.stop()

    user_name = AUTHORIZED_KEYS[user_key] or st.sidebar.text_input("Tu nombre (para registrar ediciones):")
    if not user_name:
        st.info("Por favor, escribe tu nombre para continuar.")
        st.stop()

    if st.sidebar.button("Ingresar"):
        st.session_state.update({"authenticated": True, "user_name": user_name})
        st.rerun()

# ==========================================================
#                 STYLES & LOGO
# ==========================================================
def load_logo_base64(path: str):
    if Path(path).exists():
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

logo_b64 = load_logo_base64("VxS_logo.png")

st.markdown(f"""
    <style>
    .main {{ background-color: #f7f5f2 !important; }}
    .custom-title {{
        text-align: center; color: #352208;
        font-size: 48px; font-weight: 800;
        margin: -5px 0 15px;
    }}
    .corner-image {{
        position: fixed; top: 80px; right: 25px;
        width: 90px; border-radius: 50%;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.2);
        z-index: 999;
    }}
    .bottom-left {{
        position: fixed; bottom: 10px; left: 15px;
        color: #666; font-size: 14px;
        background-color: rgba(255,255,255,0.8);
        padding: 5px 10px; border-radius: 8px;
    }}
    /* Auto-fit table cells */
    [data-testid="stDataFrame"] div[data-testid="stHorizontalBlock"] div[role="gridcell"] {{
        white-space: normal !important;
        overflow-wrap: anywhere !important;
        word-break: break-word !important;
    }}
    </style>
    {'<img src="data:image/png;base64,' + logo_b64 + '" class="corner-image">' if logo_b64 else ''}
""", unsafe_allow_html=True)

st.markdown("<h1 class='custom-title'>💛 Valentina por Siempre</h1>", unsafe_allow_html=True)

# ==========================================================
#                 HELPER FUNCTIONS
# ==========================================================
def calculate_age(dob):
    if isinstance(dob, str):
        try:
            dob = datetime.strptime(dob, "%Y-%m-%d").date()
        except Exception:
            return None
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

def style_excel(df, filename):
    for col in ["fecha_nacimiento", "fecha_ultimo_apoyo"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.date

    df.to_excel(filename, index=False)
    wb = load_workbook(filename)
    ws = wb.active

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="ff8330")
    header_alignment = Alignment(horizontal="center", vertical="center")

    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
    ws.freeze_panes = "A2"

    paliativos_col = next((i for i, c in enumerate(ws[1], 1) if c.value == "cuidados_paliativos"), None)
    paliativos_fill = PatternFill("solid", fgColor="FFAB66")

    if paliativos_col:
        for row in ws.iter_rows(min_row=2):
            if row[paliativos_col - 1].value in (1, True, "1", "true", "True"):
                for cell in row:
                    cell.fill = paliativos_fill

    wb.save(filename)

# ==========================================================
#                 MAIN INTERFACE
# ==========================================================
if st.session_state.authenticated:
    page = st.sidebar.radio(
        "Navegación",
        ["➕ Agregar Paciente", "🖊️ Editar Paciente", "📋 Ver Pacientes", "🎂 Cumpleaños"]
    )

    # ---------------- ADD PATIENT ----------------
    if page == "➕ Agregar Paciente":
        st.subheader("Ingresar nuevo paciente")
        with st.form("add_patient_form"):
            nombre = st.text_input("Nombre del paciente")
            fecha_nacimiento = st.date_input("Fecha de nacimiento", min_value=date(1900, 1, 1))
            nombre_tutor = st.text_input("Nombre del tutor")
            diagnostico = st.text_input("Diagnóstico")
            etapa_tratamiento = st.selectbox("Etapa del tratamiento", [
                "Diagnóstico inicial", "En tratamiento", "En vigilancia", "Cuidados paliativos"
            ])
            hospital = st.text_input("Hospital")
            estado_origen = st.text_input("Estado de origen")
            telefono_contacto = st.text_input("Celular de contacto")
            apoyos_entregados = st.text_input("Apoyos entregados")
            fecha_ultimo_apoyo = st.date_input("Fecha del último apoyo", value=None)
            notas = st.text_area("Notas")
            estado = st.selectbox("Estado del paciente", ["activo", "vigilancia", "fallecido"])
            cuidados_paliativos = st.checkbox("¿Está en cuidados paliativos?")
            submitted = st.form_submit_button("Agregar paciente")

            if submitted:
                data = {
                    "nombre": nombre,
                    "fecha_nacimiento": str(fecha_nacimiento),
                    "nombre_tutor": nombre_tutor,
                    "diagnostico": diagnostico,
                    "etapa_tratamiento": etapa_tratamiento,
                    "hospital": hospital,
                    "estado_origen": estado_origen,
                    "telefono_contacto": telefono_contacto,
                    "apoyos_entregados": apoyos_entregados,
                    "fecha_ultimo_apoyo": str(fecha_ultimo_apoyo) if fecha_ultimo_apoyo else None,
                    "notas": notas,
                    "estado": estado,
                    "cuidados_paliativos": cuidados_paliativos
                }
                supabase.table("pacientes").insert(data).execute()
                update_last_edit(st.session_state.user_name)
                st.success(f"✅ Paciente agregado exitosamente por {st.session_state.user_name}.")

    # ---------------- EDIT PATIENT ----------------
    elif page == "🖊️ Editar Paciente":
        st.subheader("Editar información de paciente existente")
        data = supabase.table("pacientes").select("*").execute()
        df = pd.DataFrame(data.data)

        if df.empty:
            st.info("No hay pacientes para editar.")
        else:
            df = df.sort_values(by="id", ascending=True)
            selected_name = st.selectbox("Selecciona un paciente para editar", df["nombre"].tolist())
            patient = df[df["nombre"] == selected_name].iloc[0]

            with st.form("edit_patient_form"):
                nombre_tutor = st.text_input("Nombre del tutor", value=patient["nombre_tutor"])
                diagnostico = st.text_input("Diagnóstico", value=patient["diagnostico"])
                etapa_tratamiento = st.selectbox(
                    "Etapa del tratamiento",
                    ["Diagnóstico inicial", "En tratamiento", "En vigilancia", "Cuidados paliativos"],
                    index=["Diagnóstico inicial", "En tratamiento", "En vigilancia", "Cuidados paliativos"].index(patient["etapa_tratamiento"])
                )
                hospital = st.text_input("Hospital", value=patient["hospital"])
                estado_origen = st.text_input("Estado de origen", value=patient["estado_origen"])
                telefono_contacto = st.text_input("Celular de contacto", value=patient["telefono_contacto"])
                apoyos_entregados = st.text_input("Apoyos entregados", value=patient["apoyos_entregados"])
                notas = st.text_area("Notas", value=patient["notas"])
                estado = st.selectbox("Estado del paciente", ["activo", "vigilancia", "fallecido"],
                    index=["activo", "vigilancia", "fallecido"].index(patient["estado"]))
                cuidados_paliativos = st.checkbox("¿Está en cuidados paliativos?", value=patient["cuidados_paliativos"])
                submitted_edit = st.form_submit_button("💾 Guardar cambios")

                if submitted_edit:
                    update_data = {
                        "nombre_tutor": nombre_tutor,
                        "diagnostico": diagnostico,
                        "etapa_tratamiento": etapa_tratamiento,
                        "hospital": hospital,
                        "estado_origen": estado_origen,
                        "telefono_contacto": telefono_contacto,
                        "apoyos_entregados": apoyos_entregados,
                        "notas": notas,
                        "estado": estado,
                        "cuidados_paliativos": cuidados_paliativos
                    }
                    supabase.table("pacientes").update(update_data).eq("nombre", selected_name).execute()
                    update_last_edit(st.session_state.user_name)
                    st.success("✅ Cambios guardados correctamente.")
                    st.rerun()

    # ---------------- VIEW PATIENTS ----------------
    elif page == "📋 Ver Pacientes":
        st.subheader("❤️‍🩹 Lista de pacientes")
        col1, col2, col3 = st.columns(3)
        with col1: act = st.checkbox("Activo", True)
        with col2: vig = st.checkbox("Vigilancia", False)
        with col3: fall = st.checkbox("Fallecido", False)
        search = st.text_input("🔍 Buscar paciente por nombre o diagnóstico")

        estados = [s for s, f in zip(["activo", "vigilancia", "fallecido"], [act, vig, fall]) if f]
        if not estados:
            st.info("Selecciona al menos un estado.")
            st.stop()

        data = supabase.table("pacientes").select("*").in_("estado", estados).execute()
        df = pd.DataFrame(data.data)

        if not df.empty:
            df = df.sort_values(by="id", ascending=True)
            if search:
                df = df[df["nombre"].str.contains(search, case=False, na=False) |
                        df["diagnostico"].str.contains(search, case=False, na=False)]
            df["fecha_nacimiento"] = pd.to_datetime(df["fecha_nacimiento"], errors="coerce").dt.date
            df["Edad"] = df["fecha_nacimiento"].apply(calculate_age)

            st.dataframe(
                df.style.apply(lambda r: [
                    "background-color: #FFAB66" if r["cuidados_paliativos"] in [1, True, "1", "true", "True"] else ""
                ] * len(r), axis=1),
                use_container_width=True
            )

            delete_name = st.text_input("Nombre exacto del paciente a eliminar:")
            if st.button("🗑️ Eliminar paciente"):
                if delete_name.strip():
                    supabase.table("pacientes").delete().eq("nombre", delete_name.strip()).execute()
                    update_last_edit(st.session_state.user_name)
                    st.success(f"🗑️ Paciente '{delete_name}' eliminado correctamente.")
                    st.rerun()
                else:
                    st.warning("Escribe el nombre exacto del paciente para eliminarlo.")

            if st.button("📥 Exportar a Excel"):
                filename = "pacientes_valentina.xlsx"
                style_excel(df, filename)
                with open(filename, "rb") as f:
                    st.download_button("Descargar archivo Excel", data=f, file_name=filename, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.info("No hay pacientes registrados con ese estado.")

    # ---------------- BIRTHDAYS ----------------
    elif page == "🎂 Cumpleaños":
        st.subheader("Cumpleaños del mes y del próximo mes")
        MONTHS_ES = {
            "January": "enero", "February": "febrero", "March": "marzo",
            "April": "abril", "May": "mayo", "June": "junio",
            "July": "julio", "August": "agosto", "September": "septiembre",
            "October": "octubre", "November": "noviembre", "December": "diciembre"
        }
        data = supabase.table("pacientes").select("*").neq("estado", "fallecido").execute()
        df = pd.DataFrame(data.data)
        if not df.empty:
            df["fecha_nacimiento"] = pd.to_datetime(df["fecha_nacimiento"], errors="coerce").dt.date
            current_month = datetime.today().month
            next_month = (current_month % 12) + 1
            df["Edad"] = df["fecha_nacimiento"].apply(calculate_age)

            df_this = df[pd.to_datetime(df["fecha_nacimiento"]).dt.month == current_month]
            df_next = df[pd.to_datetime(df["fecha_nacimiento"]).dt.month == next_month]

            st.markdown(f"### 🎉 Cumpleaños de **{MONTHS_ES[datetime.today().strftime('%B')]}**")
            st.dataframe(df_this[["nombre", "fecha_nacimiento", "Edad", "estado"]])

            next_month_name = MONTHS_ES[datetime(datetime.today().year, next_month, 1).strftime("%B")]
            st.markdown(f"### 🎈 Cumpleaños de **{next_month_name}**")
            st.dataframe(df_next[["nombre", "fecha_nacimiento", "Edad", "estado"]])
        else:
            st.info("No hay pacientes registrados.")

    # ---------------- FOOTER ----------------
    last_user, last_time = get_last_edit()
    if last_user and last_time:
        try:
            formatted = datetime.fromisoformat(last_time).strftime("%d/%m/%Y %H:%M")
        except Exception:
            formatted = last_time
        st.sidebar.markdown(
            f"<div class='bottom-left'>Última edición por <b>{last_user}</b> el {formatted}</div>",
            unsafe_allow_html=True
        )
