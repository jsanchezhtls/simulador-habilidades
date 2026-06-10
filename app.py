import streamlit as st
from openai import OpenAI
from streamlit_mic_recorder import mic_recorder
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import os

# --- 1. CONFIGURACIÓN DE APIS Y MODELOS ---
API_KEY_OPENAI = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=API_KEY_OPENAI)

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

# --- 2. BANCO DE CASOS ---
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

# --- 3. SELECCIÓN DE CASO DESDE LA BARRA LATERAL ---
with st.sidebar:
    # --- CAMBIO AQUÍ: Lectura directa desde el servidor raw de GitHub ---
    url_logo_github = "https://raw.githubusercontent.com/jsanchezhtls/simulador-habilidades/main/logo-original.png"
    
    # --- AJUSTE DE ALINEACIÓN ---
    # Usamos HTML con flexbox alineado a la derecha ('flex-end') para forzar la posición exacta de la imagen
    st.markdown(f"""
        <div style="display: flex; justify-content: flex-end; width: 100%; margin-bottom: 5px;">
            <img src="{url_logo_github}" width="140">
        </div>
        """, unsafe_allow_html=True)
        
    st.header("🧠 Centro de Simulación")
    caso_seleccionado = st.selectbox("Selecciona el caso a evaluar:", list(CASOS.keys()))
    st.markdown("---")
    st.caption("Cada caso evalúa competencias directivas diferentes mediante inteligencia artificial de voz.")

datos_caso = CASOS[caso_seleccionado]

# --- CONTROL DE ESTADO INTERNO ---
if "caso_actual" not in st.session_state or st.session_state.caso_actual != caso_seleccionado:
    st.session_state.caso_actual = caso_seleccionado
    st.session_state.historial = [{"role": "system", "content": datos_caso["prompt_sistema"]}]
    st.session_state.fase = "chat"
    st.session_state.conversacion_texto = ""
    st.session_state.reporte_final = ""
    st.session_state.simulacion_activa = False

# --- 4. INTERFAZ VISUAL ---
st.title("🎙️ Simulador de Habilidades Blandas")
st.markdown("---")
st.subheader(datos_caso["titulo_interfaz"])
st.info(datos_caso["contexto"])

with st.expander("📘 Marco Conceptual y Definición"): st.write(datos_caso["definicion_concepto"])
with st.expander("💡 Pautas y Tips clave para la Evaluación"): st.markdown(datos_caso["pautas_tips"])

st.markdown("#### 👤 Datos de la Sesión:")
nombre_estudiante = st.text_input("Ingresa tus nombres y apellidos completos:", key="nombre_estudiante_input")
col_docente, col_curso = st.columns(2)
with col_docente: docente_seleccionado = st.selectbox("Selecciona tu docente:", ["profesor uno", "profesor dos", "profesor tres"], key="docente_seleccionado_input")
with col_curso: curso_seleccionado = st.selectbox("Selecciona tu curso:", ["curso uno", "curso dos", "curso tres"], key="curso_seleccionado_input")

st.warning(f"🗣️ **Instrucciones del simulador:**\n1. Registra tus datos completos en la sección superior.\n2. 🚀 Presiona el botón **'Iniciar Simulación'** para que el personaje empiece a hablar.\n3. 🎙️ Responde usando el micrófono de forma sucesiva.\n4. 🏁 Cuando desees terminar la sesión, presiona el botón **'Finalizar y Evaluar'**.")

# --- FASE 1: SIMULACIÓN POR VOZ ---
if st.session_state.fase == "chat":
    
    # --- BOTONES DE CONTROL DE FLUJO SUPERIORES ---
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("🚀 Iniciar Simulación", use_container_width=True, disabled=st.session_state.simulacion_activa or not nombre_estudiante.strip()):
            st.session_state.simulacion_activa = True
            with st.spinner(f"Iniciando caso con {datos_caso['nombre_personaje']}..."):
                # Disparamos artificialmente el inicio de la conversación simulando la instrucción
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
                # Filtramos para verificar interacciones del usuario excluyendo el disparo inicial automático
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

    # --- REPRODUCCIÓN AUTOMÁTICA DEL SALUDO INICIAL DEL PERSONAJE ---
    if getattr(st.session_state, 'reproducir_inicial', False):
        st.markdown(f"### 🗣️ {datos_caso['nombre_personaje']} dice:")
        st.audio("simulador_voz.aac", format="audio/aac", autoplay=True)
        st.session_state.reproducir_inicial = False

    # --- CONTROL DINÁMICO DEL MICRÓFONO EN PANTALLA ---
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

# --- FASE 2: MOSTRAR EVALUACIÓN FIJA EN FORMULARIO ---
elif st.session_state.fase == "evaluacion":
    st.success("🏁 ¡Simulación Finalizada!")
    st.markdown("## 📊 Reporte de Evaluación de Respuesta Empática / Directiva")
    st.write(st.session_state.reporte_final)
    
    st.markdown("---")
    st.markdown("#### 🚀 Registro Centralizado:")
    
    with st.form(key="formulario_guardado"):
        st.write(f"Presiona el botón de abajo para consolidar la participación de **{nombre_estudiante}**:")
        boton_guardar = st.form_submit_button("📊 Enviar conversación a Google Sheets central", use_container_width=True)
        
        if boton_guardar:
            try:
                url_hoja = "https://docs.google.com/spreadsheets/d/1wRZoKUEbvVfrETp7aUnjyzl9qNW99XhbGLGWocngJuQ/edit?usp=sharing"
                conn = st.connection("gsheets", type=GSheetsConnection)
                df_existente = conn.read(spreadsheet=url_hoja, usecols=[0, 1, 2, 3, 4, 5, 6, 7], ttl=0).dropna(how="all")
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
                conn.update(spreadsheet=url_hoja, data=df_actualizado)
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

# --- HISTORIAL VISUAL DE LA CONVERSACIÓN ---
if st.session_state.conversacion_texto:
    st.markdown("---")
    st.markdown("### 💬 Transcripción de la conversación:")
    texto_con_iconos = st.session_state.conversacion_texto.replace("Tú:", "👤 **Tú:**").replace(f"{datos_caso['nombre_personaje']}:", f"👤 **{datos_caso['nombre_personaje']}:**")
    st.markdown(texto_con_iconos)
