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

# El prompt con las reglas secretas de Camila y los criterios de evaluación (PROHIBIDAS LAS PALABRAS SOECES)
PROMPT_SECRETO_CAMILA = """
Ponte en el rol de una persona de sexo mujer, llamada Camila, que está fastidiada y triste. Está en un equipo universitario poco organizado. Ha sido discriminada en repetidas ocasiones y se siente muy victimizada. Le han dicho frases como "es que eres muy lenta", "no entiendes las explicaciones de la profesora", "tus aportes son muy pobres", "lo hacemos nosotros o si no sacaremos mala nota". Estamos en una reunión de equipo y empezarás el diálogo molesta, con un tono de ironía y vulnerabilidad. Yo seré un integrante que tratará de empatizar contigo y buscar una solución. Trata que mis respuestas no te sean tan convincentes en primera instancia, pero si logro explicarlo de forma favorable tomarás mayor comprensión y apertura a mis respuestas. Si me confundo en algo, me lo harás saber de una forma bastante sarcástica. BAJO NINGUNA CIRCUNSTANCIA UTILICES PROFANIDADES O PALABRAS SOECES. Para iniciar el ejercicio el alumno dirá algo para saludarte. Cuando el alumno mencione firmemente la palabra "TERMINAR", el ejercicio finalizará de inmediato. En ese momento, saldrás del personaje de Camila y actuarás como un evaluador profesional de habilidades blandas. Debes redactar un reporte detallado que incluya: 1) Análisis de la escucha activa y empatía del alumno. 2) Evaluación de la claridad de sus planteamientos. 3) Un porcentaje de efectividad de 0 a 100% justificando minuciosamente el porqué de esa nota. 4) Recomendaciones puntuales con los aspectos que son necesarios de mejorar.
"""

# Inicializar cliente de OpenAI
client = OpenAI(api_key=API_KEY_OPENAI)

st.set_page_config(page_title="Evaluación de Competencias Directivas", page_icon="🎙️", layout="centered")

# --- 2. INTERFAZ VISUAL DEL ALUMNO (Lo único que él puede ver) ---
st.title("🎙️ Simulador de Habilidades Blandas")
st.markdown("---")

st.subheader("Caso de Estudio: Mediación y Manejo de Conflictos")
st.info("""
**Contexto del caso:** Te encuentras en una reunión de grupo de la universidad para coordinar la entrega final. El ambiente está bastante tenso. Tu compañera Camila se encuentra visiblemente afectada, molesta y a la defensiva debido a comentarios excluyentes que recibió anteriormente en el equipo.

**Tu Objetivo:** Utiliza tu empatía, escucha activa y asertividad para conversar con ella, disminuir la tensión del conflicto y guiar la situación hacia una solución colaborativa.
""")

st.warning("🗣️ **Instrucciones de voz:** Presiona el botón del micrófono para empezar a grabar tu respuesta. Cuando consideres que has cerrado la negociación con éxito o desees finalizar la prueba, menciona claramente la palabra **'TERMINAR'** al final de tu mensaje.")

# Inicializar variables de sesión para el chat de voz
if "historial" not in st.session_state:
    st.session_state.historial = [{"role": "system", "content": PROMPT_SECRETO_CAMILA}]
    st.session_state.fase = "chat"
    st.session_state.conversacion_texto = ""
if "reporte_final" not in st.session_state:
    st.session_state.reporte_final = ""

