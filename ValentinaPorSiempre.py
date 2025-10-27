# ValentinaPorSiempre.py
import streamlit as st
import pandas as pd
from datetime import date, datetime
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment, PatternFill
from pathlib import Path
import base64
from dotenv import load_dotenv
import os

# Supabase client
from supabase import create_client

# ------------------------
# CONFIG / ENV
# ------------------------
load_dotenv()  # prefer using .env but fallback values included
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://uumezwowrtumbonsotyc.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Valentina por Siempre", page_icon="💛", layout="wide")

# ------------------------
# Helpers: logo, age
# ------------------------
def load_logo_base64(path: str):
    p = Path(path)
    if p.exists():
        with open(p, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

def calculate_age(dob):
    if pd.isna(dob):
        return ""
    if isinstance(dob, str):
        dob = pd.to_datetime(dob, errors="coerce")
    if pd.isna(dob):
        return ""
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

# ------------------------
# Last-edit helpers (separate table in Supabase)
# ------------------------
def update_last_edit(user_name):
    """Upsert row id=1 in last_edit table with user and timestamp."""
    now = datetime.now().isoformat()
    try:
        supabase.table("last_edit").upsert({
            "id": 1,
            "user_name": user_name,
            "timestamp": now
        }).execute()
    except Exception as e:
        # Do not crash the app for tracking errors; show a small message in logs
        st.error("No se pudo actualizar 'Última edición' (ver logs).")
        print("update_last_edit error:", e)

def get_last_edit():
    try:
        res = supabase.table("last_edit").select("*").eq("id", 1).execute()
        if res.data and len(res.data) > 0:
            rec = res.data[0]
            return rec.get("user_name"), rec.get("timestamp")
    except Exception as e:
        print("get_last_edit error:", e)
    return None, None

# ------------------------
# Excel styling/export
# ------------------------
def style_excel(df: pd.DataFrame, filename: str):
    # Remove any columns we don't want in excel (none currently)
    df_to_save = df.copy()

    # Ensure date-only (no time) for these columns
    for col in ["fecha_nacimiento", "fecha_ultimo_apoyo"]:
        if col in df_to_save.columns:
            df_to_save[col] = pd.to_datetime(df_to_save[col], errors="coerce").dt.date

    df_to_save.to_excel(filename, index=False)

    wb = load_workbook(filename)
    ws = wb.active

    # Column widths (auto-friendly defaults)
    widths = {
        1: 20, 2: 15, 3: 25, 4: 30, 5: 20,
        6: 20, 7: 25, 8: 20, 9: 20, 10: 30
    }
    for col_idx, w in widths.items():
        try:
            ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = w
        except Exception:
            pass

    # Header formatting
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="FF8330")
    header_alignment = Alignment(horizontal="center", vertical="center")
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment

    # Freeze top row
    ws.freeze_panes = "A2"

    # Highlight palliative rows (search header for column name)
    pali_col_idx = None
    for idx, cell in enumerate(ws[1], start=1):
        if cell.value == "cuidados_paliativos":
            pali_col_idx = idx
            break
    if pali_col_idx:
        pali_fill = PatternFill("solid", fgColor="FFAB66")  # palliative highlight
        for r in ws.iter_rows(min_row=2, max_row=ws.max_row):
            val = r[pali_col_idx - 1].value
            if val in (1, True, "1", "true", "True"):
                for c in r:
                    c.fill = pali_fill

    wb.save(filename)

# ------------------------
# UI: Authentication
# ------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_name = ""

if not st.session_state.authenticated:
    st.sidebar.title("🔐 Ingreso")
    user_key = st.sidebar.text_input("Clave de acceso:", type="password")
    AUTHORIZED_KEYS = {
        "equipo_vxs": None,            # normal users must type their name
        "valentina_master": "Andrea"   # master key auto-fills name
    }
    if user_key not in AUTHORIZED_KEYS:
        st.sidebar.info("Introduce la clave para continuar.")
        st.stop()

    if AUTHORIZED_KEYS[user_key] is None:
        user_name_input = st.sidebar.text_input("Tu nombre (para registrar ediciones):")
        if not user_name_input:
            st.sidebar.info("Escribe tu nombre para continuar.")
            st.stop()
        chosen_user = user_name_input
    else:
        chosen_user = AUTHORIZED_KEYS[user_key]

    if st.sidebar.button("Ingresar"):
        st.session_state.authenticated = True
        st.session_state.user_name = chosen_user
        # show last edit from DB after login
        st.experimental_rerun()

