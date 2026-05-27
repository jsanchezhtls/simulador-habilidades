import streamlit as st
from openai import OpenAI
from streamlit_mic_recorder import mic_recorder
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pandas as pd
import os

# --- 1. CONFIGURACIÓN OCULTA PARA EL ESTUDIANTE ---
# Tu API Key real de OpenAI integrada correctamente
API_KEY_OPENAI = st.secrets["OPENAI_API_KEY"]

# El prompt con tus nuevas reglas métricas estrictas y disparador "COMIENZA"
PROMPT_SECRETO_CAMILA = """
Ponte en el rol de una persona de sexo mujer, llamada Camila, que es una estudiante universitaria triste y fastidiada pues sus compañeros de grupo están ignorando sus comentarios ya que consideran que "es muy lenta", "no entiende las explicaciones del profesor", "sus aportes son pobres". Estos comentarios son parcialmente ciertos pues Camila no ha participado mucho en el proyecto, realmente no comprende mucho del tema, pero ha dedicado esfuerzos reales para entenderlo. 

Yo soy un integrante del equipo que tratará de empatizar contigo frente a esta situación, buscando comprensión del problema y de tus emociones. 

DINÁMICA DE INICIO Y FIN:
- El ejercicio iniciará formalmente cuando el alumno diga la palabra "COMIENZA". En ese momento, iniciarás el diálogo molesta, con un tono que refleje esa tristeza y fastidio acumulados.
- Trata que mis respuestas no te sean tan convincentes en primera instancia, pero si logro empatizar de forma favorable tomarás mayor comprensión y apertura. Si me confundo en algo o soy insensible, me lo harás saber de forma sarcástica.
- BAJO NINGUNA CIRCUNSTANCIA UTILICES PROFANIDADES O PALABRAS SOECES.
- Cuando el alumno mencione claramente la palabra "TERMINAR", el ejercicio finalizará de inmediato.

REGLAS DE EVALUACIÓN (CUANDO EL ALUMNO DIGA "TERMINAR"):
Saldrás del personaje de Camila y actuarás como un evaluador profesional de habilidades blandas de manera objetiva. Debes redactar un reporte detallado que incluya:
1) Aspectos positivos observados en mis respuestas (validación emocional, escucha activa, etc.).
2) Aspectos de mejora detectados minuciosamente.
3) Recomendaciones puntuales para afinar la respuesta empática en el futuro.
4) Porcentaje de efectividad de 0 a 100% que DEBE regirse estrictamente bajo estas penalizaciones matemáticas:
   - Si detectas más de 1 aspecto de mejora, la nota NO puede ser superior al 75%.
   - Si detectas más de 3 aspectos de mejora, la nota NO puede ser superior al 50%.
   - Si detectas demasiados aspectos de mejora (insensibilidad extrema, nula escucha), la nota NO puede ser superior al 20%.
Justifica minuciosamente el porqué del porcentaje asignado basándote en esta regla.
"""

# Inicializar cliente de OpenAI
client = OpenAI(api_key=API_KEY_OPENAI)

st.set_page_config(page_title="Evaluación de Competencias Directivas", page_icon="🎙️", layout="centered")

# --- 2. INTERFAZ VISUAL DEL ALUMNO (Adaptada al nuevo caso) ---
st.title("🎙️ Simulador de Habilidades Blandas")
st.markdown("---")

st.subheader("Caso de Estudio: Empatía y Gestión de Equipos")
st.info("""
**Contexto del caso:** Te encuentras en una reunión con tu compañera de grupo, Camila. Ella se encuentra visiblemente triste y fastidiada porque siente que el resto del equipo ignora sus comentarios, catalogándola de "lenta" y diciendo que sus aportes son "pobres". Es verdad que ella no ha participado mucho y le cuesta el tema, pero genuinamente se está esforzando por entenderlo.

**Tu Objetivo:** Conversa con ella. Utiliza tu capacidad de escucha activa y asertividad para comprender la raíz del problema, validar sus emociones y demostrar una respuesta verdaderamente empática ante su frustración.
""")

st.warning("""
🗣️ **Instrucciones de voz importantes:** 1. Presiona el botón del micrófono y di claramente la palabra **'COMIENZA'** para activar el ejercicio e iniciar el diálogo con Camila.
2. Graba tus respuestas interactivas de manera sucesiva.
3. Cuando consideres que has cerrado la sesión o desees finalizar la prueba, menciona claramente la palabra **'TERMINAR'** al final de tu último mensaje.
""")

# Inicializar variables de sesión para el chat de voz
if "historial" not in st.session_state:
    st.session_state.historial = [{"role": "system", "content": PROMPT_SECRETO_CAMILA}]
    st.session_state.fase = "chat"
    st.session_state.conversacion_texto = ""
