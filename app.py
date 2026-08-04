import streamlit as st
from openai import OpenAI
from streamlit_mic_recorder import mic_recorder
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import os

# --- 1. CONFIGURACIÓN DE APIS Y PÁGINA ---
API_KEY_OPENAI = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=API_KEY_OPENAI)
URL_HOJA = "https://docs.google.com/spreadsheets/d/1wRZoKUEbvVfrETp7aUnjyzl9qNW99XhbGLGWocngJuQ/edit?usp=sharing"

st.set_page_config(page_title="Simulador de Habilidades Blandas", page_icon="🎙️", layout="centered")

# --- OCULTAR ELEMENTOS DERECHOS ---
st.markdown("""
    <style>
    #stMainMenu, .stAppDeployButton, button[title="Manage app"], iframe[title="streamlit-modal"] {
        display: none !important;
        visibility: hidden !important;
    }
    footer { visibility: hidden !important; }
    .viewerBadge_container__1QSob, .st-emotion-cache-6awft0 a { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

# --- CONTROL DE SESIÓN ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "usuario_actual" not in st.session_state:
    st.session_state.usuario_actual = None

# --- FUNCIÓN DE AUTENTICACIÓN ---
def verificar_credenciales(correo, password):
    correo_clean = correo.strip().lower()
    pass_clean = str(password).strip()
    
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_usuarios = conn.read(spreadsheet=URL_HOJA, worksheet="Usuarios", ttl=0).dropna(how="all")
        df_usuarios.columns = [str(col).strip() for col in df_usuarios.columns]

        if "Correo" in df_usuarios.columns and "Contraseña" in df_usuarios.columns:
            df_usuarios["Correo"] = df_usuarios["Correo"].astype(str).str.strip().str.lower()
            df_usuarios["Contraseña"] = df_usuarios["Contraseña"].astype(str).str.strip().str.replace(".0", "", regex=False)
            
            match = df_usuarios[(df_usuarios["Correo"] == correo_clean) & (df_usuarios["Contraseña"] == pass_clean)]
            if not match.empty:
                return match.iloc[0].to_dict()
        else:
            st.error("⚠️ No se encontraron las columnas 'Correo' o 'Contraseña' en la pestaña Usuarios.")
            
    except Exception as e:
        st.error(f"Error al conectar con la base de datos de usuarios: {e}")
        
    return None

# --- FUNCIÓN PARA OBTENER DOCENTES DINÁMICAMENTE ---
def obtener_lista_docentes():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_usuarios = conn.read(spreadsheet=URL_HOJA, worksheet="Usuarios", ttl=60).dropna(how="all")
        df_usuarios.columns = [str(col).strip() for col in df_usuarios.columns]
        
        if "Rol" in df_usuarios.columns and "Nombre_Completo" in df_usuarios.columns:
            # Filtrar por rol 'docente' (sin importar mayúsculas/minúsculas)
            mask_docentes = df_usuarios["Rol"].astype(str).str.strip().str.lower() == "docente"
            lista_docentes = df_usuarios[mask_docentes]["Nombre_Completo"].dropna().unique().tolist()
            
            if lista_docentes:
                return sorted(lista_docentes)
    except Exception as e:
        st.warning(f"No se pudo cargar la lista de docentes en tiempo real: {e}")
        
    return ["Sin docentes registrados"]

# ==========================================
# PANTALLA DE LOGIN
# ==========================================
if not st.session_state.autenticado:
    st.title("🔐 Acceso al Simulador")
    st.caption("Ingresa con tus credenciales institucionales de Toulouse Lautrec.")
    
    with st.form(key="form_login"):
        correo_input = st.text_input("Correo institucional:")
        pass_input = st.text_input("Contraseña:", type="password")
        btn_login = st.form_submit_button("Ingresar", use_container_width=True)
        
        if btn_login:
            if not correo_input or not pass_input:
                st.warning("Por favor completa ambos campos.")
            else:
                with st.spinner("Validando credenciales..."):
                    datos = verificar_credenciales(correo_input, pass_input)
                    if datos:
                        st.session_state.autenticado = True
                        st.session_state.usuario_actual = datos
                        st.rerun()
                    else:
                        st.error("Correo o contraseña incorrectos. Verifica tus datos.")

# ==========================================
# APLICACIÓN PRINCIPAL (USUARIO AUTENTICADO)
# ==========================================
else:
    # --- BARRA LATERAL ---
    with st.sidebar:
        url_logo_github = "https://raw.githubusercontent.com/jsanchezhtls/simulador-habilidades/main/logo-original.png"
        st.markdown(f"""
            <div style="display: flex; justify-content: flex-end; width: 100%; margin-bottom: 5px;">
                <img src="{url_logo_github}" width="140">
            </div>
            """, unsafe_allow_html=True)
        
        st.write(f"👤 **{st.session_state.usuario_actual['Nombre_Completo']}**")
        st.caption(f"Rol: **{str(st.session_state.usuario_actual['Rol']).capitalize()}**")
        
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.autenticado = False
            st.session_state.usuario_actual = None
            st.rerun()
            
        st.markdown("---")

    # --- PESTAÑAS PRINCIPALES ---
    tab_simulador, tab_progreso = st.tabs(["🎙️ ¡Simular Ahora!", "📊 Mi Progreso"])

    # ==========================================
    # PESTAÑA 1: SIMULADOR DE VOZ
    # ==========================================
    with tab_simulador:
        CASOS = {
            "Caso 1: Camila (Empatía en Equipos)": {
                "titulo_interfaz": "Caso de Estudio: Empatía y Gestión de Equipos",
                "contexto": """**Contexto del caso:** Te encuentras en una reunión con tu compañera de grupo, Camila. Ella se encuentra visiblemente triste y fastidiada porque siente que el resto del equipo ignora sus comentarios, catalogándola de "lenta" y diciendo que sus aportes son "pobres". Es verdad que ella no ha participado mucho y le cuesta el tema, pero genuinamente se está esforzando por entenderlo.""",
                "voice_config": "nova",
                "nombre_personaje": "Camila",
                "definicion_concepto": "La **Empatía** es la capacidad de comprender y compartir los sentimientos y perspectivas de los demás, validando sus emociones sin juzgar ni saltar a conclusiones o soluciones apresuradas.",
                "pautas_tips": """
                * 👂 **Escucha Activa:** No interrumpas a Camila mientras se desahoga. Deja que exprese su frustración por completo.
                * ❤️ **Valida sus Emociones:** Usa frases que reconozcan su sentir antes de proponer algo.
                * 🚫 **Evita la Indiferencia:** No minimices su problema diciendo cosas como *"no es para tanto"*.
                * 🛠️ **Co-diseña una Solución:** Pregúntale cómo se sentiría más cómoda participando.
                """,
                "prompt_sistema": """Ponte en el rol de una persona de sexo mujer, llamada Camila, que es una estudiante universitaria triste y fastidiada pues sus compañeros de grupo están ignorando sus comentarios ya que consideran que "es muy lenta", "no entiende las explicaciones del profesor", "sus aportes son pobres". Camila no ha participado mucho, realmente no comprende mucho del tema, pero ha dedicado esfuerzos reales para entenderlo.

Yo soy un integrante del equipo que tratará de empatizar contigo.

DINÁMICA DE DIÁLOGO:
- Iniciarás el diálogo molesta, con un tono que refleje esa tristeza y fastidio acumulados.
- Trata que mis respuestas no te sean tan convincentes en primera instancia. Si me confundo o soy insensible, me lo harás saber de forma sarcástica.
- BAJO NINGUNA CIRCUNSTANCIA UTILICES PROFANIDADES O PALABRAS SOECES.""",
                "prompt_evaluacion": """Te vas a convertir en un auditor académico robótico, implacable, frío y sin emociones. Tu única función es auditar los errores del alumno basándote en el historial de la conversación. No justifiques sus buenas intenciones.

PUNTUACIÓN BASE: Comienzas con 100%.

APLICA ESTE CHECKLIST DE PENALIZACIONES DE FORMA IMPLACABLE:
1. ¿El alumno dio soluciones apresuradas o recetas mágicas sin antes escuchar y profundizar en la frustración de Camila? -> Resta 25%.
2. ¿El alumno minimizó el problema de Camila, usó frases de indiferencia (ej: "no te preocupes", "es normal en grupos", "no es para tanto") o justificó el aislamiento de sus compañeros? -> Resta 30%.
3. ¿El alumno interrumpió el desahogo de Camila o mostró un tono frío, robótico y distante que no validó la tristeza del personaje? -> Resta 20%.

REPORTE A DEVOLVER (ESTRICTO):
- **Aspectos Positivos:** (Sé extremadamente breve, máximo 2 líneas)
- **Aspectos de Mejora:** (Detalla con citas textuales de la conversación cada uno de los puntos del checklist donde el alumno falló)
- **Recomendaciones:** (Cómo debió haber respondido para no cometer esos errores)
- **Porcentaje de Efectividad:** [Muestra ÚNICAMENTE el número final seguido del símbolo '%' sin desgloses matemáticos, sin operaciones y sin texto entre paréntesis. Ejemplo: 45%]"""
            },
            
            "Caso 2: Renato (Resolución de Conflictos)": {
                "titulo_interfaz": "Caso de Estudio: Mediación y Gestión de Conflictos",
                "contexto": """**Contexto del caso:** Renato es un compañero de trabajo/estudios con un carácter fuerte. Está sumamente alterado porque asegura que tú cambiaste las conclusiones del informe final sin avisarle, haciéndolo quedar mal frente al líder del proyecto. Él llega directamente a reclamarte con tono confrontativo.""",
                "voice_config": "onyx",
                "nombre_personaje": "Renato",
                "definicion_concepto": "La **Resolución de Conflictos** implica gestionar desacuerdos o crisis interpersonales de manera constructiva, aplicando el autocontrol emocional para evitar que las agresiones escalen.",
                "pautas_tips": """
                * 🧘‍♂️ **Autorregulación Emocional:** Mantén un tono de voz calmado, pausado y profesional.
                * 🔍 **Aclara el Origen del Problema:** Investiga qué causó el malentendido antes de desmentirlo drásticamente.
                * 🤝 **Enfoque en Soluciones (Ganar-Ganar):** Busca una salida técnica o práctica inmediata.
                """,
                "prompt_sistema": """Ponte en el rol de un estudiante/trabajador llamado Renato. Estás muy molesto e indignado porque descubriste que cambiaron las conclusiones del informe final del equipo. Tu tono inicial es confrontativo, desconfiado y demandante.

Yo soy tu compañero y trataré de calmar la situación usando resolución de conflictos.

DINÁMICA DE DIÁLOGO:
- Iniciarás reclamando fuertemente por los cambios del informe.
- Si el alumno se pone a la defensiva, te interrumpe o te alza la voz, te molestarás más. Si usa comunicación asertiva, irás bajando la guardia poco a poco.
- BAJO NINGUNA CIRCUNSTANCIA UTILICES PROFANIDADES O PALABRAS SOECES.""",
                "prompt_evaluacion": """Te vas a convertir en un auditor académico robótico, implacable, frío y sin emociones. Tu única función es auditar los errores del alumno basándote en el historial de la conversación. No justifiques sus buenas intenciones.

PUNTUACIÓN BASE: Comienzas con 100%.

APLICA ESTE CHECKLIST DE PENALIZACIONES DE FORMA IMPLACABLE:
1. ¿El alumno se puso a la defensiva de inmediato, atacó de vuelta, se centró solo en decir "yo no fui" o alzó el tono de voz escalando el conflicto? -> Resta 30%.
2. ¿El alumno fue incapaz de investigar activamente el origen del problema o no propuso una solución técnica/práctica viable (ganar-ganar)? -> Resta 25%.
3. ¿El alumno mostró nula autorregulación emocional o interrumpió de manera hostil los reclamos de Renato? -> Resta 25%.

REPORTE A DEVOLVER (ESTRICTO):
- **Aspectos Positivos:** (Sé extremadamente breve, máximo 2 líneas)
- **Aspectos de Mejora:** (Detalla con citas textuales de la conversación cada uno de los puntos del checklist donde el alumno falló)
- **Recomendaciones:** (Cómo debió manejar el conflicto de forma profesional)
- **Porcentaje de Efectividad:** [Muestra ÚNICAMENTE el número final seguido del símbolo '%' sin desgloses matemáticos, sin operaciones y sin texto entre paréntesis. Ejemplo: 45%]"""
            }
        }

        st.header("🧠 Centro de Simulación")
        caso_seleccionado = st.selectbox("Selecciona el caso a evaluar:", list(CASOS.keys()))
        datos_caso = CASOS[caso_seleccionado]

        # CONTROL DE ESTADO INTERNO DEL CASO
        if "caso_actual" not in st.session_state or st.session_state.caso_actual != caso_seleccionado:
            st.session_state.caso_actual = caso_seleccionado
            st.session_state.historial = [{"role": "system", "content": datos_caso["prompt_sistema"]}]
            st.session_state.fase = "chat"
            st.session_state.conversacion_texto = ""
            st.session_state.reporte_final = ""
            st.session_state.simulacion_activa = False

        st.markdown("---")
        st.subheader(datos_caso["titulo_interfaz"])
        st.info(datos_caso["contexto"])

        with st.expander("📘 Marco Conceptual y Definición"): st.write(datos_caso["definicion_concepto"])
        with st.expander("💡 Pautas y Tips clave para la Evaluación"): st.markdown(datos_caso["pautas_tips"])

        st.markdown("#### 👤 Datos de la Sesión:")
        
        # Autocompletado según el Rol
        es_estudiante = str(st.session_state.usuario_actual["Rol"]).strip().lower() == "estudiante"
        if es_estudiante:
            nombre_estudiante = st.session_state.usuario_actual["Nombre_Completo"]
            st.text_input("Estudiante asignado:", value=nombre_estudiante, disabled=True)
        else:
            nombre_estudiante = st.text_input("Ingresa el nombre del estudiante a evaluar:", key="input_nombre_docente")

        col_docente, col_curso = st.columns(2)
        
        # --- LECTURA DINÁMICA DE LA LISTA DE DOCENTES DESDE LA HOJA 'USUARIOS' ---
        docentes_disponibles = obtener_lista_docentes()
        
        with col_docente: 
            docente_seleccionado = st.selectbox("Selecciona tu docente:", docentes_disponibles, key="docente_sel")
        with col_curso: 
            curso_seleccionado = st.selectbox("Selecciona tu curso:", ["Habilidades Blandas 1", "Liderazgo y Gestión", "Comunicación Efectiva"], key="curso_sel")

        st.warning("🗣️ **Instrucciones:**\n1. Verifica tus datos arriba.\n2. Presiona **'🚀 Iniciar Simulación'**.\n3. Graba tu voz para interactuar.\n4. Al finalizar, presiona **'🏁 Finalizar y Evaluar'**.")

        # --- FASE CHAT DE VOZ ---
        if st.session_state.fase == "chat":
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.button("🚀 Iniciar Simulación", use_container_width=True, disabled=st.session_state.simulacion_activa or not nombre_estudiante.strip()):
                    st.session_state.simulacion_activa = True
                    with st.spinner(f"Iniciando caso con {datos_caso['nombre_personaje']}..."):
                        st.session_state.historial.append({"role": "user", "content": "COMIENZA EL EJERCICIO"})
                        if len(st.session_state.historial) == 3:
                            st.session_state.historial.insert(1, {"role": "system", "content": f"Nota de contexto: El usuario con el que hablas es un alumno llamado {nombre_estudiante}."})
                        
                        response = client.chat.completions.create(model="gpt-4o-mini", messages=st.session_state.historial)
                        respuesta_personaje = response.choices[0].message.content
                        st.session_state.historial.append({"role": "assistant", "content": respuesta_personaje})
                        st.session_state.conversacion_texto += f"{datos_caso['nombre_personaje']}: {respuesta_personaje}\n\n"
                        
                        audio_response = client.audio.speech.create(
                            model="tts-1", voice=datos_caso["voice_config"], input=respuesta_personaje, response_format="aac", speed=1.12
                        )
                        audio_response.write_to_file("simulador_voz.aac")
                        st.session_state.reproducir_inicial = True
                    st.rerun()

            with col_btn2:
                if st.button("🏁 Finalizar y Evaluar", use_container_width=True, disabled=not st.session_state.simulacion_activa):
                    with st.spinner("Procesando reporte de evaluación final..."):
                        intervenciones_usuario = [m for m in st.session_state.historial if m["role"] == "user" and m["content"] != "COMIENZA EL EJERCICIO"]
                        palabras_totales = " ".join([m["content"] for m in intervenciones_usuario])
                        
                        if len(palabras_totales.strip()) < 5:
                            st.session_state.reporte_final = """- **Aspectos Positivos:** Ninguno. No existió interacción real con el personaje.
- **Aspectos de Mejora:** Abandono o evasión del ejercicio práctico.
- **Recomendaciones:** Debió entablar un diálogo activo con el personaje para poner a prueba sus habilidades antes de finalizar la sesión.
- **Porcentaje de Efectividad:** 0%"""
                        else:
                            mensajes_evaluacion = [
                                {"role": "system", "content": datos_caso["prompt_evaluacion"]},
                                {"role": "user", "content": f"Aquí está el historial completo de la simulación para que lo evalúes:\n\n{st.session_state.conversacion_texto}"}
                            ]
                            response_eval = client.chat.completions.create(model="gpt-4o-mini", messages=mensajes_evaluacion)
                            st.session_state.reporte_final = response_eval.choices[0].message.content
                        
                        st.session_state.fase = "evaluacion"
                    st.rerun()

            st.markdown("---")

            if getattr(st.session_state, 'reproducir_inicial', False):
                st.markdown(f"### 🗣️ {datos_caso['nombre_personaje']} dice:")
                st.audio("simulador_voz.aac", format="audio/aac", autoplay=True)
                st.session_state.reproducir_inicial = False

            if st.session_state.simulacion_activa:
                st.markdown("### 🎙️ Graba tu respuesta aquí:")
                audio_grabado = mic_recorder(start_prompt="🔴 Presiona para Hablar", stop_prompt="⏹️ Detener Grabación", key=f"grabador_{caso_seleccionado}", format="wav")
                
                if audio_grabado:
                    estado = st.empty()
                    try:
                        with estado.container():
                            st.write("⚡ *Procesando audio...*")
                            with open("alumno_audio.wav", "wb") as f: f.write(audio_grabado["bytes"])
                            with open("alumno_audio.wav", "rb") as audio_file:
                                transcripcion = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
                        
                        texto_alumno = transcripcion.text
                        st.session_state.conversacion_texto += f"Tú: {texto_alumno}\n\n"
                        st.session_state.historial.append({"role": "user", "content": texto_alumno})
                        
                        with st.spinner(f"{datos_caso['nombre_personaje']} está pensando..."):
                            response = client.chat.completions.create(model="gpt-4o-mini", messages=st.session_state.historial)
                            respuesta_personaje = response.choices[0].message.content
                            st.session_state.historial.append({"role": "assistant", "content": respuesta_personaje})
                            st.session_state.conversacion_texto += f"{datos_caso['nombre_personaje']}: {respuesta_personaje}\n\n"
                            
                            audio_response = client.audio.speech.create(
                                model="tts-1", voice=datos_caso["voice_config"], input=respuesta_personaje, response_format="aac", speed=1.12
                            )
                            audio_response.write_to_file("simulador_voz.aac")
                        
                        estado.empty()
                        st.markdown(f"### 🗣️ {datos_caso['nombre_personaje']} dice:")
                        st.audio("simulador_voz.aac", format="audio/aac", autoplay=True)
                    except Exception as e:
                        st.error(f"Hubo un problema con la API: {e}")
            else:
                if nombre_estudiante.strip():
                    st.info("💡 Todo listo. Presiona el botón '🚀 Iniciar Simulación' arriba para comenzar el ejercicio.")
                else:
                    st.info("⚠️ Ingresa tu nombre en el cuadro superior para desbloquear los controles de la simulación.")

        # --- FASE EVALUACIÓN Y GUARDADO ---
        elif st.session_state.fase == "evaluacion":
            st.success("🏁 ¡Simulación Finalizada!")
            st.markdown("## 📊 Reporte de Evaluación")
            st.write(st.session_state.reporte_final)
            
            st.markdown("---")
            st.markdown("#### 🚀 Registro Centralizado:")
            
            with st.form(key="formulario_guardado"):
                st.write(f"Presiona el botón de abajo para consolidar la participación de **{nombre_estudiante}**:")
                boton_guardar = st.form_submit_button("📊 Enviar conversación a Google Sheets central", use_container_width=True)
                
                if boton_guardar:
                    try:
                        conn = st.connection("gsheets", type=GSheetsConnection)
                        df_existente = conn.read(spreadsheet=URL_HOJA, worksheet="Hoja 1", usecols=[0, 1, 2, 3, 4, 5, 6, 7], ttl=0).dropna(how="all")
                        fecha_actual = datetime.now(ZoneInfo("America/Lima")).strftime("%Y-%m-%d %H:%M:%S")
                        
                        with st.spinner("Extrayendo porcentaje de efectividad..."):
                            proceso_nota = client.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=[
                                    {"role": "system", "content": "Extrae exclusivamente el porcentaje numérico de efectividad final. Tu respuesta debe consistir ÚNICAMENTE en el número seguido del símbolo '%' (ejemplo: '45%' o '0%'). No incluyas texto adicional ni paréntesis."},
                                    {"role": "user", "content": st.session_state.reporte_final}
                                ]
                            )
                            solo_porcentaje = proceso_nota.choices[0].message.content.strip()
                        
                        nueva_fila = pd.DataFrame([{
                            "Fecha": fecha_actual, "Estudiante": nombre_estudiante if nombre_estudiante else "Anónimo",
                            "Docente": docente_seleccionado, "Curso": curso_seleccionado, "Caso_Evaluado": caso_seleccionado,
                            "Historial_Completo": st.session_state.conversacion_texto, "Reporte_Evaluacion": st.session_state.reporte_final,
                            "Porcentaje_Efectividad": solo_porcentaje
                        }])
                        
                        df_actualizado = pd.concat([df_existente, nueva_fila], ignore_index=True)
                        conn.update(spreadsheet=URL_HOJA, worksheet="Hoja 1", data=df_actualizado)
                        st.success(f"¡Logrado! Guardado con una efectividad del {solo_porcentaje}.")
                    except Exception as e:
                        st.error(f"Error al escribir en la nube: {e}")

            if st.button("🔄 Reiniciar Caso Actual", use_container_width=True):
                st.session_state.historial = [{"role": "system", "content": datos_caso["prompt_sistema"]}]
                st.session_state.fase = "chat"
                st.session_state.conversacion_texto = ""
                st.session_state.reporte_final = ""
                st.session_state.simulacion_activa = False
                st.rerun()

        if st.session_state.conversacion_texto:
            st.markdown("---")
            st.markdown("### 💬 Transcripción de la conversación:")
            texto_con_iconos = st.session_state.conversacion_texto.replace("Tú:", "👤 **Tú:**").replace(f"{datos_caso['nombre_personaje']}:", f"👤 **{datos_caso['nombre_personaje']}:**")
            st.markdown(texto_con_iconos)

    # ==========================================
    # PESTAÑA 2: MI PROGRESO / PANEL DOCENTE
    # ==========================================
    with tab_progreso:
        st.header("📊 Panel de Progreso y Evaluación Longitudinal")
        
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df_historico = conn.read(spreadsheet=URL_HOJA, worksheet="Hoja 1", ttl=0).dropna(how="all")
            
            df_historico["Efectividad_Num"] = df_historico["Porcentaje_Efectividad"].astype(str).str.replace("%", "").str.strip()
            df_historico["Efectividad_Num"] = pd.to_numeric(df_historico["Efectividad_Num"], errors="coerce").fillna(0)
            df_historico["Fecha"] = pd.to_datetime(df_historico["Fecha"], errors="coerce")
            
            rol_actual = str(st.session_state.usuario_actual["Rol"]).strip().lower()

            if rol_actual == "estudiante":
                mi_nombre = st.session_state.usuario_actual["Nombre_Completo"]
                df_mi_progreso = df_historico[df_historico["Estudiante"].astype(str).str.strip().str.lower() == mi_nombre.strip().lower()].sort_values("Fecha")
                
                if df_mi_progreso.empty:
                    st.info("Aún no registras simulaciones guardadas. Completa tu primer caso para ver tu evolución aquí.")
                else:
                    promedio = df_mi_progreso["Efectividad_Num"].mean()
                    total_casos = len(df_mi_progreso)
                    
                    c1, c2 = st.columns(2)
                    c1.metric("Promedio General de Efectividad", f"{promedio:.1f}%")
                    c2.metric("Simulaciones Realizadas", total_casos)
                    
                    st.subheader("📈 Mi Curva de Aprendizaje")
                    st.line_chart(df_mi_progreso.set_index("Fecha")["Efectividad_Num"])
                    
                    st.subheader("📋 Historial de Feedback")
                    for _, row in df_mi_progreso.iterrows():
                        fecha_str = row["Fecha"].strftime("%Y-%m-%d %H:%M") if pd.notnull(row["Fecha"]) else "Sin fecha"
                        with st.expander(f"Caso: {row['Caso_Evaluado']} | Nota: {row['Porcentaje_Efectividad']} ({fecha_str})"):
                            st.markdown(f"**Docente:** {row['Docente']}")
                            st.markdown(f"**Reporte:**\n{row['Reporte_Evaluacion']}")

            else:
                mi_nombre_docente = st.session_state.usuario_actual["Nombre_Completo"]
                df_docente = df_historico[df_historico["Docente"].astype(str).str.strip().str.lower() == mi_nombre_docente.strip().lower()]
                
                if df_docente.empty:
                    st.info(f"Aún no hay estudiantes que hayan registrado prácticas seleccionando a **{mi_nombre_docente}** como su docente.")
                else:
                    estudiantes_lista = list(df_docente["Estudiante"].unique())
                    st.subheader(f"👨‍🏫 Panel del Docente: {mi_nombre_docente}")
                    st.caption(f"Visualizando resultados de tus {len(estudiantes_lista)} estudiantes asignados.")
                    
                    estudiante_sel = st.selectbox("Selecciona un estudiante para revisar su perfil:", estudiantes_lista)
                    df_estudiante_sel = df_docente[df_docente["Estudiante"] == estudiante_sel].sort_values("Fecha")
                    
                    c1, c2 = st.columns(2)
                    c1.metric("Promedio del Estudiante", f"{df_estudiante_sel['Efectividad_Num'].mean():.1f}%")
                    c2.metric("Intentos Totales", len(df_estudiante_sel))
                    
                    st.subheader(f"📈 Evolución de {estudiante_sel}")
                    st.line_chart(df_estudiante_sel.set_index("Fecha")["Efectividad_Num"])
                    
                    st.subheader("📋 Detalle de Interacciones")
                    st.dataframe(df_estudiante_sel[["Fecha", "Caso_Evaluado", "Curso", "Porcentaje_Efectividad"]], use_container_width=True)

        except Exception as e:
            st.error(f"No se pudieron cargar los datos de progreso desde la nube: {e}")