# ------------------------
# Styles + Logo + Title
# ------------------------
logo_b64 = load_logo_base64("VxS_logo.png")
st.markdown(
    f"""
    <style>
    .main {{ background-color: #f7f5f2 !important; }}
    .custom-title {{ text-align:center; color:#352208; font-size:42px; margin-top:0; margin-bottom:10px; }}
    .corner-image {{ position: fixed; top: 80px; right: 25px; width: 90px; border-radius:50%; z-index:999; box-shadow:0 4px 10px rgba(0,0,0,0.2); }}
    .bottom-left {{ position: fixed; bottom: 10px; left: 15px; color: #666; font-size:13px; background: rgba(255,255,255,0.85); padding:6px 10px; border-radius:8px; }}
    </style>
    {('<img src="data:image/png;base64,' + logo_b64 + '" class="corner-image">' ) if logo_b64 else ''}
    """,
    unsafe_allow_html=True
)
st.markdown("<h1 class='custom-title'>💛 Valentina por Siempre</h1>", unsafe_allow_html=True)

# ------------------------
# Main App (after auth)
# ------------------------
if st.session_state.authenticated:
    # Sidebar navigation
    page = st.sidebar.radio("Navegación", ["➕ Agregar Paciente", "📋 Ver Pacientes", "🎂 Cumpleaños"])

    # ---------------- ADD ----------------
    if page == "➕ Agregar Paciente":
        st.subheader("📌 Ingresar nuevo paciente")
        with st.form("add_patient"):
            nombre = st.text_input("Nombre del paciente")
            # allow very old dates
            fecha_nacimiento = st.date_input("Fecha de nacimiento", min_value=date(1900, 1, 1))
            nombre_tutor = st.text_input("Nombre del tutor")
            diagnostico = st.text_input("Diagnóstico")
            etapa_tratamiento = st.selectbox("Etapa del tratamiento", ["Diagnóstico inicial", "En tratamiento", "En vigilancia", "Cuidados paliativos"])
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
                payload = {
                    "nombre": nombre,
                    "fecha_nacimiento": fecha_nacimiento.isoformat(),
                    "nombre_tutor": nombre_tutor,
                    "diagnostico": diagnostico,
                    "etapa_tratamiento": etapa_tratamiento,
                    "hospital": hospital,
                    "estado_origen": estado_origen,
                    "telefono_contacto": telefono_contacto,
                    "apoyos_entregados": apoyos_entregados,
                    "fecha_ultimo_apoyo": fecha_ultimo_apoyo.isoformat() if fecha_ultimo_apoyo else None,
                    "notas": notas,
                    "estado": estado,
                    "cuidados_paliativos": cuidados_paliativos
                }
                try:
                    supabase.table("pacientes").insert(payload).execute()
                    update_last_edit(st.session_state.user_name)
                    st.success(f"✅ Paciente agregado por {st.session_state.user_name}")
                    # refresh to show new data
                    try:
                        st.experimental_rerun()
                    except Exception:
                        st.rerun()
                except Exception as e:
                    st.error("Error agregando paciente (ver consola).")
                    print("Insert error:", e)

    # ---------------- VIEW / DELETE ----------------
    elif page == "📋 Ver Pacientes":
        st.subheader("👩‍⚕️ Lista de pacientes")

        # Multi-checkbox filter for estados
        st.markdown("**Filtrar por estado**")
        c1, c2, c3 = st.columns(3)
        with c1:
            f_activo = st.checkbox("activo", value=True)
        with c2:
            f_vigilancia = st.checkbox("vigilancia", value=False)
        with c3:
            f_fallecido = st.checkbox("fallecido", value=False)

        selected_states = []
        if f_activo: selected_states.append("activo")
        if f_vigilancia: selected_states.append("vigilancia")
        if f_fallecido: selected_states.append("fallecido")
        if not selected_states:
            st.info("Selecciona al menos un estado para mostrar pacientes.")
            st.stop()

        search = st.text_input("🔍 Buscar por nombre o diagnóstico")

        # Fetch from supabase
        try:
            query_res = supabase.table("pacientes").select("*").in_("estado", selected_states).execute()
            df = pd.DataFrame(query_res.data or [])
        except Exception as e:
            st.error("Error leyendo pacientes (ver consola).")
            print("Select error:", e)
            df = pd.DataFrame([])

        if not df.empty:
            # convert date strings to datetimes, remove times for display
            if "fecha_nacimiento" in df.columns:
                df["fecha_nacimiento"] = pd.to_datetime(df["fecha_nacimiento"], errors="coerce").dt.date
            if "fecha_ultimo_apoyo" in df.columns:
                df["fecha_ultimo_apoyo"] = pd.to_datetime(df["fecha_ultimo_apoyo"], errors="coerce").dt.date

            # search filter
            if search:
                mask = df["nombre"].str.contains(search, case=False, na=False) | df["diagnostico"].str.contains(search, case=False, na=False)
                df = df.loc[mask]

            # compute age (safe)
            if "fecha_nacimiento" in df.columns:
                df["Edad"] = df["fecha_nacimiento"].apply(lambda d: calculate_age(pd.to_datetime(d) if not pd.isna(d) else pd.NaT))

            # Styling: highlight paliativos rows with background color #FFAB66
            def highlight_pali(row):
                try:
                    if row.get("cuidados_paliativos") in (1, True, "1", "true", "True"):
                        return ['background-color: #FFAB66'] * len(row)
                except Exception:
                    pass
                return [''] * len(row)

            # Show dataframe with styling
            st.write("Resultados:")
            st.dataframe(df.style.apply(highlight_pali, axis=1), use_container_width=True)

            # Delete UI
            st.markdown("---")
            st.markdown("### 🗑️ Eliminar paciente")
            patient_ids = df["id"].tolist()
            selected_id = st.selectbox("Selecciona ID a eliminar", options=patient_ids, key="del_select")
            if st.button("Eliminar paciente"):
                # show confirmation buttons
                st.session_state[f"confirm_del_{selected_id}"] = True

            if st.session_state.get(f"confirm_del_{selected_id}", False):
                st.warning(f"⚠️ Confirma eliminación del paciente ID {selected_id}")
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("✅ Sí, eliminar", key=f"yes_{selected_id}"):
                        try:
                            supabase.table("pacientes").delete().eq("id", int(selected_id)).execute()
                            update_last_edit(st.session_state.user_name)
                            st.success(f"Paciente {selected_id} eliminado.")
                            # clear flag & refresh
                            st.session_state.pop(f"confirm_del_{selected_id}", None)
                            try: st.experimental_rerun()
                            except Exception: st.rerun()
                        except Exception as e:
                            st.error("Error eliminando (ver consola).")
                            print("Delete error:", e)
                with col_no:
                    if st.button("❌ Cancelar", key=f"no_{selected_id}"):
                        st.session_state.pop(f"confirm_del_{selected_id}", None)
                        st.info("Operación cancelada.")

            # Export to Excel
            if st.button("📥 Exportar a Excel"):
                filename = "pacientes_valentina.xlsx"
                style_excel(df, filename)
                with open(filename, "rb") as f:
                    st.download_button("Descargar Excel", data=f, file_name=filename, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.info("No hay pacientes para los filtros seleccionados.")

    # ---------------- BIRTHDAYS ----------------
    elif page == "🎂 Cumpleaños":
        st.subheader("🎉 Cumpleaños - este mes y el próximo")
        # Spanish month names map
        MONTHS_ES = {
            "January": "enero", "February": "febrero", "March": "marzo",
            "April": "abril", "May": "mayo", "June": "junio",
            "July": "julio", "August": "agosto", "September": "septiembre",
            "October": "octubre", "November": "noviembre", "December": "diciembre"
        }
        try:
            q = supabase.table("pacientes").select("*").neq("estado", "fallecido").execute()
            df = pd.DataFrame(q.data or [])
        except Exception as e:
            st.error("Error leyendo pacientes (ver consola).")
            print("Birthday select error:", e)
            df = pd.DataFrame([])

        if not df.empty:
            df["fecha_nacimiento"] = pd.to_datetime(df["fecha_nacimiento"], errors="coerce")
            today = datetime.today()
            current_month = today.month
            next_month = (current_month % 12) + 1

            df["Edad"] = df["fecha_nacimiento"].apply(lambda d: calculate_age(d) if not pd.isna(d) else "")

            df_this = df[df["fecha_nacimiento"].dt.month == current_month]
            df_next = df[df["fecha_nacimiento"].dt.month == next_month]

            name_this = MONTHS_ES[today.strftime("%B")]
            name_next = MONTHS_ES[datetime(today.year, next_month, 1).strftime("%B")]

            st.markdown(f"### 🎉 Cumpleaños de {name_this.capitalize()}")
            if not df_this.empty:
                df_this_display = df_this.copy()
                df_this_display["fecha_nacimiento"] = df_this_display["fecha_nacimiento"].dt.date
                st.dataframe(df_this_display[["nombre", "fecha_nacimiento", "Edad", "estado"]], use_container_width=True)
            else:
                st.info("No hay cumpleaños este mes.")

            st.markdown(f"### 🎈 Cumpleaños de {name_next.capitalize()}")
            if not df_next.empty:
                df_next_display = df_next.copy()
                df_next_display["fecha_nacimiento"] = df_next_display["fecha_nacimiento"].dt.date
                st.dataframe(df_next_display[["nombre", "fecha_nacimiento", "Edad", "estado"]], use_container_width=True)
            else:
                st.info("No hay cumpleaños el próximo mes.")
        else:
            st.info("No hay pacientes registrados.")

    # ---------------- Footer: Last edit (bottom-left style via sidebar) ----------------
    last_user, last_time = get_last_edit()
    if last_user and last_time:
        try:
            formatted = datetime.fromisoformat(last_time).strftime("%d/%m/%Y %H:%M")
        except Exception:
            formatted = last_time
        st.sidebar.markdown(f"<div class='bottom-left'>Última edición por <b>{last_user}</b> el {formatted}</div>", unsafe_allow_html=True)
    else:
        st.sidebar.markdown("<div class='bottom-left'>Última edición: —</div>", unsafe_allow_html=True)
