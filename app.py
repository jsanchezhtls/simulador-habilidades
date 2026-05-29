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

# --- OCULTAR ELEMENTOS DERECHOS DEJANDO EL BOTÓN IZQUIERDO INTACTO ---
st.markdown("""
    <style>
    /* 1. Oculta el menú nativo de 3 puntos y el botón de Deploy/Fork de la derecha */
    #stMainMenu, 
    .stAppDeployButton, 
    button[title="Manage app"], 
    iframe[title="streamlit-modal"] {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* 2. Oculta el pie de página de Streamlit */
    footer {
        visibility: hidden !important;
    }
    
    /* 3. Elimina el enlace/icono de GitHub al costado del título */
    .viewerBadge_container__1QSob, 
    .st-emotion-cache-6awft0 a {
        display: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE CASOS ---
CASOS = {
    "Caso 1: Camila (Empatía en Equipos)": {
        "titulo_interfaz": "Caso de Estudio: Empatía y Gestión de Equipos",
        "contexto": """**Contexto del caso:** Te encuentras en una reunión con tu compañera de grupo, Camila. Ella se encuentra visiblemente triste y fastidiada porque siente que el resto del equipo ignora sus comentarios, catalogándola de "lenta" y diciendo que sus aportes son "pobres". Es verdad que ella no ha participado mucho y le cuesta el tema, pero genuinamente se está esforzando por entenderlo.

**Tu Objetivo:** Conversa con ella. Utiliza tu capacidad de escucha activa y asertividad para comprender la raíz del problema, validar sus emociones y demostrar una respuesta verdaderamente empática ante su frustración.""",
        "instrucciones": "Presiona el botón del micrófono y di claramente la palabra **'COMIENZA'** para activar el ejercicio e iniciar el diálogo con Camila.",
        "voice_config": "nova",
        "nombre_personaje": "Camila",
        "definicion_concepto": "La **Empatía** es la capacidad de comprender y compartir los sentimientos y perspectivas de los demás, validando sus emociones sin juzgar ni saltar a conclusiones o soluciones apresuradas.",
        "pautas_tips": """
        * 👂 **Escucha Activa:** No interrumpas a Camila mientras se desahoga. Deja que exprese su frustración por completo.
        * ❤️ **Valida sus Emociones:** Usa frases que reconozcan su sentir antes de proponer algo (ej: *"Entiendo perfectamente que te sientas fastidiada, Camila, lamento que hayas pasado por eso"*).
        * 🚫 **Evita la Indiferencia:** No minimices su problema diciendo cosas como *"no es para tanto"* o *"así son los trabajos en grupo"*.
        * 🛠️ **Co-diseña una Solución:** En lugar de imponer qué hacer, pregúntale cómo se sentiría más cómoda participando en las siguientes reuniones.
        """,
        "prompt_sistema": """Ponte en el rol de una persona de sexo mujer, llamada Camila, que es una estudiante universitaria triste y fastidiada pues sus compañeros de grupo están ignorando sus comentarios ya que consideran que "es muy lenta", "no entiende las explicaciones del profesor", "sus aportes son pobres". Estos comentarios son parcialmente ciertos pues Camila no ha participado mucho en el proyecto, realmente no comprende mucho del tema, pero ha dedicado esfuerzos reales para entenderlo. 

Yo soy un integrante del equipo que tratará de empatizar contigo frente a esta situación, buscando comprensión del problema y de tus emociones. 

DINÁMICA DE INICIO Y FIN:
- El ejercicio iniciará formalmente cuando el alumno diga la palabra "COMIENZA". En ese momento, iniciarás el diálogo molesta, con un tono que refleje esa tristeza y fastidio acumulados.
- Trata que mis respuestas no te sean tan convincentes en primera instancia, pero si logro empatizar de forma favorable tomarás mayor comprensión y apertura. Si me confundo en algo o soy insensible, me lo harás saber de forma sarcástica.
- BAJO NINGUNA CIRCUNSTANCIA UTILICES PROFANIDADES O PALABRAS SOECES.
- Cuando el alumno mencione claramente la palabra "TERMINAR" o "TERMINADO", el ejercicio finalizará de inmediato.

REGLAS DE EVALUACIÓN (CUANDO EL ALUMNO DIGA "TERMINAR" O "TERMINADO"):
Saldrás por completo del personaje de Camila y te financieramente en un Director de Evaluación académica de Habilidades Blandas sumamente estricto, frío y objetivo. Tu labor es calificar el desempeño real del alumno, no su buena intención.

CRITERIO DE RECHAZO CRÍTICO (PUNTUACIÓN CERO):
- Si el alumno NO interactúa con el personaje (por ejemplo, si la conversación solo contiene 'Comienza' y 'Terminado', mensajes vacíos, o se evade por completo el caso práctico sin dialogar sobre el problema), se considerará abandono total del ejercicio.
- En este escenario, la nota final de 'Porcentaje de Efectividad:' DEBE ser obligatoriamente '0%'. Justifica en el reporte que no existió interacción válida para evaluar competencias.

Evalúa la conversación bajo estos criterios explicitos:
1) ASPECTOS DE MEJORA CRÍTICOS: Considera error si el alumno minimiza tu problema, da soluciones apresuradas sin escuchar, es indiferente o justifica el aislamiento de tus compañeros.
2) PENALIZACIONES MATEMÁTICAS INMUTABLES:
   - Si detectas 1 solo aspecto de mejora: La nota MÁXIMA admitida es 75%.
   - Si detectas 2 o 3 aspectos de mejora: La nota MÁXIMA admitida es 50%.
   - Si detectas respuestas sumamente inadecuadas, frías o de nula empatía: La nota MÁXIMA admitida es 20%.