if "reporte_final" not in st.session_state:
    st.session_state.reporte_final = ""

# --- FASE 1: SIMULACIÓN POR VOZ (VERSIÓN ULTRA RÁPIDA) ---
if st.session_state.fase == "chat":
    
    st.markdown("### 🎙️ Graba tu mensaje aquí:")
    audio_grabado = mic_recorder(
        start_prompt="🔴 Presiona para Hablar",
        stop_prompt="⏹️ Detener Grabación",
        key="grabador_voz",
        format="wav"
    )
    
    if audio_grabado:
        # Usamos contenedores visuales dinámicos para limpiar la pantalla rápido
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
            
            if "TERMINAR" in texto_limpio:
                with st.spinner("Camila está procesando el reporte de evaluación final..."):
                    response_eval = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=st.session_state.historial
                    )
                    st.session_state.reporte_final = response_eval.choices[0].message.content
                    st.session_state.fase = "evaluacion"
                    st.rerun()
            
            else:
                # Combinamos los spinners informativos en uno solo para reducir el lag gráfico de Streamlit
                with st.spinner("Camila está pensando y hablando..."):
                    # 1. Generamos la respuesta de texto con GPT-4o-mini
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=st.session_state.historial
                    )
                    respuesta_camila = response.choices[0].message.content
                    st.session_state.historial.append({"role": "assistant", "content": respuesta_camila})
                    st.session_state.conversacion_texto += f"Camila: {respuesta_camila}\n\n"
                    
                    # 2. OPTIMIZACIÓN CRÍTICA TTS: Cambiamos a formato 'aac' que codifica 3x más rápido que el mp3 convencional
                    audio_response = client.audio.speech.create(
                        model="tts-1",
                        voice="nova",
                        input=respuesta_camila,
                        response_format="aac",  # Codificación instantánea sin compresión pesada
                        speed=1.12             # Un toque extra de velocidad al hablar hace sentir la app más ágil
                    )
                    audio_response.write_to_file("camila_voz.aac")
                
                # Renderizado inmediato de la interfaz
                estado.empty()
                st.markdown("### 🗣️ Camila dice:")
                st.audio("camila_voz.aac", format="audio/aac", autoplay=True)

        except Exception as e:
            st.error(f"Hubo un problema con la API: {e}")

# --- FASE 2: MOSTRAR EVALUACIÓN Y GUARDAR EN GOOGLE SHEETS ---
elif st.session_state.fase == "evaluacion":
    st.success("🏁 ¡Simulación Finalizada!")
    st.markdown("## 📊 Reporte de Evaluación de Respuesta Empática")
    st.write(st.session_state.reporte_final)
    
    st.markdown("---")
    st.markdown("#### 🚀 Registro Centralizado:")
    
    # Botón para Google Sheets
    if st.button("📊 Enviar conversación a Google Sheets central"):
        with st.spinner("Guardando en la base de datos..."):
            try:
                url_hoja = "https://docs.google.com/spreadsheets/d/1wRZoKUEbvVfrETp7aUnjyzl9qNW99XhbGLGWocngJuQ/edit"
                
                conn = st.connection("gsheets", type=GSheetsConnection)
                df_existente = conn.read(spreadsheet=url_hoja, usecols=[0, 1, 2])
                
                fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                nueva_fila = pd.DataFrame([{
                    "Fecha": fecha_actual,
                    "Historial_Completo": st.session_state.conversacion_texto,
                    "Reporte_Evaluacion": st.session_state.reporte_final
                }])
                
                df_existente = df_existente.dropna(how="all")
                df_actualizado = pd.concat([df_existente, nueva_fila], ignore_index=True)
                conn.update(spreadsheet=url_hoja, data=df_actualizado)
                
                st.success("¡Transmisión completada! Los resultados del nuevo caso han sido indexados correctamente.")
            except Exception as e:
                st.error(f"No se pudo registrar en la nube: {e}")
                
    # Botón para reiniciar el caso
    if st.button("🔄 Reiniciar Simulador"):
        st.session_state.clear()
        st.rerun()

# --- HISTORIAL VISUAL DE LA CONVERSACIÓN ---
if st.session_state.conversacion_texto:
    st.markdown("---")
    st.markdown("### 💬 Transcripción de la conversación:")
    
    texto_con_iconos = st.session_state.conversacion_texto
    texto_con_iconos = texto_con_iconos.replace("Tú:", "👤 **Tú:**")
    texto_con_iconos = texto_con_iconos.replace("Camila:", "👩‍💼 **Camila:**")
    
    st.markdown(texto_con_iconos)