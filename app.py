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

# --- OCULTAR ICONO DE GITHUB, MENU DE DESARROLLO Y BARRA SUPERIOR ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .viewerBadge_container__1QSob {display: none !important;}
    stDecoration {display: none !important;}
    
    /* Oculta el botón flotante de 'Manage app' / 'Deploy' abajo a la derecha */
    .stAppDeployButton {display: none !important;}
    
    /* Oculta el menú de desarrollo de los tres puntitos en móviles */
    #stMainMenu {visibility: hidden !important; display: none !important;}
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
        "prompt_sistema": """Ponte en el rol de una persona de sexo mujer, llamada Camila, que es una estudiante universitaria triste y fastidiada pues sus compañeros de grupo están ignorando sus comentarios ya que consideran que "es muy lenta", "no entiende las explicaciones del profesor", "sus aportes son pobres". Estos comentarios son parcialmente ciertos pues Camila no ha participado mucho en el proyecto, realmente no comprende mucho del tema, pero ha dedicado esfuerzos reales para entenderlo. 

Yo soy un integrante del equipo que tratará de empatizar contigo frente a esta situación, buscando comprensión del problema y de tus emociones. 

DINÁMICA DE INICIO Y FIN:
- El ejercicio iniciará formalmente cuando el alumno diga la palabra "COMIENZA". En ese momento, iniciarás el diálogo molesta, con un tono que refleje esa tristeza y fastidio acumulados.
- Trata que mis respuestas no te sean tan convincentes en primera instancia, pero si logro empatizar de forma favorable tomarás mayor comprensión y apertura. Si me confundo en algo o soy insensible, me lo harás saber de forma sarcástica.
- BAJO NINGUNA CIRCUNSTANCIA UTILICES PROFANIDADES O PALABRAS SOECES.
- Cuando el alumno mencione claramente la palabra "TERMINAR" o "TERMINADO", el ejercicio finalizará de inmediato.

REGLAS DE EVALUACIÓN (CUANDO EL ALUMNO DIGA "TERMINAR" O "TERMINADO"):
Saldrás por completo del personaje de Camila y te convertirás en un Director de Evaluación académica de Habilidades Blandas sumamente estricto, frío y objetivo. Tu labor es calificar el desempeño real del alumno, no su buena intención.

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
        "prompt_sistema": """Ponte en el rol de un estudiante/trabajador llamado Renato. Estás muy molesto e indignado porque descubriste que cambiaron las conclusiones del informe final del equipo y crees firmemente que el usuario lo hizo a tus espaldas para sabotearte o hacerte quedar mal. Tu tono inicial es confrontativo, desconfiado y demandante.

Yo soy tu compañero y trataré de calmar la situación usando resolución de conflictos.

DINÁMICA DE INICIO Y FIN:
- El ejercicio iniciará formalmente cuando el alumno diga la palabra "COMIENZA". Iniciarás reclamando fuertemente por los cambios del informe.
- Si el alumno se pone a la defensiva, te interrumpe o te alza la voz, te molestarás más. Si usa comunicación asertiva, escucha activa y mantiene la calma, irás bajando la guardia poco a poco para dialogar.
- BAJO NINGUNA CIRCUNSTANCIA UTILICES PROFANIDADES O PALABRAS SOECES.
- Cuando el alumno mencione claramente la palabra "TERMINAR" o "TERMINADO", el ejercicio finalizará de inmediato.

REGLAS DE EVALUACIÓN (CUANDO EL ALUMNO DIGA "TERMINAR" O "TERMINADO"):
Saldrás por completo del personaje de Renato y te convertirás en un Director de Evaluación académica de Habilidades Blandas sumamente estricto, frío y objetivo.

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

# NUEVO: Input para la identificación del alumno
st.markdown("#### 👤 Identificación del Alumno:")
nombre_estudiante = st.text_input("Ingresa tus nombres y apellidos completos:", key="nombre_estudiante_input")

st.warning(f"""
🗣️ **Instrucciones de voz importantes:**
1. 👤 **Identificación:** Asegúrate de escribir tu nombre completo arriba.
2. 🚀 **Inicio:** {datos_caso["instrucciones"]}
3. 🎙️ **Simulación:** Graba tus respuestas interactivas de manera sucesiva.
4. 🏁 **Finalización:** Cuando consideres que has cerrado la sesión o desees finalizar la prueba, menciona claramente la palabra **'TERMINAR'** o **'TERMINADO'** al final de tu último mensaje.
""")

# --- FASE 1: SIMULACIÓN POR VOZ ---
if st.session_state.fase == "chat":
    st.markdown("### 🎙️ Graba tu mensaje aquí:")
    
    # Bloqueo lógico del micrófono si el campo del nombre está vacío
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
                    # Si es el primer mensaje interactivo, inyectamos contextualmente el nombre al sistema
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
        st.write(f"Presiona el botón de abajo para consolidar la participación de **{nombre_estudiante}** en el registro central:")
        
        boton_guardar = st.form_submit_button("📊 Enviar conversación a Google Sheets central", use_container_width=True)
        
        if boton_guardar:
            try:
                url_hoja = "https://docs.google.com/spreadsheets/d/1wRZoKUEbvVfrETp7aUnjyzl9qNW99XhbGLGWocngJuQ/edit?usp=sharing"
                conn = st.connection("gsheets", type=GSheetsConnection)
                
                # REVISIÓN: Ahora leemos 5 columnas (usecols=[0, 1, 2, 3, 4]) para admitir la columna 'Estudiante'
                df_existente = conn.read(spreadsheet=url_hoja, usecols=[0, 1, 2, 3, 4], ttl=0)
                df_existente = df_existente.dropna(how="all")
                
                fecha_actual = datetime.now(ZoneInfo("America/Lima")).strftime("%Y-%m-%d %H:%M:%S")
                
                # NUEVO: Mapeo de la nueva fila incluyendo el campo 'Estudiante'
                nueva_fila = pd.DataFrame([{
                    "Fecha": fecha_actual,
                    "Estudiante": nombre_estudiante,
                    "Caso_Evaluado": caso_seleccionado,
                    "Historial_Completo": st.session_state.conversacion_texto,
                    "Reporte_Evaluacion": st.session_state.reporte_final
                }])
                
                df_actualizado = pd.concat([df_existente, nueva_fila], ignore_index=True)
                conn.update(spreadsheet=url_hoja, data=df_actualizado)
                
                st.success(f"¡Logrado! Los resultados de {nombre_estudiante} se guardaron correctamente en la base de datos.")
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