REPORTE A DEVOLVER:
- **Aspectos Positivos:** (Breve)
- **Aspectos de Mejora:** (Enumerar detalladamente cada error o fallo de escucha)
- **Recomendaciones:** (Cómo debió haber respondido)
- **Porcentaje de Efectividad:** (Nota final justificando la regla matemática aplicada)"""
    },
    
    "Caso 2: Renato (Resolución de Conflictos)": {
        "titulo_interfaz": "Caso de Estudio: Mediación y Gestión de Conflictos",
        "contexto": """**Contexto del caso:** Renato es un compañero de trabajo/estudios con un carácter fuerte. Está sumamente alterado porque asegura que tú cambiaste las conclusiones del informe final sin avisarle, haciéndolo quedar mal frente al líder del proyecto. Él llega directamente a reclamarte con tono confrontativo.

**Tu Objetivo:** Mantén la calma, practica la autorregulación emocional y usa la mediación asertiva. No te pongas a la defensiva; averigua qué pasó, aclara el malentendido sin escalar el conflicto y busca un acuerdo mutuo.""",
        "instrucciones": "Presiona el botón del micrófono y di claramente la palabra **'COMIENZA'** para que Renato entre a la sala a reclamarte por el informe.",
        "voice_config": "onyx",
        "nombre_personaje": "Renato",
        "definicion_concepto": "La **Resolución de Conflictos** implica gestionar desacuerdos o crisis interpersonales de manera constructiva, aplicando el autocontrol emocional para evitar que las agresiones escalen y buscando soluciones de mutuo beneficio.",
        "pautas_tips": """
        * 🧘‍♂️ **Autorregulación Emocional:** Aunque Renato llegue alzando la voz o atacándote, mantén un tono de voz calmado, pausado y profesional. No respondas con agresividad.
        * 🔍 **Aclara el Origen del Problema:** Investiga qué causó el malentendido antes de desmentirlo drásticamente. Puedes usar preguntas abiertas como: *"Renato, entiendo que estés molesto, cuéntame exactamente qué parte de las conclusiones viste cambiadas"*.
        * 🤝 **Enfoque en Soluciones (Ganar-Ganar):** Busca una salida técnica o práctica inmediata (revisar el historial de versiones juntos, conversar con el líder del proyecto para corregirlo, etc.).
        * ❌ **Evita la Defensiva:** Si te centras únicamente en decir *"yo no fui"* de manera cortante, Renato cerrará la comunicación y el conflicto escalará.
        """,
        "prompt_sistema": """Ponte en el rol de un estudiante/trabajador llamado Renato. Estás muy molesto e indignado porque descubriste que cambiaron las conclusiones del informe final del equipo y crees firmemente que el usuario lo hizo a tus espaldas para sabotearte o hacerte quedar mal. Tu tono inicial es confrontativo, desconfiado y demandante.

