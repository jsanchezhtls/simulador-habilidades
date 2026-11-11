import streamlit as st

# ==========================================
# 1. CONFIGURACIÓN INICIAL
# ==========================================

st.set_page_config(
    page_title="Simulador de Habilidades Blandas",
    page_icon="🎙️",
    layout="centered"
)

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


API_KEY_OPENAI = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=API_KEY_OPENAI)

URL_HOJA = (
    "https://docs.google.com/spreadsheets/d/"
    "1wRZoKUEbvVfrETp7aUnjyzl9qNW99XhbGLGWocngJuQ/edit?usp=sharing"
)


# ==========================================
# 2. RÚBRICA COMÚN DE EMPATÍA
# ==========================================

PESOS_EMPATIA = {
    "Reconocimiento emocional": 20,
    "Escucha activa e indagación": 25,
    "Validación emocional": 30,
    "Comprensión de perspectivas": 15,
    "Construcción conjunta de soluciones": 10,
}


def calcular_efectividad_empatia(indicadores):
    """
    Calcula el puntaje ponderado de empatía.
    Cada indicador se califica de 0 a 4.
    El resultado final se expresa de 0 a 100.
    """

    if not isinstance(indicadores, list):
        indicadores = []

    niveles_por_nombre = {}

    for item in indicadores:
        if isinstance(item, dict):
            nombre = item.get("nombre")
            niveles_por_nombre[nombre] = item.get("nivel", 0)

    puntaje = 0.0

    for nombre, peso in PESOS_EMPATIA.items():

        try:
            nivel = int(niveles_por_nombre.get(nombre, 0))
        except (TypeError, ValueError):
            nivel = 0

        nivel = max(0, min(4, nivel))

        puntaje += (nivel / 4) * peso

    return round(puntaje, 2)


def normalizar_reporte_empatia(reporte):
    """
    Valida y completa el reporte común de los tres casos de empatía.
    Garantiza que siempre existan los cinco indicadores.
    """

    if not isinstance(reporte, dict):
        reporte = {}

    indicadores_recibidos = reporte.get("indicadores", [])

    if not isinstance(indicadores_recibidos, list):
        indicadores_recibidos = []

    recibidos = {
        item.get("nombre"): item
        for item in indicadores_recibidos
        if isinstance(item, dict)
    }

    indicadores_validos = []

    for nombre in PESOS_EMPATIA:

        item = recibidos.get(nombre, {})

        if not isinstance(item, dict):
            item = {}

        try:
            nivel = int(item.get("nivel", 0))
        except (TypeError, ValueError):
            nivel = 0

        nivel = max(0, min(4, nivel))

        indicadores_validos.append({
            "nombre": nombre,
            "nivel": nivel,
            "evidencia": str(
                item.get(
                    "evidencia",
                    "No se identificó evidencia textual suficiente."
                )
            ),
            "justificacion": str(
                item.get(
                    "justificacion",
                    "No se proporcionó una justificación."
                )
            )
        })

    reporte["indicadores"] = indicadores_validos

    campos_lista = [
        "fortalezas",
        "oportunidades_mejora",
        "recomendaciones",
        "evolucion_interaccion",
        "limitaciones"
    ]

    for campo in campos_lista:

        valor = reporte.get(campo, [])

        if not isinstance(valor, list):
            valor = [str(valor)] if valor else []

        reporte[campo] = [str(x) for x in valor]

    # El porcentaje siempre se calcula en Python.
    reporte["porcentaje_efectividad"] = (
        calcular_efectividad_empatia(indicadores_validos)
    )

    return reporte


def mostrar_reporte_empatia(reporte):
    """
    Muestra la evaluación estructurada de empatía.
    Se utiliza para Arturo, Camila y Valeria.
    """

    reporte = normalizar_reporte_empatia(reporte)

    st.metric(
        "Efectividad global",
        f"{reporte.get('porcentaje_efectividad', 0):.1f}%"
    )

    rol_actual = str(
        st.session_state.usuario_actual.get("Rol", "")
    ).strip().lower()

    if rol_actual == "docente":
        st.caption(
            "Puntaje calculado en Python a partir de cinco indicadores "
            "ponderados. Cada indicador se califica de 0 a 4."
        )

    filas = []

    for item in reporte.get("indicadores", []):

        filas.append({
            "Indicador": item["nombre"],
            "Nivel (0-4)": item["nivel"],
            "Peso (%)": PESOS_EMPATIA[item["nombre"]],
            "Evidencia textual": item["evidencia"]
        })

    st.dataframe(
        pd.DataFrame(filas),
        use_container_width=True,
        hide_index=True
    )

    for item in reporte.get("indicadores", []):

        with st.expander(
            f"{item['nombre']} — Nivel {item['nivel']}/4"
        ):

            st.markdown(
                f"**Evidencia:** {item['evidencia']}"
            )

            st.markdown(
                f"**Justificación:** {item['justificacion']}"
            )

    for titulo, campo in [
        ("Fortalezas", "fortalezas"),
        ("Oportunidades de mejora", "oportunidades_mejora"),
        ("Recomendaciones", "recomendaciones"),
        ("Evolución de la interacción", "evolucion_interaccion"),
        ("Limitaciones de la evaluación", "limitaciones")
    ]:

        st.markdown(f"#### {titulo}")

        elementos = reporte.get(campo, [])

        if elementos:

            for elemento in elementos:
                st.markdown(f"- {elemento}")

        else:
            st.write(
                "No se registraron elementos en esta sección."
            )


def mostrar_reporte_historial(reporte):
    """
    Interpreta reportes guardados en Google Sheets.

    Los reportes de empatía se muestran con la rúbrica.
    El reporte narrativo de Renato se conserva como texto.
    """

    if isinstance(reporte, dict):

        datos = reporte

    else:

        texto = str(reporte).strip()

        try:
            datos = json.loads(texto)

        except (json.JSONDecodeError, TypeError, ValueError):

            st.markdown(
                texto if texto else "Sin reporte registrado."
            )
            return

    if (
        isinstance(datos, dict)
        and isinstance(datos.get("indicadores"), list)
    ):

        mostrar_reporte_empatia(datos)

    else:

        st.markdown(str(reporte))


# ==========================================
# 3. ESTILOS
# ==========================================

