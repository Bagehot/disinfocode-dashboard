"""Etiquetas descriptivas para cada código SLI."""

SLI_LABELS = {
    # ── Publicidad ─────────────────────────────────────────────────────────────
    "1.1.1":  "Anuncios eliminados · Contenido político",
    "1.1.2":  "Valor (€) de anuncios desmonetizados",
    "1.2.1":  "Anuncios eliminados · Fuentes de desinformación",
    "1.6.1":  "% anuncios con herramientas de brand safety",
    "2.1.1":  "Anuncios eliminados · Política de desinformación",
    "2.3.1":  "Anuncios eliminados e impresiones · Desinformación",
    "2.4.1":  "Apelaciones de anuncios eliminados · Desinformación",

    # ── Integridad del servicio ────────────────────────────────────────────────
    "14.2.1": "Canales / vídeos eliminados por comportamiento inauténtico (CIB)",
    "14.2.2": "Seguidores de cuentas falsas identificadas",
    "14.2.3": "Vídeos etiquetados como generados por IA (label 'Creator')",
    "14.2.4": "Cuentas falsas eliminadas y ratio sobre usuarios activos",
    "16.1.1": "Respuesta a crisis y elecciones (notificaciones RRS)",

    # ── Empoderamiento de usuarios ─────────────────────────────────────────────
    "17.1.1": "Impresiones de etiquetas de medios afines al Estado",
    "17.2.1": "Impresiones de paneles informativos (páginas H5)",
    "18.1.1": "Tasa de cancelación tras etiqueta 'contenido no verificado' (%)",
    "18.2.1": "Vídeos eliminados por violación de política de desinformación",
    "19.2.1": "Usuarios que filtraron hashtags o palabras clave",
    "21.1.1": "% de eliminaciones de vídeo por política de desinformación",
    "21.1.2": "Vídeos con etiqueta 'contenido no verificado'",
    "22.7.1": "Impresiones de paneles informativos (excl. paneles de fact-check)",
    "24.1.1": "Apelaciones de vídeos eliminados por desinformación",

    # ── Empoderamiento de investigadores ──────────────────────────────────────
    "26.1.1": "Solicitudes recibidas para la API de investigación",
    "26.2.1": "Solicitudes aprobadas para la API de investigación",
    "27.3.1": "Proyectos de investigación con acceso a datos",

    # ── Empoderamiento de verificadores (fact-checkers) ───────────────────────
    "30.1.1": "Acuerdos con organizaciones de fact-checking",
    "31.1.1": "Contenido tratado con fact-checks (visto en Facebook)",
    "31.1.2": "Contenido tratado con fact-checks · Denominador",
    "31.1.3": "Contenido tratado con fact-checks · Denominador (baseline)",
    "31.2.1": "Vídeos sometidos a fact-checking",
    "31.2.2": "Vídeos eliminados tras evaluación de fact-checking",
    "31.2.3": "% vídeos eliminados tras evaluación de fact-checking",
    "32.1.1": "Datos sobre cobertura de fact-checkers",

    # ── Centro de Transparencia ────────────────────────────────────────────────
    "36.1.1": "Datos enviados al Centro de Transparencia",
}


def label(sli_code: str, sli_name: str = "") -> str:
    """Devuelve etiqueta descriptiva; si no existe, retorna sli_name."""
    return SLI_LABELS.get(str(sli_code), sli_name or sli_code)
