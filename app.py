import streamlit as st
from openai import OpenAI
from streamlit_mic_recorder import mic_recorder
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import altair as alt
import os
import json
import tempfile
import uuid

# --- 1. CONFIGURACIÓN DE APIS Y PÁGINA ---
API_KEY_OPENAI = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=API_KEY_OPENAI)
URL_HOJA = "https://docs.google.com/spreadsheets/d/1wRZoKUEbvVfrETp7aUnjyzl9qNW99XhbGLGWocngJuQ/edit?usp=sharing"


# --- FUNCIONES DE EVALUACIÓN PARA EL CASO CAMILA ---
PESOS_CAMILA = {
    "Reconocimiento emocional": 20,
    "Escucha activa e indagación": 25,
    "Validación emocional": 30,
    "Comprensión de perspectivas": 15,
    "Construcción conjunta de soluciones": 10,
}

def calcular_efectividad_camila(indicadores):
    """Calcula el puntaje de forma determinista a partir de niveles 0-4."""
    niveles_por_nombre = {item.get("nombre"): item.get("nivel", 0) for item in indicadores}
    puntaje = 0.0
    for nombre, peso in PESOS_CAMILA.items():
        try:
            nivel = int(niveles_por_nombre.get(nombre, 0))
        except (TypeError, ValueError):
            nivel = 0
        nivel = max(0, min(4, nivel))
        puntaje += (nivel / 4) * peso
    return round(puntaje, 2)

def normalizar_reporte_camila(reporte):
    """Valida y completa el JSON devuelto por el modelo."""
    indicadores_validos = []
    recibidos = {i.get("nombre"): i for i in reporte.get("indicadores", []) if isinstance(i, dict)}
    for nombre in PESOS_CAMILA:
        item = recibidos.get(nombre, {})
        try:
            nivel = int(item.get("nivel", 0))
        except (TypeError, ValueError):
            nivel = 0
        indicadores_validos.append({
            "nombre": nombre,
            "nivel": max(0, min(4, nivel)),
            "evidencia": str(item.get("evidencia", "No se identificó evidencia textual suficiente.")),
            "justificacion": str(item.get("justificacion", "No se proporcionó una justificación.")),
        })
    reporte["indicadores"] = indicadores_validos
    for campo in ["fortalezas", "oportunidades_mejora", "recomendaciones", "evolucion_interaccion", "limitaciones"]:
        valor = reporte.get(campo, [])
        if not isinstance(valor, list):
            valor = [str(valor)] if valor else []
        reporte[campo] = [str(x) for x in valor]
    reporte["porcentaje_efectividad"] = calcular_efectividad_camila(indicadores_validos)
    return reporte

def mostrar_reporte_camila(reporte):
    """Presenta la rúbrica analítica de Camila en Streamlit."""

    st.metric(
        "Efectividad global",
        f"{reporte.get('porcentaje_efectividad', 0):.1f}%"
    )

    # Mostrar esta aclaración únicamente a los docentes
    rol_actual = str(
        st.session_state.usuario_actual.get("Rol", "")
    ).strip().lower()

    if rol_actual == "docente":
        st.caption(
            "Puntaje calculado en Python a partir de cinco indicadores "
            "ponderados; cada indicador se califica de 0 a 4."
        )

    filas = []

    for item in reporte.get("indicadores", []):
        filas.append({
            "Indicador": item["nombre"],
            "Nivel (0-4)": item["nivel"],
            "Peso (%)": PESOS_CAMILA[item["nombre"]],
            "Evidencia textual": item["evidencia"],
        })
    st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)
    for item in reporte.get("indicadores", []):
        with st.expander(f"{item['nombre']} — Nivel {item['nivel']}/4"):
            st.markdown(f"**Evidencia:** {item['evidencia']}")
            st.markdown(f"**Justificación:** {item['justificacion']}")
    for titulo, campo in [
        ("Fortalezas", "fortalezas"),
        ("Oportunidades de mejora", "oportunidades_mejora"),
        ("Recomendaciones", "recomendaciones"),
        ("Evolución de la interacción", "evolucion_interaccion"),
        ("Limitaciones de la evaluación", "limitaciones"),
    ]:
        st.markdown(f"#### {titulo}")
        elementos = reporte.get(campo, [])
        if elementos:
            for elemento in elementos:
                st.markdown(f"- {elemento}")
        else:
            st.write("No se registraron elementos en esta sección.")