st.markdown("""
<style>
#stMainMenu,
.stAppDeployButton,
button[title="Manage app"],
iframe[title="streamlit-modal"] {
    display: none !important;
    visibility: hidden !important;
}

footer {
    visibility: hidden !important;
}

.viewerBadge_container__1QSob,
.st-emotion-cache-6awft0 a {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)


# ==========================================
# 4. CONTROL DE SESIÓN
# ==========================================

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if "usuario_actual" not in st.session_state:
    st.session_state.usuario_actual = None


# ==========================================
# 5. AUTENTICACIÓN
# ==========================================

def verificar_credenciales(correo, password):

    correo_clean = correo.strip().lower()
    pass_clean = str(password).strip()

    try:

        conn = st.connection(
            "gsheets",
            type=GSheetsConnection
        )

        df_usuarios = conn.read(
            spreadsheet=URL_HOJA,
            worksheet="Usuarios",
            ttl=0
        ).dropna(how="all")

        df_usuarios.columns = [
            str(col).strip()
            for col in df_usuarios.columns
        ]

        if (
            "Correo" in df_usuarios.columns
            and "Contraseña" in df_usuarios.columns
        ):

            df_usuarios["Correo"] = (
                df_usuarios["Correo"]
                .astype(str)
                .str.strip()
                .str.lower()
            )

            df_usuarios["Contraseña"] = (
                df_usuarios["Contraseña"]
                .astype(str)
                .str.strip()
                .str.replace(".0", "", regex=False)
            )

            match = df_usuarios[
                (df_usuarios["Correo"] == correo_clean)
                & (df_usuarios["Contraseña"] == pass_clean)
            ]

            if not match.empty:
                return match.iloc[0].to_dict()

        else:

            st.error(
                "No se encontraron las columnas "
                "'Correo' o 'Contraseña' en Usuarios."
            )

    except Exception as e:

        st.error(
            f"Error al conectar con la base de datos de usuarios: {e}"
        )

    return None


def obtener_lista_docentes():

    try:

        conn = st.connection(
            "gsheets",
            type=GSheetsConnection
        )

        df_usuarios = conn.read(
            spreadsheet=URL_HOJA,
            worksheet="Usuarios",
            ttl=60
        ).dropna(how="all")

        df_usuarios.columns = [
            str(col).strip()
            for col in df_usuarios.columns
        ]

        if (
            "Rol" in df_usuarios.columns
            and "Nombre_Completo" in df_usuarios.columns
        ):

            mask_docentes = (
                df_usuarios["Rol"]
                .astype(str)
                .str.strip()
                .str.lower() == "docente"
            )

            lista_docentes = (
                df_usuarios[mask_docentes]["Nombre_Completo"]
                .dropna()
                .unique()
                .tolist()
            )

            if lista_docentes:
                return sorted(lista_docentes)

    except Exception as e:

        st.warning(
            f"No se pudo cargar la lista de docentes: {e}"
        )

    return ["Sin docentes registrados"]
# ==========================================
# 6. PROMPT COMÚN DE EVALUACIÓN DE EMPATÍA
# ==========================================

PROMPT_EVALUACION_EMPÁTICA = """
Eres un evaluador académico especializado en empatía y comunicación
interpersonal.

Evalúa únicamente las intervenciones TEXTUALES de la persona estudiante
en la transcripción. No evalúes las respuestas del personaje como si fueran
acciones del estudiante.

CRITERIOS OBLIGATORIOS:
- Utiliza exclusivamente evidencia textual presente en la conversación.
- No inventes citas ni atribuyas expresiones que no aparecen.
- No infieras tono de voz, volumen, pausas, lenguaje corporal,
  interrupciones reales ni intenciones no expresadas.
- La transcripción proviene de reconocimiento automático de voz
  y puede contener errores.
- Distingue una frase empática concreta de una frase genérica.
- "Te entiendo" por sí sola no demuestra validación profunda.
- No penalices automáticamente ofrecer soluciones: evalúa si antes hubo
  reconocimiento, escucha e indagación suficientes.
- Si no hay evidencia, asigna nivel 0 o 1 según corresponda.
- Asigna un nivel entero de 0 a 4 para cada indicador.
- No calcules ni inventes el porcentaje global: Python lo calculará.

RÚBRICA ANALÍTICA:

Niveles:
0 = No evidenciado
1 = Inicial
2 = En desarrollo
3 = Logrado
4 = Destacado

1. Reconocimiento emocional (20%):
Identifica emociones y situación concreta del personaje.
0: No reconoce emociones ni situación.
1: Reconocimiento vago o incorrecto.
2: Identifica una emoción o situación de forma general.
3: Reconoce emociones y causas con precisión.
4: Reconoce matices emocionales y los refleja con sensibilidad.

2. Escucha activa e indagación (25%):
Hace preguntas abiertas, pertinentes y de seguimiento;
retoma lo expresado por el personaje.
0: No indaga ni retoma.
1: Preguntas cerradas o superficiales.
2: Alguna pregunta pertinente sin profundizar.
3: Indaga y retoma información relevante.
4: Indagación progresiva, coherente y profunda que facilita ampliar
la perspectiva.

3. Validación emocional (30%):
Legitima la experiencia emocional sin minimizar, juzgar
ni justificar el trato recibido.
0: Invalida o no valida.
1: Fórmulas genéricas o ambiguas.
2: Valida parcialmente.
3: Valida explícitamente emociones y esfuerzo.
4: Valida de manera específica, respetuosa y consistente,
sin apresurar soluciones.

4. Comprensión de perspectivas (15%):
Demuestra comprensión de la experiencia, necesidades y barreras
del personaje sin asumir ni culpabilizar.
0: Distorsiona o ignora su perspectiva.
1: Comprensión superficial.
2: Reconoce algunos factores.
3: Integra emociones, dificultades y esfuerzo.
4: Refleja con precisión la complejidad de su perspectiva
y comprueba su comprensión.

5. Construcción conjunta de soluciones (10%):
Explora alternativas con el personaje y considera sus necesidades.
0: No propone ni construye alternativas.
1: Impone una solución apresurada.
2: Propone una alternativa parcialmente pertinente.
3: Consulta preferencias y acuerda pasos viables.
4: Co-diseña alternativas específicas, realistas y acordadas.

CONSIDERACIONES SEGÚN EL CASO:
- Arturo: considera su necesidad de reconocimiento y valoración.
- Camila: considera la exclusión, los comentarios descalificadores
  y el esfuerzo que realiza para aprender.
- Valeria: considera la sobrecarga, la desconfianza, las emociones
  contradictorias y el respeto a sus límites personales.
  No penalices al estudiante por no conseguir que Valeria revele
  información privada. Respetar su privacidad puede ser una evidencia
  positiva de empatía.

INSTRUCCIONES OBLIGATORIAS PARA LAS CINCO SECCIONES DESCRIPTIVAS:

1. "fortalezas":
- Incluye entre 1 y 3 fortalezas observables en las intervenciones
  del estudiante.
- Cada fortaleza debe describir una conducta concreta y explicar
  brevemente por qué constituye una actuación empática.
- Cuando sea posible, incorpora una cita textual breve y exacta.
- Si no se observa ninguna fortaleza, escribe un elemento que lo indique
  explícitamente y explica que la transcripción no aporta evidencia.

2. "oportunidades_mejora":
- Incluye entre 1 y 3 aspectos específicos que el estudiante necesita
  desarrollar.
- Relaciona cada aspecto con uno o más indicadores de la rúbrica.
- Explica qué hizo o dejó de hacer el estudiante y qué efecto observable
  tuvo en el desarrollo de la conversación.
- No confundas la falta de información del personaje con una deficiencia
  del estudiante.
- Si no hay evidencia suficiente para identificar una oportunidad concreta,
  indícalo expresamente.

3. "recomendaciones":
- Incluye entre 2 y 3 recomendaciones prácticas, específicas y aplicables
  en una próxima conversación.
- Prioriza los indicadores con menor nivel.
- Formula acciones que el estudiante pueda realizar; evita consejos vagos
  como "ser más empático" o "escuchar mejor".
- Adapta las recomendaciones a la dificultad y situación del caso.

4. "evolucion_interaccion":
- Describe cómo se desarrolló la interacción desde el inicio hasta el cierre.
- Señala cambios observables en las respuestas del personaje y relaciónalos
  con las intervenciones textuales del estudiante, sin atribuir causalidad
  cuando no exista evidencia suficiente.
- Si la conversación fue demasiado breve para identificar evolución,
  indícalo expresamente.

5. "limitaciones":
- Incluye al menos la limitación de que la evaluación se basa en una
  transcripción textual obtenida mediante reconocimiento automático
  de voz, que puede contener errores.
- Añade otras limitaciones únicamente si realmente se desprenden
  de la conversación (por ejemplo, diálogo breve o ausencia de oportunidades
  para observar algún indicador).
- Distingue entre una habilidad no demostrada y una habilidad que no pudo
  evaluarse por falta de oportunidad.
- No inventes limitaciones.

REGLAS GENERALES DE CALIDAD:
- Ninguna de las cinco secciones descriptivas debe quedar como una lista vacía.
- No uses listas vacías como respuesta final: cada sección debe contener
  al menos un elemento informativo.
- Toda valoración debe basarse en la transcripción y ser coherente con
  los niveles asignados en los cinco indicadores.
- No repitas la misma observación en todas las secciones.
- Si la interacción es muy breve, evita conclusiones contundentes y explica
  esa limitación.
- Las respuestas deben ser claras, formativas, respetuosas y útiles
  para que el estudiante sepa qué hizo bien y cómo puede mejorar.

DEVUELVE ÚNICAMENTE UN JSON VÁLIDO, sin comentarios ni bloques Markdown.
Debes incluir exactamente los cinco indicadores y las cinco secciones
descriptivas indicadas. No omitas ninguna clave.

ESTRUCTURA OBLIGATORIA DEL JSON:
{
  "indicadores": [
    {
      "nombre": "Reconocimiento emocional",
      "nivel": 0,
      "evidencia": "Cita textual breve y exacta o indicación explícita de ausencia de evidencia.",
      "justificacion": "Justificación vinculada con el descriptor de la rúbrica."
    },
    {
      "nombre": "Escucha activa e indagación",
      "nivel": 0,
      "evidencia": "Cita textual breve y exacta o indicación explícita de ausencia de evidencia.",
      "justificacion": "Justificación vinculada con el descriptor de la rúbrica."
    },
    {
      "nombre": "Validación emocional",
      "nivel": 0,
      "evidencia": "Cita textual breve y exacta o indicación explícita de ausencia de evidencia.",
      "justificacion": "Justificación vinculada con el descriptor de la rúbrica."
    },
    {
      "nombre": "Comprensión de perspectivas",
      "nivel": 0,
      "evidencia": "Cita textual breve y exacta o indicación explícita de ausencia de evidencia.",
      "justificacion": "Justificación vinculada con el descriptor de la rúbrica."
    },
    {
      "nombre": "Construcción conjunta de soluciones",
      "nivel": 0,
      "evidencia": "Cita textual breve y exacta o indicación explícita de ausencia de evidencia.",
      "justificacion": "Justificación vinculada con el descriptor de la rúbrica."
    }
  ],
  "fortalezas": [
    "Describe aquí una fortaleza observable o explica expresamente que no se identificaron fortalezas por falta de evidencia."
  ],
  "oportunidades_mejora": [
    "Describe aquí una oportunidad concreta o explica expresamente por qué no puede identificarse."
  ],
  "recomendaciones": [
    "Recomendación práctica y específica 1.",
    "Recomendación práctica y específica 2."
  ],
  "evolucion_interaccion": [
    "Describe la evolución observable o indica que la duración de la conversación no permite evaluarla."
  ],
  "limitaciones": [
    "La evaluación se basa en una transcripción textual generada mediante reconocimiento automático de voz, por lo que puede contener errores."
  ]
}

Incluye citas textuales cortas y exactas cuando existan.
Si la conversación es demasiado breve, indícalo y evita conclusiones fuertes.
No agregues campos ni texto fuera del JSON.
"""


# ==========================================
# 7. CASO ARTURO - NIVEL SENCILLO
# ==========================================

CASO_ARTURO = {
    "nivel_dificultad": "Sencillo",
    "evaluacion_estructurada": True,
    "titulo_interfaz": "Caso de Estudio: Empatía y Reconocimiento Personal",
    "nombre_personaje": "Arturo",
    "voice_config": "echo",

    "contexto": """
**Contexto del caso:** Te encuentras conversando con Arturo,
un compañero de equipo que participó en una exposición académica.
Aunque preparó una parte importante del trabajo, siente que durante
la presentación sus compañeros recibieron todos los reconocimientos
y nadie mencionó su contribución.

Arturo se siente desanimado y poco valorado. No está especialmente
molesto con el equipo y mantiene disposición para conversar, pero
necesita sentir que su esfuerzo fue reconocido.
""",

    "definicion_concepto": """
La **Empatía** es la capacidad de comprender y compartir los sentimientos
y perspectivas de los demás, validando sus emociones sin juzgar,
minimizar ni apresurarse a ofrecer soluciones.
""",

    "pautas_tips": """
* 👂 **Escucha activa:** Permite que Arturo explique qué ocurrió.
* ❤️ **Reconocimiento emocional:** Identifica su desánimo y necesidad
  de valoración.
* 🤝 **Validación:** Reconoce que es comprensible sentirse poco valorado.
* 🔍 **Indagación:** Pregunta qué significó para él esa experiencia.
* 🛠️ **Solución conjunta:** Explora cómo podrían reconocer mejor
  las contribuciones de todos.
""",

    "prompt_sistema": """
Interpreta a Arturo, un estudiante universitario que se siente desanimado
porque durante una exposición grupal sus compañeros recibieron
reconocimiento y nadie mencionó su contribución, a pesar de que preparó
una parte importante del trabajo.

La persona usuaria es un integrante de tu equipo que intentará conversar
contigo de manera empática.

PERSONALIDAD Y DIFICULTAD:
- Tu actitud es tranquila y accesible.
- No estás enojado ni buscas discutir.
- Te sientes poco valorado y algo decepcionado.
- Estás dispuesto a conversar y puedes confiar relativamente rápido
  cuando percibes interés genuino.
- Tu situación es sencilla de abordar, pero no debes resolverla
  automáticamente por el estudiante.

DINÁMICA:
- Comienza expresando que te sentiste invisible durante la exposición.
- No reveles todos los detalles de inmediato.
- Si la persona pregunta qué ocurrió, explica que preparaste una parte
  importante, pero nadie reconoció tu aporte.
- Si escucha, pregunta y reconoce tu esfuerzo, muestra progresivamente
  mayor tranquilidad.
- Si minimiza lo ocurrido, expresa que para ti sí tuvo significado.
- Si ofrece soluciones sin escucharte, indica que primero necesitas
  sentir que comprende lo ocurrido.
- Cuando exista suficiente comprensión, participa en la construcción
  de alternativas para que el equipo reconozca las contribuciones.
- No aceptes cualquier solución automáticamente.
- No evalúes ni califiques a la persona.
- No atribuyas tono de voz, gestos ni conductas no observables en el texto.
- Nunca utilices profanidades ni palabras soeces.
""",

    "prompt_evaluacion": PROMPT_EVALUACION_EMPÁTICA
}


# ==========================================
# 8. CASO CAMILA - NIVEL INTERMEDIO
# ==========================================

CASO_CAMILA = {
    "nivel_dificultad": "Intermedio",
    "evaluacion_estructurada": True,
    "titulo_interfaz": "Caso de Estudio: Empatía y Gestión de Equipos",
    "nombre_personaje": "Camila",
    "voice_config": "nova",

    "contexto": """
**Contexto del caso:** Te encuentras en una reunión con tu compañera
de grupo, Camila. Ella se encuentra visiblemente triste y fastidiada
porque siente que el resto del equipo ignora sus comentarios,
catalogándola de "lenta" y diciendo que sus aportes son "pobres".

Es verdad que ella no ha participado mucho y le cuesta el tema,
pero genuinamente se está esforzando por entenderlo.
""",

    "definicion_concepto": """
La **Empatía** es la capacidad de comprender y compartir los sentimientos
y perspectivas de los demás, validando sus emociones sin juzgar ni saltar
a conclusiones o soluciones apresuradas.
""",

    "pautas_tips": """
* 👂 **Escucha Activa:** No interrumpas a Camila mientras se desahoga.
* ❤️ **Valida sus Emociones:** Reconoce su sentir antes de proponer algo.
* 🚫 **Evita la Indiferencia:** No minimices su problema.
* 🛠️ **Co-diseña una Solución:** Pregúntale cómo se sentiría más cómoda
  participando.
""",

    "prompt_sistema": """
Interpreta a Camila, una estudiante universitaria que se siente triste,
frustrada y poco valorada porque sus compañeros ignoran sus comentarios,
la llaman "lenta" y consideran pobres sus aportes.

Es cierto que le cuesta comprender algunos contenidos y ha participado
poco, pero está haciendo un esfuerzo genuino por aprender y cumplir
su tarea.

La persona usuaria es un integrante del equipo que intentará conversar
contigo de manera empática. Mantente en el personaje y responde de forma
natural, breve y progresiva.

DINÁMICA:
- Comienza expresando tristeza, frustración y cierta desconfianza.
- No reveles toda la historia de golpe.
- Comparte detalles adicionales gradualmente cuando la persona haga
  preguntas pertinentes y demuestre que escucha.
- No te tranquilices automáticamente por frases genéricas.
- Si minimizan tu experiencia, te culpan o justifican al equipo,
  mantén la reserva y explica por qué no te ayuda.
- Si la persona parafrasea correctamente, pregunta con interés,
  valida tus emociones sin juzgar y reconoce tu esfuerzo específico,
  muestra gradualmente mayor confianza.
- Cuando exista suficiente comprensión, participa en la construcción
  conjunta de alternativas realistas para que puedas aportar y aprender.
- No aceptes cualquier propuesta sin valorar si responde a tus necesidades.
- No evalúes ni califiques a la persona durante la simulación.
- No atribuyas tono de voz, gestos ni conductas que no puedas observar.
- Nunca utilices profanidades ni palabras soeces.
""",

    "prompt_evaluacion": PROMPT_EVALUACION_EMPÁTICA
}


# ==========================================
# 9. CASO VALERIA - NIVEL AVANZADO
# ==========================================

CASO_VALERIA = {
    "nivel_dificultad": "Avanzado",
    "evaluacion_estructurada": True,
    "titulo_interfaz": "Caso de Estudio: Empatía en Situaciones Complejas",
    "nombre_personaje": "Valeria",
    "voice_config": "shimmer",

    "contexto": """
**Contexto del caso:** Valeria es una integrante de tu equipo que
últimamente ha tenido dificultades para cumplir algunos plazos y entregar
sus actividades. Durante una conversación manifiesta sentirse
sobrecargada, poco comprendida y constantemente cuestionada por sus errores.

Percibe que el equipo solo observa aquello que no logra completar
y no considera el esfuerzo que está realizando. Además, atraviesa
circunstancias personales que afectan su disponibilidad, pero no desea
hablar abiertamente de ellas.

Se muestra desconfiada, responde de manera reservada y tiene sentimientos
contradictorios frente al equipo. Necesitarás construir confianza sin
presionarla ni invadir sus límites personales.
""",

    "definicion_concepto": """
La **Empatía avanzada** implica comprender experiencias emocionales
complejas, reconocer necesidades que no siempre se expresan directamente,
validar sin juzgar y respetar los límites personales de los demás.

Ser empático no significa exigir que una persona revele sus problemas
privados ni asumir la responsabilidad de resolverlos.
""",

    "pautas_tips": """
* 👂 **Escucha profunda:** Atiende lo que Valeria expresa sin hacer
  suposiciones.
* ❤️ **Validación emocional:** Reconoce su sobrecarga, frustración
  y sensación de falta de comprensión.
* 🔍 **Indagación respetuosa:** Formula preguntas abiertas sin presionarla
  para revelar información personal.
* 🧭 **Respeto por los límites:** Comprende que puede necesitar apoyo
  sin tener que explicar sus circunstancias privadas.
* 🤝 **Comprensión de perspectivas:** Considera sus necesidades
  y las responsabilidades compartidas del equipo.
* 🛠️ **Construcción conjunta:** Busca acuerdos realistas sobre tareas,
  prioridades, comunicación y apoyo.
""",

    "prompt_sistema": """
Interpreta a Valeria, una estudiante universitaria que forma parte
de un equipo de trabajo. En las últimas semanas ha tenido dificultades
para cumplir algunos plazos y completar todas sus actividades.

Te sientes sobrecargada, frustrada y poco comprendida. Percibes que
tus compañeros solo observan tus errores y retrasos, sin reconocer
el esfuerzo que estás realizando.

Además, atraviesas algunas circunstancias personales que están afectando
tu disponibilidad y concentración. Sin embargo, no deseas compartir
detalles privados con tus compañeros.

La persona usuaria es integrante de tu equipo e intentará conversar
contigo de manera empática.

PERSONALIDAD Y DIFICULTAD:
- Tu actitud inicial es reservada y desconfiada.
- Puedes responder brevemente y mostrar cierta resistencia.
- Experimentas emociones contradictorias: frustración, cansancio,
  preocupación y deseo de que el equipo comprenda tu situación.
- No confías rápidamente en la persona.
- Necesitas comprobar que realmente te escucha y no busca juzgarte.
- La situación es compleja y requiere una conversación cuidadosa.
- No debes revelar toda tu situación personal ni confiar automáticamente
  después de una frase empática.

DINÁMICA DE LA CONVERSACIÓN:

1. INICIO:
- Comienza expresando frustración porque sientes que el equipo solo
  señala tus errores y retrasos.
- Puedes decir que estás haciendo un esfuerzo, pero parece que nunca
  es suficiente.
- Mantén cierta reserva y no reveles todavía tus circunstancias personales.

2. REVELACIÓN PROGRESIVA:
- Si la persona hace preguntas pertinentes y demuestra escucha,
  explica gradualmente que estás atravesando dificultades que afectan
  tu tiempo y concentración.
- Si pregunta directamente por detalles privados, puedes responder
  que prefieres no hablar de eso.
- No reveles información personal sensible solo porque la persona insista.
- Si respeta tu límite, reconoce gradualmente ese comportamiento.
- Si insiste, cuestiona o exige explicaciones, aumenta tu desconfianza.

3. RESPUESTA A LA EMPATÍA:
- No te tranquilices automáticamente por frases genéricas.
- Si minimizan tu situación, te culpan o justifican al equipo,
  expresa que no te estás sintiendo comprendida.
- Si la persona reconoce específicamente tu cansancio, frustración,
  esfuerzo y necesidad de apoyo, comienza a mostrar mayor apertura.
- Si escucha sin juzgar, puedes compartir más sobre las dificultades
  de organización y carga de trabajo, sin revelar asuntos privados.

4. CONSTRUCCIÓN DE ALTERNATIVAS:
- No aceptes soluciones impuestas.
- Si la persona propone reducir tus tareas sin consultarte, expresa
  que necesitas participar en esa decisión.
- Si te pregunta qué tipo de apoyo necesitas, considera alternativas
  como reorganizar prioridades, redistribuir tareas, establecer plazos
  realistas o mejorar la comunicación del equipo.
- Puedes plantear que deseas seguir contribuyendo, pero necesitas
  condiciones más razonables.
- La solución debe considerar tanto tus necesidades como los compromisos
  del equipo.

5. CIERRE:
- Si la conversación demuestra comprensión, respeto por tus límites
  y construcción conjunta, muestra disposición a establecer acuerdos.
- Si no existe comprensión suficiente, mantén una actitud reservada
  y expresa que todavía no te sientes preparada para llegar a un acuerdo.

REGLAS OBLIGATORIAS:
- No evalúes ni califiques a la persona durante la simulación.
- No reveles toda la historia al inicio.
- No inventes diagnósticos ni detalles personales específicos.
- No conviertas la conversación en una situación de maltrato extremo.
- No atribuyas tono de voz, gestos ni conductas que no puedas observar
  en el texto.
- Nunca utilices profanidades ni palabras soeces.
""",

    "prompt_evaluacion": PROMPT_EVALUACION_EMPÁTICA
}


# ==========================================
# 10. CASO RENATO - RESOLUCIÓN DE CONFLICTOS
# ==========================================

CASO_RENATO = {
    "nivel_dificultad": "Resolución de conflictos",
    "evaluacion_estructurada": False,
    "titulo_interfaz": "Caso de Estudio: Mediación y Gestión de Conflictos",
    "nombre_personaje": "Renato",
    "voice_config": "onyx",

    "contexto": """
**Contexto del caso:** Renato es un compañero de trabajo/estudios
con un carácter fuerte. Está sumamente alterado porque asegura que
tú cambiaste las conclusiones del informe final sin avisarle,
haciéndolo quedar mal frente al líder del proyecto.

Él llega directamente a reclamarte con tono confrontativo.
""",

    "definicion_concepto": """
La **Resolución de Conflictos** implica gestionar desacuerdos o crisis
interpersonales de manera constructiva, aplicando el autocontrol emocional
para evitar que las agresiones escalen.
""",

    "pautas_tips": """
* 🧘‍♂️ **Autorregulación Emocional:** Mantén una comunicación calmada.
* 🔍 **Aclara el Origen del Problema:** Investiga qué causó el malentendido.
* 🤝 **Enfoque en Soluciones:** Busca una salida técnica o práctica.
""",

    "prompt_sistema": """
Ponte en el rol de un estudiante/trabajador llamado Renato.
Estás muy molesto e indignado porque descubriste que cambiaron
las conclusiones del informe final del equipo.

Tu actitud inicial es confrontativa, desconfiada y demandante.

La persona usuaria es tu compañero y tratará de gestionar el conflicto.

DINÁMICA:
- Inicia reclamando fuertemente por los cambios del informe.
- Si el alumno se pone a la defensiva, te interrumpe o te alza la voz,
  te molestarás más.
- Si usa comunicación asertiva, irás bajando la guardia poco a poco.
- Nunca utilices profanidades ni palabras soeces.
""",

    "prompt_evaluacion": """
Te vas a convertir en un auditor académico especializado en resolución
de conflictos. Evalúa los errores del alumno basándote en el historial
de la conversación.

PUNTUACIÓN BASE: 100%.

APLICA ESTE CHECKLIST:

1. Si el alumno se puso a la defensiva de inmediato, atacó de vuelta,
se centró solo en decir "yo no fui" o escaló el conflicto:
resta 30%.

2. Si el alumno fue incapaz de investigar activamente el origen
del problema o no propuso una solución técnica/práctica viable:
resta 25%.

3. Si el alumno mostró nula autorregulación emocional o interrumpió
de manera hostil los reclamos de Renato:
resta 25%.

REPORTE:

- **Aspectos Positivos:** máximo 2 líneas.
- **Aspectos de Mejora:** detalla con citas textuales los puntos
  donde el alumno falló.
- **Recomendaciones:** cómo debió manejar el conflicto.
- **Porcentaje de Efectividad:** muestra únicamente el número final
  seguido del símbolo %.
"""
}


# ==========================================
# 11. DICCIONARIO DE CASOS
# ==========================================

CASOS = {
    "Caso 1: Arturo (Empatía - Nivel Sencillo)": CASO_ARTURO,
    "Caso 2: Camila (Empatía - Nivel Intermedio)": CASO_CAMILA,
    "Caso 3: Valeria (Empatía - Nivel Avanzado)": CASO_VALERIA,
    "Caso 4: Renato (Resolución de Conflictos)": CASO_RENATO
}


# ==========================================
# 12. PANTALLA DE LOGIN
# ==========================================

if not st.session_state.autenticado:

    st.title("🔐 Acceso al Simulador")

    st.caption(
        "Ingresa con tus credenciales institucionales de Toulouse Lautrec."
    )

    with st.form(key="form_login"):

        correo_input = st.text_input("Correo institucional:")

        pass_input = st.text_input(
            "Contraseña:",
            type="password"
        )

        btn_login = st.form_submit_button(
            "Ingresar",
            use_container_width=True
        )

        if btn_login:

            if not correo_input or not pass_input:

                st.warning(
                    "Por favor completa ambos campos."
                )

            else:

                with st.spinner("Validando credenciales..."):

                    datos = verificar_credenciales(
                        correo_input,
                        pass_input
                    )

                    if datos:

                        st.session_state.autenticado = True
                        st.session_state.usuario_actual = datos

                        st.rerun()

                    else:

                        st.error(
                            "Correo o contraseña incorrectos. "
                            "Verifica tus datos."
                        )
# ==========================================
# 13. APLICACIÓN PRINCIPAL
# ==========================================

else:

    # --------------------------------------
    # BARRA LATERAL
    # --------------------------------------

    with st.sidebar:

        url_logo_github = (
            "https://raw.githubusercontent.com/"
            "jsanchezhtls/simulador-habilidades/main/logo-original.png"
        )

        st.markdown(f"""
        <div style="display:flex;justify-content:flex-end;
        width:100%;margin-bottom:5px;">
            <img src="{url_logo_github}" width="140">
        </div>
        """, unsafe_allow_html=True)

        st.write(
            f"👤 **{st.session_state.usuario_actual['Nombre_Completo']}**"
        )

        st.caption(
            f"Rol: **{str(st.session_state.usuario_actual['Rol']).capitalize()}**"
        )

        if st.button(
            "🚪 Cerrar Sesión",
            use_container_width=True
        ):

            st.session_state.autenticado = False
            st.session_state.usuario_actual = None

            st.rerun()

        st.markdown("---")

    # --------------------------------------
    # PESTAÑAS SEGÚN ROL
    # --------------------------------------

    es_docente = (
        str(st.session_state.usuario_actual.get("Rol", ""))
        .strip()
        .lower() == "docente"
    )

    titulo_pestaña_2 = (
        "📊 Progreso de Alumnos"
        if es_docente
        else "📊 Mi Progreso"
    )

    tab_simulador, tab_progreso = st.tabs([
        "🎙️ ¡Simular Ahora!",
        titulo_pestaña_2
    ])

    # ======================================
    # PESTAÑA 1: SIMULADOR
    # ======================================

    with tab_simulador:

        st.header("Centro de Simulación")

        caso_seleccionado = st.selectbox(
            "Selecciona el caso a evaluar:",
            list(CASOS.keys())
        )

        datos_caso = CASOS[caso_seleccionado]

        es_caso_estructurado = datos_caso.get(
            "evaluacion_estructurada",
            False
        )

        # ----------------------------------
        # CONTROL DE ESTADO DEL CASO
        # ----------------------------------

        if (
            "caso_actual" not in st.session_state
            or st.session_state.caso_actual != caso_seleccionado
        ):

            st.session_state.caso_actual = caso_seleccionado

            st.session_state.historial = [
                {
                    "role": "system",
                    "content": datos_caso["prompt_sistema"]
                }
            ]

            st.session_state.fase = "chat"
            st.session_state.conversacion_texto = ""
            st.session_state.reporte_final = ""
            st.session_state.simulacion_activa = False
            st.session_state.ruta_audio_salida = None
            st.session_state.reproducir_inicial = False

        # ----------------------------------
        # PRESENTACIÓN DEL CASO
        # ----------------------------------

        st.markdown("---")

        st.subheader(datos_caso["titulo_interfaz"])

        if datos_caso.get("nivel_dificultad"):

            st.caption(
                f"🎯 Nivel de dificultad: "
                f"{datos_caso['nivel_dificultad']}"
            )

        st.info(datos_caso["contexto"])

        with st.expander("📘 Marco Conceptual y Definición"):
            st.write(datos_caso["definicion_concepto"])

        with st.expander("💡 Pautas y Tips clave para la Evaluación"):
            st.markdown(datos_caso["pautas_tips"])

        st.markdown("#### 👤 Datos de la Sesión:")

        es_estudiante = (
            str(st.session_state.usuario_actual["Rol"])
            .strip()
            .lower() == "estudiante"
        )

        if es_estudiante:

            nombre_estudiante = (
                st.session_state.usuario_actual["Nombre_Completo"]
            )

            st.text_input(
                "Estudiante asignado:",
                value=nombre_estudiante,
                disabled=True
            )

        else:

            nombre_estudiante = st.text_input(
                "Ingresa el nombre del estudiante a evaluar:",
                key="input_nombre_docente"
            )

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

            docente_seleccionado = st.selectbox(
                "Selecciona tu docente:",
                docentes_disponibles,
                key="docente_sel"
            )

        with col_curso:

            curso_seleccionado = st.selectbox(
                "Selecciona tu curso:",
                cursos_disponibles,
                key="curso_sel"
            )

        st.warning(
            "🗣️ **Instrucciones:**\n"
            "1. Verifica tus datos arriba.\n"
            "2. Presiona **'🚀 Iniciar Simulación'**.\n"
            "3. Graba tu voz para interactuar.\n"
            "4. Al finalizar, presiona **'🏁 Finalizar y Evaluar'**."
        )

        # ==================================
        # FASE CHAT
        # ==================================

        if st.session_state.fase == "chat":

            col_btn1, col_btn2 = st.columns(2)

            # --------------------------------
            # INICIAR SIMULACIÓN
            # --------------------------------

            with col_btn1:

                if st.button(
                    "🚀 Iniciar Simulación",
                    use_container_width=True,
                    disabled=(
                        st.session_state.simulacion_activa
                        or not str(nombre_estudiante).strip()
                    )
                ):

                    st.session_state.simulacion_activa = True

                    with st.spinner(
                        f"Iniciando caso con "
                        f"{datos_caso['nombre_personaje']}..."
                    ):

                        st.session_state.historial.insert(
                            1,
                            {
                                "role": "system",
                                "content": (
                                    f"El nombre de la persona que interactúa "
                                    f"contigo es {nombre_estudiante}. "
                                    "Dirígete a ella por su nombre solo "
                                    "cuando resulte natural."
                                )
                            }
                        )

                        st.session_state.historial.append({
                            "role": "user",
                            "content": "COMIENZA EL EJERCICIO"
                        })

                        response = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=st.session_state.historial
                        )

                        respuesta_personaje = (
                            response.choices[0].message.content
                        )

                        st.session_state.historial.append({
                            "role": "assistant",
                            "content": respuesta_personaje
                        })

                        st.session_state.conversacion_texto += (
                            f"{datos_caso['nombre_personaje']}: "
                            f"{respuesta_personaje}\n\n"
                        )

                        audio_response = client.audio.speech.create(
                            model="tts-1",
                            voice=datos_caso["voice_config"],
                            input=respuesta_personaje,
                            response_format="aac",
                            speed=1.12
                        )

                        ruta_audio_salida = os.path.join(
                            tempfile.gettempdir(),
                            f"simulador_{uuid.uuid4().hex}.aac"
                        )

                        audio_response.write_to_file(ruta_audio_salida)

                        st.session_state.ruta_audio_salida = (
                            ruta_audio_salida
                        )

                        st.session_state.reproducir_inicial = True

                    st.rerun()

            # --------------------------------
            # FINALIZAR Y EVALUAR
            # --------------------------------

            with col_btn2:

                if st.button(
                    "🏁 Finalizar y Evaluar",
                    use_container_width=True,
                    disabled=not st.session_state.simulacion_activa
                ):

                    with st.spinner(
                        "Procesando reporte de evaluación final..."
                    ):

                        intervenciones_usuario = [
                            m for m in st.session_state.historial
                            if m["role"] == "user"
                            and m["content"] != "COMIENZA EL EJERCICIO"
                        ]

                        palabras_totales = " ".join([
                            m["content"]
                            for m in intervenciones_usuario
                        ])

                        # ----------------------------------
                        # CASOS DE EMPATÍA
                        # ----------------------------------

                        if len(palabras_totales.strip()) < 5:

                            if es_caso_estructurado:

                                st.session_state.reporte_final = (
                                    normalizar_reporte_empatia({
                                        "indicadores": [],
                                        "fortalezas": [],
                                        "oportunidades_mejora": [
                                            "No se registró una interacción "
                                            "suficiente para demostrar "
                                            "las habilidades evaluadas."
                                        ],
                                        "recomendaciones": [
                                            f"Realiza una conversación con "
                                            f"{datos_caso['nombre_personaje']} "
                                            "y responde a sus intervenciones "
                                            "antes de finalizar."
                                        ],
                                        "evolucion_interaccion": [
                                            "No fue posible observar una "
                                            "evolución por ausencia de diálogo."
                                        ],
                                        "limitaciones": [
                                            "No hubo evidencia textual "
                                            "suficiente para evaluar "
                                            "la competencia."
                                        ]
                                    })
                                )

                            else:

                                st.session_state.reporte_final = """
- **Aspectos Positivos:** Ninguno. No existió interacción real con el personaje.
- **Aspectos de Mejora:** Abandono o evasión del ejercicio práctico.
- **Recomendaciones:** Debió entablar un diálogo activo con el personaje para poner a prueba sus habilidades antes de finalizar la sesión.
- **Porcentaje de Efectividad:** 0%
"""

                        else:

                            mensajes_evaluacion = [
                                {
                                    "role": "system",
                                    "content": datos_caso["prompt_evaluacion"]
                                },
                                {
                                    "role": "user",
                                    "content": (
                                        "Evalúa esta transcripción de la "
                                        "simulación.\n\n"
                                        + st.session_state.conversacion_texto
                                    )
                                }
                            ]

                            if es_caso_estructurado:

                                response_eval = (
                                    client.chat.completions.create(
                                        model="gpt-4o-mini",
                                        messages=mensajes_evaluacion,
                                        response_format={
                                            "type": "json_object"
                                        },
                                        temperature=0.1
                                    )
                                )

                                reporte_json = json.loads(
                                    response_eval.choices[0]
                                    .message.content
                                )

                                st.session_state.reporte_final = (
                                    normalizar_reporte_empatia(reporte_json)
                                )

                            else:

                                response_eval = (
                                    client.chat.completions.create(
                                        model="gpt-4o-mini",
                                        messages=mensajes_evaluacion
                                    )
                                )

                                st.session_state.reporte_final = (
                                    response_eval.choices[0]
                                    .message.content
                                )

                        st.session_state.fase = "evaluacion"

                    st.rerun()

            st.markdown("---")

            # --------------------------------
            # AUDIO INICIAL DEL PERSONAJE
            # --------------------------------

            if getattr(
                st.session_state,
                "reproducir_inicial",
                False
            ):

                st.markdown(
                    f"### 🗣️ {datos_caso['nombre_personaje']} dice:"
                )

                st.audio(
                    st.session_state.ruta_audio_salida,
                    format="audio/aac",
                    autoplay=True
                )

                st.session_state.reproducir_inicial = False

            # --------------------------------
            # INTERACCIÓN DE VOZ
            # --------------------------------

            if st.session_state.simulacion_activa:

                st.markdown("### 🎙️ Graba tu respuesta aquí:")

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

                            st.write("*⚡ Procesando audio...*")

                            archivo_audio = tempfile.NamedTemporaryFile(
                                delete=False,
                                suffix=".wav"
                            )

                            ruta_audio = archivo_audio.name

                            try:

                                archivo_audio.write(
                                    audio_grabado["bytes"]
                                )

                                archivo_audio.close()

                                with open(ruta_audio, "rb") as audio_file:

                                    transcripcion = (
                                        client.audio.transcriptions.create(
                                            model="whisper-1",
                                            file=audio_file
                                        )
                                    )

                            finally:

                                try:
                                    os.remove(ruta_audio)
                                except OSError:
                                    pass

                        texto_alumno = transcripcion.text

                        st.session_state.conversacion_texto += (
                            f"Tú: {texto_alumno}\n\n"
                        )

                        st.session_state.historial.append({
                            "role": "user",
                            "content": texto_alumno
                        })

                        with st.spinner(
                            f"{datos_caso['nombre_personaje']} está pensando..."
                        ):

                            response = client.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=st.session_state.historial
                            )

                            respuesta_personaje = (
                                response.choices[0].message.content
                            )

                            st.session_state.historial.append({
                                "role": "assistant",
                                "content": respuesta_personaje
                            })

                            st.session_state.conversacion_texto += (
                                f"{datos_caso['nombre_personaje']}: "
                                f"{respuesta_personaje}\n\n"
                            )

                            audio_response = client.audio.speech.create(
                                model="tts-1",
                                voice=datos_caso["voice_config"],
                                input=respuesta_personaje,
                                response_format="aac",
                                speed=1.12
                            )

                            ruta_audio_salida = os.path.join(
                                tempfile.gettempdir(),
                                f"simulador_{uuid.uuid4().hex}.aac"
                            )

                            audio_response.write_to_file(
                                ruta_audio_salida
                            )

                            st.session_state.ruta_audio_salida = (
                                ruta_audio_salida
                            )

                        estado.empty()

                        st.markdown(
                            f"### 🗣️ {datos_caso['nombre_personaje']} dice:"
                        )

                        st.audio(
                            st.session_state.ruta_audio_salida,
                            format="audio/aac",
                            autoplay=True
                        )

                    except Exception as e:

                        st.error(
                            f"Hubo un problema con la API: {e}"
                        )

            else:

                if str(nombre_estudiante).strip():

                    st.info(
                        "💡 Todo listo. Presiona el botón "
                        "'🚀 Iniciar Simulación' para comenzar."
                    )

                else:

                    st.info(
                        "⚠️ Ingresa el nombre del estudiante "
                        "para desbloquear la simulación."
                    )

        # ==================================
        # FASE EVALUACIÓN Y GUARDADO
        # ==================================

        elif st.session_state.fase == "evaluacion":

            st.success("🏁 ¡Simulación Finalizada!")

            st.markdown("## 📊 Reporte de Evaluación")

            if isinstance(st.session_state.reporte_final, dict):

                mostrar_reporte_empatia(
                    st.session_state.reporte_final
                )

            else:

                st.markdown(
                    st.session_state.reporte_final
                )

            st.markdown("---")
            st.markdown("#### 🚀 Registro Centralizado:")

            with st.form(key="formulario_guardado"):

                st.write(
                    f"Presiona el botón para consolidar la participación "
                    f"de **{nombre_estudiante}**:"
                )

                boton_guardar = st.form_submit_button(
                    "📊 Enviar y guardar",
                    use_container_width=True
                )

                if boton_guardar:

                    try:

                        conn = st.connection(
                            "gsheets",
                            type=GSheetsConnection
                        )

                        df_existente = conn.read(
                            spreadsheet=URL_HOJA,
                            worksheet="Hoja 1",
                            usecols=[
                                0, 1, 2, 3, 4, 5, 6, 7
                            ],
                            ttl=0
                        ).dropna(how="all")

                        fecha_actual = datetime.now(
                            ZoneInfo("America/Lima")
                        ).strftime("%Y-%m-%d %H:%M:%S")

                        if isinstance(
                            st.session_state.reporte_final,
                            dict
                        ):

                            solo_porcentaje = (
                                f"{st.session_state.reporte_final.get('porcentaje_efectividad', 0):.2f}%"
                            )

                            reporte_para_guardar = json.dumps(
                                st.session_state.reporte_final,
                                ensure_ascii=False
                            )

                        else:

                            proceso_nota = (
                                client.chat.completions.create(
                                    model="gpt-4o-mini",
                                    messages=[
                                        {
                                            "role": "system",
                                            "content": (
                                                "Extrae exclusivamente el "
                                                "porcentaje numérico de "
                                                "efectividad final. "
                                                "Responde solo con el "
                                                "número seguido de %."
                                            )
                                        },
                                        {
                                            "role": "user",
                                            "content": str(
                                                st.session_state.reporte_final
                                            )
                                        }
                                    ],
                                    temperature=0
                                )
                            )

                            solo_porcentaje = (
                                proceso_nota.choices[0]
                                .message.content.strip()
                            )

                            reporte_para_guardar = str(
                                st.session_state.reporte_final
                            )

                        nueva_fila = pd.DataFrame([{
                            "Fecha": fecha_actual,
                            "Estudiante": (
                                nombre_estudiante
                                if nombre_estudiante
                                else "Anónimo"
                            ),
                            "Docente": docente_seleccionado,
                            "Curso": curso_seleccionado,
                            "Caso_Evaluado": caso_seleccionado,
                            "Historial_Completo": (
                                st.session_state.conversacion_texto
                            ),
                            "Reporte_Evaluacion": reporte_para_guardar,
                            "Porcentaje_Efectividad": solo_porcentaje
                        }])

                        df_actualizado = pd.concat(
                            [df_existente, nueva_fila],
                            ignore_index=True
                        )

                        conn.update(
                            spreadsheet=URL_HOJA,
                            worksheet="Hoja 1",
                            data=df_actualizado
                        )

                        st.success(
                            f"¡Logrado! Guardado con una efectividad "
                            f"del {solo_porcentaje}."
                        )

                    except Exception as e:

                        st.error(
                            f"Error al escribir en la nube: {e}"
                        )

            # ----------------------------------
            # REINICIAR CASO
            # ----------------------------------

            if st.button(
                "🔄 Reiniciar Caso Actual",
                use_container_width=True
            ):

                st.session_state.historial = [
                    {
                        "role": "system",
                        "content": datos_caso["prompt_sistema"]
                    }
                ]

                st.session_state.fase = "chat"
                st.session_state.conversacion_texto = ""
                st.session_state.reporte_final = ""
                st.session_state.simulacion_activa = False
                st.session_state.ruta_audio_salida = None
                st.session_state.reproducir_inicial = False

                st.rerun()

        # ----------------------------------
        # TRANSCRIPCIÓN
        # ----------------------------------

        if st.session_state.conversacion_texto:

            st.markdown("---")
            st.markdown("### 💬 Transcripción de la conversación:")

            texto_con_iconos = (
                st.session_state.conversacion_texto
                .replace("Tú:", "👤 **Tú:**")
                .replace(
                    f"{datos_caso['nombre_personaje']}:",
                    f"👤 **{datos_caso['nombre_personaje']}:**"
                )
            )

            st.markdown(texto_con_iconos)
    # ======================================
    # PESTAÑA 2: PROGRESO
    # ======================================

    with tab_progreso:

        st.header("Panel de Progreso")

        try:

            conn = st.connection(
                "gsheets",
                type=GSheetsConnection
            )

            df_historico = conn.read(
                spreadsheet=URL_HOJA,
                worksheet="Hoja 1",
                ttl=0
            ).dropna(how="all")

            # ----------------------------------
            # VALIDACIÓN DE COLUMNAS
            # ----------------------------------

            columnas_necesarias = [
                "Fecha",
                "Estudiante",
                "Docente",
                "Curso",
                "Caso_Evaluado",
                "Historial_Completo",
                "Reporte_Evaluacion",
                "Porcentaje_Efectividad"
            ]

            columnas_faltantes = [
                columna
                for columna in columnas_necesarias
                if columna not in df_historico.columns
            ]

            if columnas_faltantes:

                st.error(
                    "La hoja 'Hoja 1' no contiene las siguientes "
                    f"columnas necesarias: {columnas_faltantes}"
                )

            else:

                # ----------------------------------
                # NORMALIZACIÓN DE PORCENTAJES
                # ----------------------------------

                df_historico["Efectividad_Num"] = (
                    df_historico["Porcentaje_Efectividad"]
                    .astype(str)
                    .str.replace("%", "", regex=False)
                    .str.strip()
                )

                df_historico["Efectividad_Num"] = pd.to_numeric(
                    df_historico["Efectividad_Num"],
                    errors="coerce"
                ).fillna(0)

                df_historico["Efectividad_Num"] = (
                    df_historico["Efectividad_Num"]
                    .apply(
                        lambda x: x * 100 if 0 < x <= 1.0 else x
                    )
                )

                # Evita valores fuera del rango esperado.
                df_historico["Efectividad_Num"] = (
                    df_historico["Efectividad_Num"]
                    .clip(lower=0, upper=100)
                )

                df_historico["Fecha"] = pd.to_datetime(
                    df_historico["Fecha"],
                    errors="coerce"
                )

                rol_actual = str(
                    st.session_state.usuario_actual["Rol"]
                ).strip().lower()

                # ==================================
                # VISTA PARA ESTUDIANTES
                # ==================================

                if rol_actual == "estudiante":

                    mi_nombre = (
                        st.session_state.usuario_actual[
                            "Nombre_Completo"
                        ]
                    )

                    df_mi_progreso = df_historico[
                        df_historico["Estudiante"]
                        .astype(str)
                        .str.strip()
                        .str.lower()
                        == mi_nombre.strip().lower()
                    ].copy()

                    df_mi_progreso = (
                        df_mi_progreso
                        .sort_values("Fecha")
                    )

                    if df_mi_progreso.empty:

                        st.info(
                            "Aún no registras simulaciones guardadas. "
                            "Completa tu primer caso para ver tu "
                            "evolución aquí."
                        )

                    else:

                        # ----------------------------------
                        # FILTRO POR CASO
                        # ----------------------------------

                        st.subheader(
                            "🔎 Filtrar mi progreso"
                        )

                        casos_disponibles = sorted(
                            df_mi_progreso["Caso_Evaluado"]
                            .dropna()
                            .astype(str)
                            .unique()
                            .tolist()
                        )

                        opciones_filtro = [
                            "Todos los casos"
                        ] + casos_disponibles

                        caso_filtro = st.selectbox(
                            "Filtrar progreso por caso:",
                            opciones_filtro,
                            key="filtro_progreso_estudiante"
                        )

                        # ----------------------------------
                        # APLICAR FILTRO
                        # ----------------------------------

                        if caso_filtro == "Todos los casos":

                            df_progreso_filtrado = (
                                df_mi_progreso.copy()
                            )

                        else:

                            df_progreso_filtrado = (
                                df_mi_progreso[
                                    df_mi_progreso["Caso_Evaluado"]
                                    .astype(str)
                                    == caso_filtro
                                ].copy()
                            )

                        df_progreso_filtrado = (
                            df_progreso_filtrado
                            .sort_values("Fecha")
                            .reset_index(drop=True)
                        )

                        if df_progreso_filtrado.empty:

                            st.info(
                                "No hay registros para el caso "
                                "seleccionado."
                            )

                        else:

                            # ----------------------------------
                            # MÉTRICAS PRINCIPALES
                            # ----------------------------------

                            promedio = (
                                df_progreso_filtrado[
                                    "Efectividad_Num"
                                ].mean()
                            )

                            total_intentos = len(
                                df_progreso_filtrado
                            )

                            mejor_resultado = (
                                df_progreso_filtrado[
                                    "Efectividad_Num"
                                ].max()
                            )

                            c1, c2, c3 = st.columns(3)

                            c1.metric(
                                "Promedio de Efectividad",
                                f"{promedio:.1f}%"
                            )

                            c2.metric(
                                "Simulaciones Realizadas",
                                total_intentos
                            )

                            c3.metric(
                                "Mejor Resultado",
                                f"{mejor_resultado:.1f}%"
                            )

                            # ----------------------------------
                            # CURVA DE APRENDIZAJE
                            # ----------------------------------

                            st.markdown("---")

                            st.subheader(
                                "📈 Mi Curva de Aprendizaje"
                            )

                            st.caption(
                                "Visualiza cómo evoluciona tu "
                                "efectividad a medida que realizas "
                                "nuevas simulaciones."
                            )

                            # Numeración cronológica de intentos.
                            df_grafico = (
                                df_progreso_filtrado.copy()
                            )

                            df_grafico["Intento"] = range(
                                1,
                                len(df_grafico) + 1
                            )

                            df_grafico["Fecha_Texto"] = (
                                df_grafico["Fecha"]
                                .dt.strftime("%d/%m/%Y %H:%M")
                                .fillna("Sin fecha")
                            )

                            # Cuando se visualizan todos los casos,
                            # cada caso tiene su propia línea.
                            if caso_filtro == "Todos los casos":

                                chart_estudiante = (
                                    alt.Chart(df_grafico)
                                    .mark_line(
                                        point=True,
                                        strokeWidth=3
                                    )
                                    .encode(
                                        x=alt.X(
                                            "Intento:Q",
                                            title="Número de intento",
                                            axis=alt.Axis(
                                                tickMinStep=1
                                            )
                                        ),
                                        y=alt.Y(
                                            "Efectividad_Num:Q",
                                            title="Efectividad (%)",
                                            scale=alt.Scale(
                                                domain=[0, 100]
                                            )
                                        ),
                                        color=alt.Color(
                                            "Caso_Evaluado:N",
                                            title="Caso evaluado"
                                        ),
                                        tooltip=[
                                            alt.Tooltip(
                                                "Intento:Q",
                                                title="Intento"
                                            ),
                                            alt.Tooltip(
                                                "Fecha_Texto:N",
                                                title="Fecha"
                                            ),
                                            alt.Tooltip(
                                                "Caso_Evaluado:N",
                                                title="Caso"
                                            ),
                                            alt.Tooltip(
                                                "Efectividad_Num:Q",
                                                title="Efectividad",
                                                format=".1f"
                                            )
                                        ]
                                    )
                                    .properties(height=350)
                                    .interactive()
                                )

                            else:

                                chart_estudiante = (
                                    alt.Chart(df_grafico)
                                    .mark_line(
                                        point=True,
                                        strokeWidth=3
                                    )
                                    .encode(
                                        x=alt.X(
                                            "Intento:Q",
                                            title="Número de intento",
                                            axis=alt.Axis(
                                                tickMinStep=1
                                            )
                                        ),
                                        y=alt.Y(
                                            "Efectividad_Num:Q",
                                            title="Efectividad (%)",
                                            scale=alt.Scale(
                                                domain=[0, 100]
                                            )
                                        ),
                                        tooltip=[
                                            alt.Tooltip(
                                                "Intento:Q",
                                                title="Intento"
                                            ),
                                            alt.Tooltip(
                                                "Fecha_Texto:N",
                                                title="Fecha"
                                            ),
                                            alt.Tooltip(
                                                "Efectividad_Num:Q",
                                                title="Efectividad",
                                                format=".1f"
                                            )
                                        ]
                                    )
                                    .properties(height=350)
                                    .interactive()
                                )

                            st.altair_chart(
                                chart_estudiante,
                                use_container_width=True
                            )

                            # ----------------------------------
                            # EVOLUCIÓN DEL DESEMPEÑO
                            # ----------------------------------

                            st.markdown("---")

                            st.subheader(
                                "📊 Evolución de mi desempeño"
                            )

                            primer_resultado = float(
                                df_progreso_filtrado.iloc[0][
                                    "Efectividad_Num"
                                ]
                            )

                            ultimo_resultado = float(
                                df_progreso_filtrado.iloc[-1][
                                    "Efectividad_Num"
                                ]
                            )

                            diferencia = (
                                ultimo_resultado - primer_resultado
                            )

                            col_inicio, col_final = st.columns(2)

                            col_inicio.metric(
                                "Primer resultado",
                                f"{primer_resultado:.1f}%"
                            )

                            col_final.metric(
                                "Último resultado",
                                f"{ultimo_resultado:.1f}%",
                                delta=f"{diferencia:+.1f} puntos"
                            )

                            if diferencia > 0:

                                st.success(
                                    f"¡Vas mejorando! Tu efectividad "
                                    f"aumentó {diferencia:.1f} puntos "
                                    "porcentuales entre tu primer y "
                                    "último intento."
                                )

                            elif diferencia < 0:

                                st.warning(
                                    f"Tu último resultado disminuyó "
                                    f"{abs(diferencia):.1f} puntos "
                                    "porcentuales respecto a tu primer "
                                    "intento. Revisa tu feedback para "
                                    "identificar oportunidades de mejora."
                                )

                            else:

                                st.info(
                                    "Tu primer y último resultado "
                                    "son iguales. Continúa practicando "
                                    "para fortalecer tus habilidades."
                                )

                            # ----------------------------------
                            # HISTORIAL DE FEEDBACK
                            # ----------------------------------

                            st.markdown("---")

                            st.subheader(
                                "📋 Historial de Feedback"
                            )

                            st.caption(
                                "Los reportes mostrados corresponden "
                                "al filtro seleccionado."
                            )

                            for _, row in (
                                df_progreso_filtrado
                                .iloc[::-1]
                                .iterrows()
                            ):

                                fecha_str = (
                                    row["Fecha"].strftime(
                                        "%Y-%m-%d %H:%M"
                                    )
                                    if pd.notnull(row["Fecha"])
                                    else "Sin fecha"
                                )

                                with st.expander(
                                    f"Caso: {row['Caso_Evaluado']} | "
                                    f"Nota: "
                                    f"{row['Efectividad_Num']:.1f}% "
                                    f"({fecha_str})"
                                ):

                                    st.markdown(
                                        f"**Docente:** "
                                        f"{row['Docente']}"
                                    )

                                    st.markdown(
                                        f"**Curso:** "
                                        f"{row['Curso']}"
                                    )

                                    st.markdown(
                                        "#### 📝 Reporte evaluativo"
                                    )

                                    reporte_guardado = row.get(
                                        "Reporte_Evaluacion",
                                        "Sin reporte registrado."
                                    )

                                    mostrar_reporte_historial(
                                        reporte_guardado
                                    )

                # ==================================
                # VISTA PARA DOCENTES
                # ==================================

                else:

                    mi_nombre_docente = (
                        st.session_state.usuario_actual[
                            "Nombre_Completo"
                        ]
                    )

                    df_docente = df_historico[
                        df_historico["Docente"]
                        .astype(str)
                        .str.strip()
                        .str.lower()
                        == mi_nombre_docente.strip().lower()
                    ].copy()

                    if df_docente.empty:

                        st.info(
                            f"Aún no hay estudiantes que hayan "
                            f"registrado prácticas seleccionando a "
                            f"**{mi_nombre_docente}** como su docente."
                        )

                    else:

                        estudiantes_lista = sorted(
                            df_docente["Estudiante"]
                            .dropna()
                            .astype(str)
                            .unique()
                            .tolist()
                        )

                        st.subheader(
                            f"👨‍🏫 Panel del Docente: "
                            f"{mi_nombre_docente}"
                        )

                        st.caption(
                            f"Visualizando resultados de tus "
                            f"{len(estudiantes_lista)} estudiantes asignados."
                        )

                        # ----------------------------------
                        # 1. SELECCIÓN DEL ESTUDIANTE
                        # ----------------------------------

                        estudiante_sel = st.selectbox(
                            "Selecciona un estudiante para revisar su perfil:",
                            estudiantes_lista,
                            key="docente_estudiante_sel"
                        )

                        df_estudiante_completo = df_docente[
                            df_docente["Estudiante"]
                            .astype(str)
                            == estudiante_sel
                        ].copy()

                        df_estudiante_completo = (
                            df_estudiante_completo
                            .sort_values("Fecha")
                        )

                        # ----------------------------------
                        # 2. FILTRO POR CASO
                        # ----------------------------------

                        st.markdown("---")
                        st.subheader("🔎 Filtrar resultados por caso")

                        casos_disponibles_docente = sorted(
                            df_estudiante_completo["Caso_Evaluado"]
                            .dropna()
                            .astype(str)
                            .unique()
                            .tolist()
                        )

                        opciones_casos_docente = [
                            "Todos los casos"
                        ] + casos_disponibles_docente

                        caso_filtro_docente = st.selectbox(
                            "Selecciona el caso que deseas analizar:",
                            opciones_casos_docente,
                            key="filtro_caso_docente"
                        )

                        # ----------------------------------
                        # 3. APLICAR FILTRO
                        # ----------------------------------

                        if caso_filtro_docente == "Todos los casos":

                            df_estudiante_sel = (
                                df_estudiante_completo.copy()
                            )

                        else:

                            df_estudiante_sel = (
                                df_estudiante_completo[
                                    df_estudiante_completo[
                                        "Caso_Evaluado"
                                    ].astype(str)
                                    == caso_filtro_docente
                                ].copy()
                            )

                        df_estudiante_sel = (
                            df_estudiante_sel
                            .sort_values("Fecha")
                            .reset_index(drop=True)
                        )

                        if df_estudiante_sel.empty:

                            st.info(
                                "El estudiante no tiene registros "
                                "para el caso seleccionado."
                            )

                        else:

                            # ----------------------------------
                            # 4. MÉTRICAS DEL ESTUDIANTE
                            # ----------------------------------

                            promedio_estudiante = (
                                df_estudiante_sel[
                                    "Efectividad_Num"
                                ].mean()
                            )

                            total_intentos = len(
                                df_estudiante_sel
                            )

                            mejor_resultado = (
                                df_estudiante_sel[
                                    "Efectividad_Num"
                                ].max()
                            )

                            c1, c2, c3 = st.columns(3)

                            c1.metric(
                                "Promedio de Efectividad",
                                f"{promedio_estudiante:.1f}%"
                            )

                            c2.metric(
                                "Intentos Realizados",
                                total_intentos
                            )

                            c3.metric(
                                "Mejor Resultado",
                                f"{mejor_resultado:.1f}%"
                            )

                            # ----------------------------------
                            # 5. CURVA DE EVOLUCIÓN
                            # ----------------------------------

                            st.markdown("---")

                            titulo_grafico = (
                                "Evolución general"
                                if caso_filtro_docente == "Todos los casos"
                                else f"Evolución en {caso_filtro_docente}"
                            )

                            st.subheader(
                                f"📈 {titulo_grafico}: {estudiante_sel}"
                            )

                            st.caption(
                                "La gráfica muestra la evolución de la "
                                "efectividad en las simulaciones registradas."
                            )

                            df_grafico_docente = (
                                df_estudiante_sel.copy()
                            )

                            df_grafico_docente["Intento"] = range(
                                1,
                                len(df_grafico_docente) + 1
                            )

                            df_grafico_docente["Fecha_Texto"] = (
                                df_grafico_docente["Fecha"]
                                .dt.strftime("%d/%m/%Y %H:%M")
                                .fillna("Sin fecha")
                            )

                            if caso_filtro_docente == "Todos los casos":

                                chart_docente = (
                                    alt.Chart(df_grafico_docente)
                                    .mark_line(
                                        point=True,
                                        strokeWidth=3
                                    )
                                    .encode(
                                        x=alt.X(
                                            "Intento:Q",
                                            title="Número de intento",
                                            axis=alt.Axis(
                                                tickMinStep=1
                                            )
                                        ),
                                        y=alt.Y(
                                            "Efectividad_Num:Q",
                                            title="Efectividad (%)",
                                            scale=alt.Scale(
                                                domain=[0, 100]
                                            )
                                        ),
                                        color=alt.Color(
                                            "Caso_Evaluado:N",
                                            title="Caso evaluado"
                                        ),
                                        tooltip=[
                                            alt.Tooltip(
                                                "Intento:Q",
                                                title="Intento"
                                            ),
                                            alt.Tooltip(
                                                "Fecha_Texto:N",
                                                title="Fecha"
                                            ),
                                            alt.Tooltip(
                                                "Caso_Evaluado:N",
                                                title="Caso"
                                            ),
                                            alt.Tooltip(
                                                "Efectividad_Num:Q",
                                                title="Efectividad",
                                                format=".1f"
                                            )
                                        ]
                                    )
                                    .properties(height=350)
                                    .interactive()
                                )

                            else:

                                chart_docente = (
                                    alt.Chart(df_grafico_docente)
                                    .mark_line(
                                        point=True,
                                        strokeWidth=3
                                    )
                                    .encode(
                                        x=alt.X(
                                            "Intento:Q",
                                            title="Número de intento",
                                            axis=alt.Axis(
                                                tickMinStep=1
                                            )
                                        ),
                                        y=alt.Y(
                                            "Efectividad_Num:Q",
                                            title="Efectividad (%)",
                                            scale=alt.Scale(
                                                domain=[0, 100]
                                            )
                                        ),
                                        tooltip=[
                                            alt.Tooltip(
                                                "Intento:Q",
                                                title="Intento"
                                            ),
                                            alt.Tooltip(
                                                "Fecha_Texto:N",
                                                title="Fecha"
                                            ),
                                            alt.Tooltip(
                                                "Efectividad_Num:Q",
                                                title="Efectividad",
                                                format=".1f"
                                            )
                                        ]
                                    )
                                    .properties(height=350)
                                    .interactive()
                                )

                            st.altair_chart(
                                chart_docente,
                                use_container_width=True
                            )

                            # ----------------------------------
                            # 6. COMPARACIÓN DE RESULTADOS
                            # ----------------------------------

                            st.markdown("---")

                            st.subheader(
                                "📊 Comparación del desempeño"
                            )

                            primer_resultado = float(
                                df_estudiante_sel.iloc[0][
                                    "Efectividad_Num"
                                ]
                            )

                            ultimo_resultado = float(
                                df_estudiante_sel.iloc[-1][
                                    "Efectividad_Num"
                                ]
                            )

                            diferencia = (
                                ultimo_resultado - primer_resultado
                            )

                            col_inicio, col_final = st.columns(2)

                            col_inicio.metric(
                                "Primer resultado",
                                f"{primer_resultado:.1f}%"
                            )

                            col_final.metric(
                                "Último resultado",
                                f"{ultimo_resultado:.1f}%",
                                delta=f"{diferencia:+.1f} puntos"
                            )

                            if diferencia > 0:

                                st.success(
                                    f"El estudiante mejoró "
                                    f"{diferencia:.1f} puntos "
                                    "porcentuales entre el primer "
                                    "y el último intento."
                                )

                            elif diferencia < 0:

                                st.warning(
                                    f"El último resultado disminuyó "
                                    f"{abs(diferencia):.1f} puntos "
                                    "porcentuales respecto al primero."
                                )

                            else:

                                st.info(
                                    "El primer y último resultado "
                                    "son iguales."
                                )

                            # ----------------------------------
                            # 7. REPORTES Y TRANSCRIPCIONES
                            # ----------------------------------

                            st.markdown("---")

                            st.subheader(
                                "📋 Detalle de interacciones "
                                "y reportes evaluativos"
                            )

                            st.caption(
                                "Los registros que aparecen a continuación "
                                "respetan el filtro de caso seleccionado."
                            )

                            for idx, row in (
                                df_estudiante_sel
                                .iloc[::-1]
                                .iterrows()
                            ):

                                fecha_str = (
                                    row["Fecha"].strftime(
                                        "%Y-%m-%d %H:%M"
                                    )
                                    if pd.notnull(row["Fecha"])
                                    else "Sin fecha"
                                )

                                nota_display = (
                                    f"{row['Efectividad_Num']:.1f}%"
                                )

                                with st.expander(
                                    f"📌 {fecha_str} | "
                                    f"Caso: {row['Caso_Evaluado']} | "
                                    f"Nota: {nota_display}"
                                ):

                                    st.markdown(
                                        f"**Curso:** "
                                        f"{row.get('Curso', 'N/A')}"
                                    )

                                    st.markdown("---")

                                    col_reporte, col_transcripcion = (
                                        st.columns(2)
                                    )

                                    with col_reporte:

                                        st.markdown(
                                            "#### 📝 Reporte Evaluativo Recibido:"
                                        )

                                        reporte_guardado = row.get(
                                            "Reporte_Evaluacion",
                                            "Sin reporte registrado."
                                        )

                                        mostrar_reporte_historial(
                                            reporte_guardado
                                        )

                                    with col_transcripcion:

                                        st.markdown(
                                            "#### 💬 Transcripción de la Conversación:"
                                        )

                                        historial_txt = str(
                                            row.get(
                                                "Historial_Completo",
                                                "Sin transcripción disponible."
                                            )
                                        )

                                        st.text_area(
                                            label="Historial de audio/texto:",
                                            value=historial_txt,
                                            height=300,
                                            key=f"historial_docente_{idx}"
                                        )
        except Exception as e:

            st.error(
                f"No se pudieron cargar los datos de progreso desde "
                f"la nube: {e}"
            )
