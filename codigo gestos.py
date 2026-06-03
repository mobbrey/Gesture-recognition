

import cv2
import mediapipe as mp
import math
import requests
import time

# ─────────────────────────────────────────────
#  CONFIGURACIÓN DE RED
# ─────────────────────────────────────────────
ESP32_IP   = "192.168.4.1"
ESP32_PORT = 80
BASE_URL   = f"http://{ESP32_IP}:{ESP32_PORT}"
TIMEOUT    = 0.5   # segundos de espera por respuesta HTTP

# ─────────────────────────────────────────────
#  CONFIGURACIÓN MEDIAPIPE
# ─────────────────────────────────────────────
mp_hands = mp.solutions.hands
mp_draw  = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.8,
    min_tracking_confidence=0.8
)

# ─────────────────────────────────────────────
#  ESTADO GLOBAL
# ─────────────────────────────────────────────
ultimo_gesto   = None   # Evita enviar el mismo comando repetido
ultimo_envio   = 0      # Timestamp del último envío exitoso
INTERVALO_MIN  = 0.3    # Segundos mínimos entre envíos iguales


# ═════════════════════════════════════════════
#  MÓDULO 1 — CONEXIÓN WIFI / HTTP
# ═════════════════════════════════════════════

def verificar_conexion() -> bool:
    """
    Verifica que el ESP32 esté accesible antes de comenzar.
    Devuelve True si responde al ping HTTP.
    """
    try:
        r = requests.get(f"{BASE_URL}/ping", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def enviar_comando(cmd: str) -> bool:
    """
    Envía un comando HTTP GET al ESP32.
    Ejemplo: enviar_comando("STOP") → GET /cmd?action=STOP

    Devuelve True si el ESP32 respondió correctamente.
    """
    try:
        url = f"{BASE_URL}/cmd?action={cmd}"
        r = requests.get(url, timeout=TIMEOUT)
        if r.status_code == 200:
            print(f"  [ESP32] ✓ Comando '{cmd}' aceptado → {r.text.strip()}")
            return True
        else:
            print(f"  [ESP32] ✗ Respuesta inesperada: {r.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("  [ESP32] ✗ Sin conexión con el ESP32")
        return False
    except requests.exceptions.Timeout:
        print("  [ESP32] ✗ Timeout — ESP32 no respondió a tiempo")
        return False


# ═════════════════════════════════════════════
#  MÓDULO 2 — DETECCIÓN DE GESTOS
# ═════════════════════════════════════════════

def _distancia(p1, p2) -> float:
    """Distancia euclidiana 2D entre dos landmarks."""
    return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)


def _cerca(p1, p2, umbral=0.25) -> bool:
    """True si dos puntos están a menos de 'umbral' de distancia."""
    return _distancia(p1, p2) < umbral


def detectar_gesto(lm) -> str | None:
    """
    Analiza los 21 landmarks de la mano y devuelve el gesto detectado.

    Landmarks clave:
      0  = muñeca
      8  = punta índice
      12 = punta medio
      16 = punta anular
      20 = punta meñique
      6,10,14,18 = nudillos (bases de cada dedo)

    Retorna uno de: 'punio' | 'palma' | 'dedo_derecho' | 'dedo_izquierdo' | None
    """
    muneca = lm[0]

    # ── Puntas e indicadores de posición ──────────────────────
    indice_cerrado  = _cerca(lm[8],  muneca)   # índice plegado
    medio_cerrado   = _cerca(lm[12], muneca)   # medio plegado
    anular_cerrado  = _cerca(lm[16], muneca)   # anular plegado
    menique_cerrado = _cerca(lm[20], muneca)   # meñique plegado
    
    # Palma abierta: todas las puntas por encima de sus nudillos
    puntas_bases = [(8, 6), (12, 10), (16, 14), (20, 18)]
    palma_abierta = all(lm[p].y < lm[b].y for p, b in puntas_bases)

    # ── Clasificación ─────────────────────────────────────────
    if indice_cerrado and medio_cerrado and anular_cerrado and menique_cerrado:
        return "punio"                          # Todos cerrados → STOP

    if palma_abierta:
        return "palma"                          # Todos abiertos → FORWARD

    # Dedo derecho (meñique levantado, los demás cerrados)
    if not menique_cerrado and indice_cerrado and medio_cerrado and anular_cerrado:
        return "dedo_derecho"

    # Dedo izquierdo (índice levantado, los demás cerrados)
    if not indice_cerrado and medio_cerrado and anular_cerrado and menique_cerrado:
        return "dedo_izquierdo"

    return None   # Gesto no reconocido


# ═════════════════════════════════════════════
#  MÓDULO 3 — CONTROL DE MOTORES (lógica PC)
# ═════════════════════════════════════════════

# Mapa gesto → comando enviado al ESP32
GESTO_A_COMANDO = {
    "punio":          "STOP",
    "palma":          "FORWARD",
    "dedo_derecho":   "RIGHT",
    "dedo_izquierdo": "LEFT",
}

# Colores para el overlay de OpenCV (BGR)
COLOR_GESTO = {
    "punio":          (0, 0, 220),    # rojo
    "palma":          (0, 200, 0),    # verde
    "dedo_derecho":   (220, 120, 0),  # azul marino
    "dedo_izquierdo": (0, 180, 220),  # amarillo
}

ETIQUETA_GESTO = {
    "punio":          "STOP",
    "palma":          "AVANZAR",
    "dedo_derecho":   "DERECHA",
    "dedo_izquierdo": "IZQUIERDA",
}


def procesar_gesto(gesto: str | None):
    """
    Dado un gesto detectado, decide si debe enviar un comando al ESP32.
    Evita reenvíos innecesarios del mismo comando.
    """
    global ultimo_gesto, ultimo_envio

    if gesto is None:
        return

    ahora = time.time()
    cmd = GESTO_A_COMANDO.get(gesto)

    if cmd is None:
        return

    # Solo envía si el gesto cambió O pasó más del intervalo mínimo
    if gesto != ultimo_gesto or (ahora - ultimo_envio) > INTERVALO_MIN * 10:
        print(f"\n[GESTO] {gesto.upper()} → Enviando '{cmd}'")
        if enviar_comando(cmd):
            ultimo_gesto = gesto
            ultimo_envio = ahora


# ═════════════════════════════════════════════
#  MÓDULO 4 — OVERLAY VISUAL (OpenCV)
# ═════════════════════════════════════════════

def dibujar_overlay(frame, gesto: str | None, conexion_ok: bool):
    """
    Dibuja sobre el frame de cámara:
      - Estado de conexión ESP32
      - Gesto actual y acción correspondiente
      - Leyenda de controles
    """
    h, w = frame.shape[:2]

    # ── Estado de conexión ────────────────────
    estado_txt = "ESP32: CONECTADO" if conexion_ok else "ESP32: SIN CONEXION"
    estado_col = (0, 200, 0) if conexion_ok else (0, 0, 220)
    cv2.rectangle(frame, (0, 0), (280, 32), (0, 0, 0), -1)
    cv2.putText(frame, estado_txt, (8, 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, estado_col, 2)

    # ── Gesto y acción actuales ───────────────
    if gesto:
        etiqueta = ETIQUETA_GESTO.get(gesto, gesto.upper())
        color    = COLOR_GESTO.get(gesto, (255, 255, 255))
        cv2.rectangle(frame, (0, h - 60), (w, h), (20, 20, 20), -1)
        cv2.putText(frame, etiqueta, (w // 2 - 80, h - 15),
                    cv2.FONT_HERSHEY_DUPLEX, 1.4, color, 3)

    # ── Leyenda lateral ───────────────────────
    leyenda = [
        ("Punio",    "STOP"),
        ("Palma",    "AVANZAR"),
        ("Menique",  "DERECHA"),
        ("Indice",   "IZQUIERDA"),
        ("ESC",      "Salir"),
    ]
    for i, (gst, acc) in enumerate(leyenda):
        y = 55 + i * 22
        cv2.putText(frame, f"{gst}: {acc}", (w - 200, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (180, 180, 180), 1)


# ═════════════════════════════════════════════
#  BUCLE PRINCIPAL
# ═════════════════════════════════════════════

def main():
    print("=" * 55)
    print("  Robot Gesture Controller — iniciando...")
    print(f"  ESP32 objetivo: {BASE_URL}")
    print("=" * 55)

    # Intentar conectar al ESP32 (no bloquea si falla)
    print("\n[NET] Verificando conexión con ESP32...")
    conexion_ok = verificar_conexion()
    if conexion_ok:
        print("[NET] ✓ ESP32 accesible\n")
    else:
        print("[NET] ✗ ESP32 no encontrado — verifica el WiFi y reintentará en tiempo real\n")

    # Abrir cámara
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] No se pudo abrir la cámara")
        return

    ultimo_check_conexion = 0   # para reverificar la conexión periódicamente

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)  # efecto espejo

        # ── Procesar con MediaPipe ──────────────
        frame_rgb  = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        resultado  = hands.process(frame_rgb)

        gesto_actual = None

        if resultado.multi_hand_landmarks:
            for hand_landmarks in resultado.multi_hand_landmarks:
                mp_draw.draw_landmarks(
                    frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                    mp_draw.DrawingSpec(color=(80, 200, 80), thickness=2, circle_radius=4),
                    mp_draw.DrawingSpec(color=(200, 80, 80), thickness=2)
                )
                lm = hand_landmarks.landmark
                gesto_actual = detectar_gesto(lm)

        # ── Enviar comando si hay gesto válido ──
        procesar_gesto(gesto_actual)

        # ── Reverificar conexión cada 5 segundos ─
        ahora = time.time()
        if ahora - ultimo_check_conexion > 5:
            conexion_ok = verificar_conexion()
            ultimo_check_conexion = ahora

        # ── Dibujar overlay y mostrar ───────────
        dibujar_overlay(frame, gesto_actual, conexion_ok)
        cv2.imshow("Robot Gesture Controller", frame)

        if cv2.waitKey(1) & 0xFF == 27:   # ESC para salir
            break

    # ── Liberar recursos ────────────────────────
    print("\n[INFO] Deteniendo motores antes de salir...")
    enviar_comando("STOP")
    cap.release()
    cv2.destroyAllWindows()
    print("[INFO] Programa finalizado.")


if __name__ == "__main__":
    main()