def mostrar_reporte_historial(reporte):
    """Muestra reportes de Camila estructurados y conserva Renato en texto."""

    if isinstance(reporte, dict):
        datos = reporte
    else:
        texto = str(reporte).strip()
        try:
            datos = json.loads(texto)
        except (json.JSONDecodeError, TypeError, ValueError):
            st.markdown(texto if texto else "Sin reporte registrado.")
            return

    # Los reportes de Camila contienen la clave "indicadores".
    if isinstance(datos, dict) and isinstance(datos.get("indicadores"), list):
        mostrar_reporte_camila(datos)
    else:
        # Renato y los reportes antiguos en texto mantienen su presentación original.
        st.markdown(str(reporte))


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

    # --- PESTAÑAS PRINCIPALES (DINÁMICAS SEGÚN ROL) ---
    es_docente = str(st.session_state.usuario_actual.get("Rol", "")).strip().lower() == "docente"
    titulo_pestaña_2 = "📊 Progreso de Alumnos" if es_docente else "📊 Mi Progreso"

    tab_simulador, tab_progreso = st.tabs(["🎙️ ¡Simular Ahora!", titulo_pestaña_2])

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
                "prompt_sistema": """Interpreta a Camila, una estudiante universitaria que se siente triste, frustrada y poco valorada porque sus compañeros ignoran sus comentarios, la llaman "lenta" y consideran pobres sus aportes. Es cierto que le cuesta comprender algunos contenidos y ha participado poco, pero está haciendo un esfuerzo genuino por aprender y cumplir su tarea.

La persona usuaria es un integrante del equipo que intentará conversar contigo de manera empática. Mantente en el personaje y responde de forma natural, breve y progresiva.

DINÁMICA DE LA CONVERSACIÓN:
- Comienza expresando tristeza, frustración y cierta desconfianza. No reveles toda la historia de golpe.
- Comparte detalles adicionales gradualmente cuando la persona haga preguntas pertinentes y demuestre que escucha.
- No te tranquilices automáticamente por frases genéricas como "te entiendo" o "no te preocupes". Observa si la respuesta reconoce concretamente lo que sientes.
- Si minimizan tu experiencia, te culpan, justifican al equipo o saltan directamente a dar soluciones, mantén la reserva y explica por qué no te ayuda.
- Si la persona parafrasea correctamente, pregunta con interés, valida tus emociones sin juzgar y reconoce tu esfuerzo específico, muestra gradualmente mayor confianza.
- Cuando exista suficiente comprensión, participa en la construcción conjunta de alternativas realistas para que puedas aportar y aprender. No aceptes cualquier propuesta sin valorar si responde a tus necesidades.
- No evalúes ni califiques a la persona durante la simulación.
- No atribuyas tono de voz, gestos ni conductas que no puedas observar en el texto.
- Nunca utilices profanidades ni palabras soeces.""",
                "prompt_evaluacion": """Eres un evaluador académico especializado en empatía y comunicación interpersonal. Evalúa únicamente las intervenciones TEXTUALES de la persona estudiante en la transcripción. No evalúes la calidad de las respuestas de Camila como si fueran acciones del estudiante.

CRITERIOS OBLIGATORIOS:
- Usa exclusivamente evidencia textual presente en la conversación. No inventes citas.
- No infieras tono de voz, volumen, pausas, lenguaje corporal, interrupciones reales ni intención no expresada. La transcripción proviene de reconocimiento automático de voz y puede contener errores.
- Distingue una frase empática concreta de una frase genérica. "Te entiendo" por sí sola no demuestra validación profunda.
- No penalices automáticamente ofrecer soluciones: evalúa si antes hubo reconocimiento, escucha e indagación suficientes.
- Si no hay evidencia, asigna nivel 0 o 1 según corresponda y explica la limitación.
- Asigna un nivel entero de 0 a 4 para cada indicador. No calcules ni inventes el porcentaje global: Python lo calculará usando los pesos establecidos.

RÚBRICA ANALÍTICA (niveles: 0 = No evidenciado; 1 = Inicial; 2 = En desarrollo; 3 = Logrado; 4 = Destacado):
1. Reconocimiento emocional (20%): identifica emociones y situación concreta de Camila. 0: no reconoce; 1: reconocimiento vago o incorrecto; 2: identifica una emoción/situación de forma general; 3: reconoce emociones y causas con precisión; 4: reconoce matices emocionales y los refleja con sensibilidad.
2. Escucha activa e indagación (25%): hace preguntas abiertas, pertinentes y de seguimiento; retoma lo expresado por Camila. 0: no indaga ni retoma; 1: preguntas cerradas/superficiales; 2: alguna pregunta pertinente sin profundizar; 3: indaga y retoma información relevante; 4: indagación progresiva, coherente y profunda que facilita ampliar la perspectiva.
3. Validación emocional (30%): legitima la experiencia emocional sin minimizar, juzgar ni justificar el trato recibido. 0: invalida o no valida; 1: usa fórmulas genéricas o ambiguas; 2: valida parcialmente; 3: valida explícitamente emociones y esfuerzo; 4: valida de manera específica, respetuosa y consistente, sin apresurar soluciones.
4. Comprensión de perspectivas (15%): demuestra que comprende la experiencia, necesidades y barreras de Camila sin asumir ni culpabilizar. 0: distorsiona o ignora su perspectiva; 1: comprensión superficial; 2: reconoce algunos factores; 3: integra emociones, dificultades y esfuerzo; 4: refleja con precisión la complejidad de su perspectiva y comprueba su comprensión.
5. Construcción conjunta de soluciones (10%): explora alternativas con Camila y considera sus necesidades. 0: no propone ni construye alternativas; 1: impone una solución apresurada; 2: propone una alternativa parcialmente pertinente; 3: consulta preferencias y acuerda pasos viables; 4: co-diseña alternativas específicas, realistas y acordadas.

DEVUELVE ÚNICAMENTE UN JSON VÁLIDO con esta estructura exacta:
{
  "indicadores": [
    {"nombre": "Reconocimiento emocional", "nivel": 0, "evidencia": "cita textual breve o ausencia de evidencia", "justificacion": "explicación basada en la rúbrica"},
    {"nombre": "Escucha activa e indagación", "nivel": 0, "evidencia": "...", "justificacion": "..."},
    {"nombre": "Validación emocional", "nivel": 0, "evidencia": "...", "justificacion": "..."},
    {"nombre": "Comprensión de perspectivas", "nivel": 0, "evidencia": "...", "justificacion": "..."},
    {"nombre": "Construcción conjunta de soluciones", "nivel": 0, "evidencia": "...", "justificacion": "..."}
  ],
  "fortalezas": ["..."],
  "oportunidades_mejora": ["..."],
  "recomendaciones": ["..."],
  "evolucion_interaccion": ["Describe cómo cambió la disposición de Camila, solo a partir del diálogo textual"],
  "limitaciones": ["Indica que solo se evaluó la transcripción textual y que el reconocimiento automático puede contener errores"]
}

Incluye citas textuales cortas y exactas cuando existan. Si la conversación es demasiado breve, indícalo y evita conclusiones fuertes. No agregues campos ni markdown fuera del JSON."""
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

        st.header("Centro de Simulación")
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
            st.session_state.ruta_audio_salida = None

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
        
        docentes_disponibles = obtener_lista_docentes()
        cursos_disponibles = [
            "Estrategia Personal",
            "Inteligencia Relacional",
            "Comunicación Efectiva",
            "Trabajo en Equipo",
            "Liderazgo Estratégico"
        ]
        
        with col_docente: 
            docente_seleccionado = st.selectbox("Selecciona tu docente:", docentes_disponibles, key="docente_sel")
        with col_curso: 
            curso_seleccionado = st.selectbox("Selecciona tu curso:", cursos_disponibles, key="curso_sel")

        st.warning("🗣️ **Instrucciones:**\n1. Verifica tus datos arriba.\n2. Presiona **'🚀 Iniciar Simulación'**.\n3. Graba tu voz para interactuar.\n4. Al finalizar, presiona **'🏁 Finalizar y Evaluar'**.")

        # --- FASE CHAT DE VOZ ---
        if st.session_state.fase == "chat":
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.button("🚀 Iniciar Simulación", use_container_width=True, disabled=st.session_state.simulacion_activa or not nombre_estudiante.strip()):
                    st.session_state.simulacion_activa = True
                    with st.spinner(f"Iniciando caso con {datos_caso['nombre_personaje']}..."):
                        # Insertar el nombre antes de iniciar el diálogo (evita la condición de longitud incorrecta).
                        st.session_state.historial.insert(
                            1,
                            {"role": "system", "content": f"El nombre de la persona que interactúa contigo es {nombre_estudiante}. Dirígete a ella por su nombre solo cuando resulte natural."}
                        )
                        st.session_state.historial.append({"role": "user", "content": "COMIENZA EL EJERCICIO"})
                        
                        response = client.chat.completions.create(model="gpt-4o-mini", messages=st.session_state.historial)
                        respuesta_personaje = response.choices[0].message.content
                        st.session_state.historial.append({"role": "assistant", "content": respuesta_personaje})
                        st.session_state.conversacion_texto += f"{datos_caso['nombre_personaje']}: {respuesta_personaje}\n\n"
                        
                        audio_response = client.audio.speech.create(
                            model="tts-1", voice=datos_caso["voice_config"], input=respuesta_personaje, response_format="aac", speed=1.12
                        )
                        ruta_audio_salida = os.path.join(tempfile.gettempdir(), f"simulador_{uuid.uuid4().hex}.aac")
                        audio_response.write_to_file(ruta_audio_salida)
                        st.session_state.ruta_audio_salida = ruta_audio_salida
                        st.session_state.reproducir_inicial = True
                    st.rerun()

            with col_btn2:
                if st.button("🏁 Finalizar y Evaluar", use_container_width=True, disabled=not st.session_state.simulacion_activa):
                    with st.spinner("Procesando reporte de evaluación final..."):
                        intervenciones_usuario = [m for m in st.session_state.historial if m["role"] == "user" and m["content"] != "COMIENZA EL EJERCICIO"]
                        palabras_totales = " ".join([m["content"] for m in intervenciones_usuario])
                        
                        es_caso_camila = caso_seleccionado.startswith("Caso 1: Camila")
                        if len(palabras_totales.strip()) < 5:
                            if es_caso_camila:
                                st.session_state.reporte_final = normalizar_reporte_camila({
                                    "indicadores": [],
                                    "fortalezas": [],
                                    "oportunidades_mejora": ["No se registró una interacción suficiente para demostrar las habilidades evaluadas."],
                                    "recomendaciones": ["Realiza una conversación con Camila y responde a sus intervenciones antes de finalizar."],
                                    "evolucion_interaccion": ["No fue posible observar una evolución por ausencia de diálogo."],
                                    "limitaciones": ["No hubo evidencia textual suficiente para evaluar la competencia."]
                                })
                            else:
                                st.session_state.reporte_final = """- **Aspectos Positivos:** Ninguno. No existió interacción real con el personaje.
- **Aspectos de Mejora:** Abandono o evasión del ejercicio práctico.
- **Recomendaciones:** Debió entablar un diálogo activo con el personaje para poner a prueba sus habilidades antes de finalizar la sesión.
- **Porcentaje de Efectividad:** 0%"""
                        else:
                            mensajes_evaluacion = [
                                {"role": "system", "content": datos_caso["prompt_evaluacion"]},
                                {"role": "user", "content": f"Evalúa esta transcripción de la simulación.\n\n{st.session_state.conversacion_texto}"}
                            ]
                            if es_caso_camila:
                                response_eval = client.chat.completions.create(
                                    model="gpt-4o-mini",
                                    messages=mensajes_evaluacion,
                                    response_format={"type": "json_object"},
                                    temperature=0.1
                                )
                                reporte_json = json.loads(response_eval.choices[0].message.content)
                                st.session_state.reporte_final = normalizar_reporte_camila(reporte_json)
                            else:
                                response_eval = client.chat.completions.create(model="gpt-4o-mini", messages=mensajes_evaluacion)
                                st.session_state.reporte_final = response_eval.choices[0].message.content
                        
                        st.session_state.fase = "evaluacion"
                    st.rerun()

            st.markdown("---")

            if getattr(st.session_state, 'reproducir_inicial', False):
                st.markdown(f"### 🗣️ {datos_caso['nombre_personaje']} dice:")
                st.audio(st.session_state.ruta_audio_salida, format="audio/aac", autoplay=True)
                st.session_state.reproducir_inicial = False

            if st.session_state.simulacion_activa:
                st.markdown("### 🎙️ Graba tu respuesta aquí:")
                audio_grabado = mic_recorder(start_prompt="🔴 Presiona para Hablar", stop_prompt="⏹️ Detener Grabación", key=f"grabador_{caso_seleccionado}", format="wav")
                
                if audio_grabado:
                    estado = st.empty()
                    try:
                        with estado.container():
                            st.write("⚡ *Procesando audio...*")
                            archivo_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                            ruta_audio = archivo_audio.name
                            try:
                                archivo_audio.write(audio_grabado["bytes"])
                                archivo_audio.close()
                                with open(ruta_audio, "rb") as audio_file:
                                    transcripcion = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
                            finally:
                                try:
                                    os.remove(ruta_audio)
                                except OSError:
                                    pass
                        
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
                            ruta_audio_salida = os.path.join(tempfile.gettempdir(), f"simulador_{uuid.uuid4().hex}.aac")
                            audio_response.write_to_file(ruta_audio_salida)
                            st.session_state.ruta_audio_salida = ruta_audio_salida
                        
                        estado.empty()
                        st.markdown(f"### 🗣️ {datos_caso['nombre_personaje']} dice:")
                        st.audio(st.session_state.ruta_audio_salida, format="audio/aac", autoplay=True)
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
            if isinstance(st.session_state.reporte_final, dict):
                mostrar_reporte_camila(st.session_state.reporte_final)
            else:
                st.markdown(st.session_state.reporte_final)
            
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
                        
                        # Camila ya tiene un puntaje calculado en Python. Renato conserva su extracción previa.
                        if isinstance(st.session_state.reporte_final, dict):
                            solo_porcentaje = f"{st.session_state.reporte_final.get('porcentaje_efectividad', 0):.2f}%"
                            reporte_para_guardar = json.dumps(st.session_state.reporte_final, ensure_ascii=False)
                        else:
                            proceso_nota = client.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=[
                                    {"role": "system", "content": "Extrae exclusivamente el porcentaje numérico de efectividad final. Responde solo con el número seguido de %."},
                                    {"role": "user", "content": str(st.session_state.reporte_final)}
                                ],
                                temperature=0
                            )
                            solo_porcentaje = proceso_nota.choices[0].message.content.strip()
                            reporte_para_guardar = str(st.session_state.reporte_final)
                        
                        nueva_fila = pd.DataFrame([{
                            "Fecha": fecha_actual, "Estudiante": nombre_estudiante if nombre_estudiante else "Anónimo",
                            "Docente": docente_seleccionado, "Curso": curso_seleccionado, "Caso_Evaluado": caso_seleccionado,
                            "Historial_Completo": st.session_state.conversacion_texto, "Reporte_Evaluacion": reporte_para_guardar,
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
    # PESTAÑA 2: PROGRESO DE ALUMNOS / MI PROGRESO
    # ==========================================
    with tab_progreso:
        st.header("Panel de Progreso")
        
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df_historico = conn.read(spreadsheet=URL_HOJA, worksheet="Hoja 1", ttl=0).dropna(how="all")
            
            # --- NORMALIZACIÓN DEL PORCENTAJE ---
            df_historico["Efectividad_Num"] = df_historico["Porcentaje_Efectividad"].astype(str).str.replace("%", "").str.strip()
            df_historico["Efectividad_Num"] = pd.to_numeric(df_historico["Efectividad_Num"], errors="coerce").fillna(0)
            
            # Si el valor en Sheets viene como decimal (ej. 0.25 en lugar de 25), lo multiplicamos por 100
            df_historico["Efectividad_Num"] = df_historico["Efectividad_Num"].apply(lambda x: x * 100 if 0 < x <= 1.0 else x)
            
            df_historico["Fecha"] = pd.to_datetime(df_historico["Fecha"], errors="coerce")
            
            rol_actual = str(st.session_state.usuario_actual["Rol"]).strip().lower()

            # ------------------------------------------
            # VISTA PARA ESTUDIANTES
            # ------------------------------------------
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
                    
                    # Gráfico con eje Y de 0 a 100
                    chart_estudiante = alt.Chart(df_mi_progreso).mark_line(point=True).encode(
                        x=alt.X('Fecha:T', title='Fecha y Hora'),
                        y=alt.Y('Efectividad_Num:Q', title='Porcentaje (%)', scale=alt.Scale(domain=[0, 100])),
                        tooltip=['Fecha', 'Caso_Evaluado', 'Efectividad_Num']
                    ).properties(height=300)
                    st.altair_chart(chart_estudiante, use_container_width=True)
                    
                    st.subheader("📋 Historial de Feedback")
                    for _, row in df_mi_progreso.iterrows():
                        fecha_str = row["Fecha"].strftime("%Y-%m-%d %H:%M") if pd.notnull(row["Fecha"]) else "Sin fecha"
                        with st.expander(f"Caso: {row['Caso_Evaluado']} | Nota: {row['Efectividad_Num']:.1f}% ({fecha_str})"):
                            st.markdown(f"**Docente:** {row['Docente']}")
                            st.markdown("#### 📝 Reporte evaluativo")
                            reporte_guardado = row.get(
                                "Reporte_Evaluacion",
                                "Sin reporte registrado."
                            )
                            mostrar_reporte_historial(reporte_guardado)

            # ------------------------------------------
            # VISTA PARA DOCENTES
            # ------------------------------------------
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
                    
                    # Gráfico con eje Y de 0 a 100
                    chart_docente = alt.Chart(df_estudiante_sel).mark_line(point=True).encode(
                        x=alt.X('Fecha:T', title='Fecha y Hora'),
                        y=alt.Y('Efectividad_Num:Q', title='Porcentaje (%)', scale=alt.Scale(domain=[0, 100])),
                        tooltip=['Fecha', 'Caso_Evaluado', 'Efectividad_Num']
                    ).properties(height=300)
                    st.altair_chart(chart_docente, use_container_width=True)
                    
                    # --- VISTA DETALLADA DE INTERACCIONES Y REPORTE PARA DOCENTE ---
                    st.subheader("📋 Detalle de Interacciones y Reportes Evaluativos")
                    
                    for idx, row in df_estudiante_sel.iterrows():
                        fecha_str = row["Fecha"].strftime("%Y-%m-%d %H:%M") if pd.notnull(row["Fecha"]) else "Sin fecha"
                        nota_display = f"{row['Efectividad_Num']:.1f}%"
                        
                        with st.expander(f"📌 {fecha_str} | Caso: {row['Caso_Evaluado']} | Nota: {nota_display}"):
                            st.markdown(f"**Curso:** {row.get('Curso', 'N/A')}")
                            st.markdown("---")
                            
                            col_reporte, col_transcripcion = st.columns(2)
                            
                            with col_reporte:
                                st.markdown("#### 📝 Reporte Evaluativo Recibido:")
                                reporte_guardado = row.get(
                                    "Reporte_Evaluacion",
                                    "Sin reporte registrado."
                                )
                                mostrar_reporte_historial(reporte_guardado)
                                
                            with col_transcripcion:
                                st.markdown("#### 💬 Transcripción de la Conversación:")
                                historial_txt = str(row.get("Historial_Completo", "Sin transcripción disponible."))
                                st.text_area(
                                    label="Historial de audio/texto:",
                                    value=historial_txt,
                                    height=300,
                                    key=f"historial_docente_{idx}"
                                )

        except Exception as e:
            st.error(f"No se pudieron cargar los datos de progreso desde la nube: {e}")