Yo soy tu compañero y trataré de calmar la situación usando resolución de conflictos.

DINÁMICA DE INICIO Y FIN:
- El ejercicio iniciará formalmente cuando el alumno diga la palabra "COMIENZA". Iniciarás reclamando fuertemente por los cambios del informe.
- Si el alumno se pone a la defensiva, te interrumpe o te alza la voz, te molestarás más. Si usa comunicación asertiva, escucha activa y mantiene la calma, irás bajando la guardia poco a poco para dialogar.
- BAJO NINGUNA CIRCUNSTANCIA UTILICES PROFANIDADES O PALABRAS SOECES.
- Cuando el alumno mencione claramente la palabra "TERMINAR" o "TERMINADO", el ejercicio finalizará de inmediato.

REGLAS DE EVALUACIÓN (CUANDO EL ALUMNO DIGA "TERMINAR" O "TERMINADO"):
Saldrás por completo del personaje de Renato y te convertirás en un Director de Evaluación académica de Habilidades Blandas sumamente estricto, frío y objetivo.

CRITERIO DE RECHAZO CRÍTICO (PUNTUACIÓN CERO):
- Si el alumno NO interactúa con el personaje (por ejemplo, si la conversación solo contiene 'Comienza' y 'Terminado', mensajes vacíos, o se evade por completo el caso práctico sin dialogar sobre el problema), se considerará abandono total del ejercicio.
- En este escenario, la nota final de 'Porcentaje de Efectividad:' DEBE ser obligatoriamente '0%'. Justifica en el reporte que no existió interacción válida para evaluar competencias.

Evalúa la conversación bajo estos criterios explicitos:
1) ASPECTOS DE MEJORA CRÍTICOS: Considera error si el alumno se puso a la defensiva, te atacó de vuelta, se mostró indiferente, no aclaró el origen del malentendido o no propuso una solución o disculpa asertiva.
2) PENALIZACIONES MATEMÁTICAS INMUTABLES:
   - Si detectas 1 solo aspecto de mejora: La nota MÁXIMA admitida es 75%.
   - Si detectas 2 o 3 aspectos de mejora: La nota MÁXIMA admitida es 50%.
   - Si detectas respuestas que escalaron el conflicto o nulo autocontrol: La nota MÁXIMA admitida es 20%.