# --- FASE 1: SIMULACIÓN POR VOZ ---
if st.session_state.fase == "chat":
    
    st.markdown("### 🎙️ Graba tu mensaje para Camila:")
    # Componente de micrófono que procesa el audio
    audio_grabado = mic_recorder(
        start_prompt="🔴 Presiona para Hablar",
        stop_prompt="⏹️ Detener Grabación",
        key="grabador_voz",
        format="wav"
    )
    
    if audio_grabado:
        # Enviar el audio grabado a la API de OpenAI para transcribirlo a texto (Whisper)
        with st.spinner("Transcribiendo tu voz..."):
            try:
                # Guardar temporalmente el archivo de audio del alumno
                with open("alumno_audio.wav", "wb") as f:
                    f.write(audio_grabado["bytes"])
                
                # Transcribir usando OpenAI
                with open("alumno_audio.wav", "rb") as audio_file:
                    transcripcion = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file
                    )
                
                texto_alumno = transcripcion.text
                st.session_state.conversacion_texto += f"Tú: {texto_alumno}\n\n"
                st.session_state.historial.append({"role": "user", "content": texto_alumno})
                
                # Verificar si el alumno dijo "TERMINAR" en su audio para pasar a evaluación
                if "TERMINAR" in texto_alumno.upper():
                    with st.spinner("Generando reporte de evaluación final..."):
                        response_eval = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=st.session_state.historial
                        )
                        st.session_state.reporte_final = response_eval.choices[0].message.content
                        st.session_state.fase = "evaluacion"
                        st.rerun()
                
                # Generar respuesta normal de Camila en personaje
                with st.spinner("Camila está procesando tu respuesta..."):
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=st.session_state.historial
                    )
                    respuesta_camila = response.choices[0].message.content
                    st.session_state.historial.append({"role": "assistant", "content": respuesta_camila})
                    st.session_state.conversacion_texto += f"Camila: {respuesta_camila}\n\n"
                    
                    # Convertir respuesta de Camila a audio con OpenAI TTS
                    with st.spinner("Generando voz premium..."):
                        audio_response = client.audio.speech.create(
                            model="tts-1",
                            voice="nova",  # Voz femenina, profesional y clara
                            input=respuesta_camila,
                            speed=1.10    # Velocidad un poco más rápida y fluida
                        )
                    audio_response.write_to_file("camila_voz.mp3")
                    
                    # Reproducir automáticamente
                    st.markdown("### 🗣️ Camila dice:")
                    st.audio("camila_voz.mp3", format="audio/mp3", autoplay=True)

            except Exception as e:
                st.error(f"Hubo un problema con la API: {e}")

# --- FASE 2: MOSTRAR EVALUACIÓN Y GUARDAR EN GOOGLE SHEETS ---
elif st.session_state.fase == "evaluacion":
    st.success("🏁 ¡Simulación Finalizada!")
    st.markdown("## 📊 Reporte de Evaluación de Habilidades Blandas")
    st.write(st.session_state.reporte_final)
    
    st.markdown("---")
    st.markdown("#### 🚀 Guardar Reporte del Docente:")
    
    # Botón automático para subir todo a la nube de Google Sheets
    if st.button("📊 Enviar conversación a Google Sheets central"):
        with st.spinner("Guardando en la base de datos..."):
            try:
                # Tu hoja de cálculo real integrada y enlazada correctamente
                url_hoja = "https://docs.google.com/spreadsheets/d/1wRZoKUEbvVfrETp7aUnjyzl9qNW99XhbGLGWocngJuQ/edit"
                
                conn = st.connection("gsheets", type=GSheetsConnection)
                df_existente = conn.read(spreadsheet=url_hoja, usecols=[0, 1])
                
                fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                nueva_fila = pd.DataFrame([{
                    "Fecha": fecha_actual,
                    "Historial_Completo": st.session_state.conversacion_texto
                }])
                
                df_actualizado = pd.concat([df_existente, nueva_fila], ignore_index=True)
                conn.update(spreadsheet=url_hoja, data=df_actualizado)
                
                st.success("¡Transmisión completada! La conversación ha sido registrada con éxito en 'Resultados_Simulador_Habilidades'.")
            except Exception as e:
                st.error(f"No se pudo registrar en la nube: {e}")
                
    if st.button("🔄 Reiniciar Simulador"):
        st.session_state.clear()
        st.rerun()

# --- HISTORIAL VISUAL DE LA CONVERSACIÓN (FRONTEND LIMPIO) ---
if st.session_state.conversacion_texto:
    st.markdown("---")
    st.markdown("### 💬 Transcripción de la conversación:")
    
    # Tomamos el texto original sin duplicados
    texto_con_iconos = st.session_state.conversacion_texto
    
    # Reemplazamos los nombres por versiones estilizadas con emoticones
    texto_con_iconos = texto_con_iconos.replace("Tú:", "👤 Tú:")
    texto_con_iconos = texto_con_iconos.replace("Camila:", "👩‍💼 Camila:")
    
    # Mostramos el texto ya transformado
    st.write(texto_con_iconos)