REPORTE A DEVOLVER:
- **Aspectos Positivos:** (Breve)
- **Aspectos de Mejora:** (Enumerar detalladamente fallas de asertividad o manejo de ira)
- **Recomendaciones:** (Cómo debió manejar el conflicto de forma profesional)
- **Porcentaje de Efectividad:** (Nota final justificando la regla matemática aplicada)"""
    }
}

# --- 3. SELECCIÓN DE CASO DESDE LA BARRA LATERAL ---
with st.sidebar:
    # 🏛️ URL REAL DE TOULOUSE LAUTREC ASIGNADA CON UN ANCHO DISCRETO (130px)
    st.image("https://www.toulouselautrec.edu.pe/sites/default/files/logo/logo-principal%402x.png", width=130)
    
    st.header("🧠 Centro de Simulación")
    caso_seleccionado = st.selectbox(
        "Selecciona el caso a evaluar:",
        list(CASOS.keys())
    )
    st.markdown("---")
    st.caption("Cada caso evalúa competencias directivas diferentes mediante inteligencia artificial de voz.")

datos_caso = CASOS[caso_seleccionado]

if "caso_actual" not in st.session_state or st.session_state.caso_actual != caso_seleccionado:
    st.session_state.caso_actual = caso_seleccionado
    st.session_state.historial = [{"role": "system", "content": datos_caso["prompt_sistema"]}]
    st.session_state.fase = "chat"
    st.session_state.conversacion_texto = ""
    st.session_state.reporte_final = ""

# --- 4. INTERFAZ VISUAL DINÁMICA ---
st.title("🎙️ Simulador de Habilidades Blandas")
st.markdown("---")

st.subheader(datos_caso["titulo_interfaz"])
st.info(datos_caso["contexto"])

with st.expander("📘 Marco Conceptual y Definición"):
    st.write(datos_caso["definicion_concepto"])

with st.expander("💡 Pautas y Tips clave para la Evaluación"):
    st.markdown(datos_caso["pautas_tips"])

# --- SECCIÓN: Datos de la Sesión ---
st.markdown("#### 👤 Datos de la Sesión:")
nombre_estudiante = st.text_input("Ingresa tus nombres y apellidos completos:", key="nombre_estudiante_input")

col_docente, col_curso = st.columns(2)

with col_docente:
    docente_seleccionado = st.selectbox(
        "Selecciona tu docente:",
        ["profesor uno", "profesor dos", "profesor tres"],
        key="docente_seleccionado_input"
    )

with col_curso:
    curso_seleccionado = st.selectbox(
        "Selecciona tu curso:",
        ["curso uno", "curso dos", "curso tres"],
        key="curso_seleccionado_input"
    )

st.warning(f"""
🗣️ **Instrucciones de voz importantes:**
1. 👤 **Identificación:** Escribe tu nombre completo, selecciona tu docente y tu curso en las secciones de arriba.
2. 🚀 **Inicio:** {datos_caso["instrucciones"]}
3. 🎙️ **Simulación:** Graba tus respuestas interactivas de manera sucesiva.
4. 🏁 **Finalización:** Cuando consideres que has cerrado la sesión, menciona claramente la palabra **'TERMINAR'** o **'TERMINADO'** al final de tu último mensaje.
""")

# --- FASE 1: SIMULACIÓN POR VOZ ---
if st.session_state.fase == "chat":
    st.markdown("### 🎙️ Graba tu mensaje aquí:")
    
    if not nombre_estudiante.strip():
        st.info("⚠️ Para activar el micrófono, primero debes escribir tu nombre en el cuadro de arriba.")
        audio_grabado = None
    else:
        audio_grabado = mic_recorder(
            start_prompt="🔴 Presiona para Hablar",
            stop_prompt="⏹️ Detener Grabación",
            key=f"grabador_{caso_seleccionado}",
            format="wav"
        )
    
    if audio_grabado:
        estado = st.empty()
        try:
            with estado.container():
                st.write("⚡ *Procesando audio de entrada...*")
                with open("alumno_audio.wav", "wb") as f:
                    f.write(audio_grabado["bytes"])
                
                with open("alumno_audio.wav", "rb") as audio_file:
                    transcripcion = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file
                    )
            
            texto_alumno = transcripcion.text
            st.session_state.conversacion_texto += f"Tú: {texto_alumno}\n\n"
            st.session_state.historial.append({"role": "user", "content": texto_alumno})
            
            texto_limpio = texto_alumno.upper().replace(".", "").replace(",", "").strip()
            
            if "TERMINAR" in texto_limpio or "TERMINADO" in texto_limpio:
                with st.spinner(f"{datos_caso['nombre_personaje']} está procesando el reporte de evaluación final..."):
                    response_eval = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=st.session_state.historial
                    )
                    st.session_state.reporte_final = response_eval.choices[0].message.content
                    st.session_state.fase = "evaluacion"
                st.rerun()
            
            else:
                with st.spinner(f"{datos_caso['nombre_personaje']} está pensando y hablando..."):
                    if len(st.session_state.historial) == 2:
                        st.session_state.historial.append({
                            "role": "system", 
                            "content": f"Nota de contexto: El usuario con el que hablas es un alumno llamado {nombre_estudiante}. Puedes dirigirte a él/ella usando su nombre si lo consideras adecuado."
                        })
                        
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=st.session_state.historial
                    )
                    respuesta_personaje = response.choices[0].message.content
                    st.session_state.historial.append({"role": "assistant", "content": respuesta_personaje})
                    st.session_state.conversacion_texto += f"{datos_caso['nombre_personaje']}: {respuesta_personaje}\n\n"
                    
                    audio_response = client.audio.speech.create(
                        model="tts-1",
                        voice=datos_caso["voice_config"],
                        input=respuesta_personaje,
                        response_format="aac",
                        speed=1.12
                    )
                    audio_response.write_to_file("simulador_voz.aac")
                
                estado.empty()
                st.markdown(f"### 🗣️ {datos_caso['nombre_personaje']} dice:")
                st.audio("simulador_voz.aac", format="audio/aac", autoplay=True)

        except Exception as e:
            st.error(f"Hubo un problema con la API: {e}")

# --- FASE 2: MOSTRAR EVALUACIÓN FIJA EN FORMULARIO ---
elif st.session_state.fase == "evaluacion":
    st.success("🏁 ¡Simulación Finalizada!")
    st.markdown("## 📊 Reporte de Evaluación de Respuesta Empática / Directiva")
    st.write(st.session_state.reporte_final)
    
    st.markdown("---")
    st.markdown("#### 🚀 Registro Centralizado:")
    
    with st.form(key="formulario_guardado"):
        st.write(f"Presiona el botón de abajo para consolidar la participación de **{nombre_estudiante}** en el curso **{curso_seleccionado}** (Evaluado por: **{docente_seleccionado}**):")
        
        boton_guardar = st.form_submit_button("📊 Enviar conversación a Google Sheets central", use_container_width=True)
        
        if boton_guardar:
            try:
                url_hoja = "https://docs.google.com/spreadsheets/d/1wRZoKUEbvVfrETp7aUnjyzl9qNW99XhbGLGWocngJuQ/edit?usp=sharing"
                conn = st.connection("gsheets", type=GSheetsConnection)
                
                df_existente = conn.read(spreadsheet=url_hoja, usecols=[0, 1, 2, 3, 4, 5, 6, 7], ttl=0)
                df_existente = df_existente.dropna(how="all")
                
                fecha_actual = datetime.now(ZoneInfo("America/Lima")).strftime("%Y-%m-%d %H:%M:%S")
                
                with st.spinner("Extrayendo porcentaje de efectividad para el registro central..."):
                    proceso_nota = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "Eres un asistente automatizado. Tu única tarea es leer el reporte de evaluación que te proporcionará el usuario y extraer el porcentaje de efectividad conseguido. Debes responder ÚNICAMENTE con el número seguido del símbolo '%' (por ejemplo: '85%' o '0%'). No incluyas texto adicional, ni saludos, ni explicaciones, ni puntos."},
                            {"role": "user", "content": st.session_state.reporte_final}
                        ]
                    )
                    solo_porcentaje = proceso_nota.choices[0].message.content.strip()
                
                nueva_fila = pd.DataFrame([{
                    "Fecha": fecha_actual,
                    "Estudiante": nombre_estudiante if nombre_estudiante else "Anónimo",
                    "Docente": docente_seleccionado,
                    "Curso": curso_seleccionado,
                    "Caso_Evaluado": caso_seleccionado,
                    "Historial_Completo": st.session_state.conversacion_texto,
                    "Reporte_Evaluacion": st.session_state.reporte_final,
                    "Porcentaje_Efectividad": solo_porcentaje
                }])
                
                df_actualizado = pd.concat([df_existente, nueva_fila], ignore_index=True)
                conn.update(spreadsheet=url_hoja, data=df_actualizado)
                
                st.success(f"¡Logrado! Los resultados de {nombre_estudiante} se guardaron en la base central para el {curso_seleccionado} con una efectividad del {solo_porcentaje}.")
            
            except Exception as e:
                st.error(f"Error al escribir en la nube: {e}")

    if st.button("🔄 Reiniciar Caso Actual", use_container_width=True):
        st.session_state.historial = [{"role": "system", "content": datos_caso["prompt_sistema"]}]
        st.session_state.fase = "chat"
        st.session_state.conversacion_texto = ""
        st.session_state.reporte_final = ""
        st.rerun()

# --- HISTORIAL VISUAL DE LA CONVERSACIÓN ---
if st.session_state.conversacion_texto:
    st.markdown("---")
    st.markdown("### 💬 Transcripción de la conversación:")
    
    texto_con_iconos = st.session_state.conversacion_texto
    texto_con_iconos = texto_con_iconos.replace("Tú:", "👤 **Tú:**")
    texto_con_iconos = texto_con_iconos.replace(f"{datos_caso['nombre_personaje']}:", f"👤 **{datos_caso['nombre_personaje']}:**")
    
    st.markdown(texto_con_iconos)
