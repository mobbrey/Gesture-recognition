import network
import socket
from machine import Pin
import time
 
# ─────────────────────────────────────────────
#  CONFIGURACIÓN DE PINES — MOTORES
# ─────────────────────────────────────────────
 
# Motor derecho (IN1, IN2)
motor_d_in1 = Pin(22, Pin.OUT)
motor_d_in2 = Pin(23, Pin.OUT)
 
# Motor izquierdo (IN3, IN4)
motor_i_in3 = Pin(19, Pin.OUT)
motor_i_in4 = Pin(21, Pin.OUT)
 
# LED de estado (onboard)
led = Pin(2, Pin.OUT)
led.off()
 
 
# ═════════════════════════════════════════════
#  MÓDULO 1 — CONTROL DE MOTORES
# ═════════════════════════════════════════════
 
def motor_derecho_on():
    motor_d_in1.off()
    motor_d_in2.on()
 
def motor_derecho_off():
    motor_d_in1.off()
    motor_d_in2.off()
 
def motor_izquierdo_on():
    motor_i_in3.off()
    motor_i_in4.on()
 
def motor_izquierdo_off():
    motor_i_in3.off()
    motor_i_in4.off()

def atras():
    motor_d_in1.on()
    motor_i_in3.on()
 
def cmd_stop():
    motor_derecho_off()
    motor_izquierdo_off()
    led.off()
    print("[MOTOR] STOP")
 
def cmd_forward():
    motor_derecho_on()
    motor_izquierdo_on()
    led.on()
    print("[MOTOR] FORWARD")
 
def cmd_right():
    motor_derecho_on()
    motor_izquierdo_off()
    led.on()
    print("[MOTOR] RIGHT")
 
def cmd_left():
    motor_derecho_off()
    motor_izquierdo_on()
    led.on()
    print("[MOTOR] LEFT")
def cmd_backward():
    atras_on()
    led.on()
    print("atras")
    
    
 
ACCIONES = {
    "STOP":    cmd_stop,
    "FORWARD": cmd_forward,
    "RIGHT":   cmd_right,
    "LEFT":    cmd_left,
     
}
 
 
# ═════════════════════════════════════════════
#  MÓDULO 2 — ACCESS POINT WIFI
# ═════════════════════════════════════════════
 
def iniciar_ap(ssid, password):
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=ssid, password=password)
 
    timeout = 10
    while not ap.active() and timeout > 0:
        time.sleep(0.5)
        timeout -= 1
 
    ip = ap.ifconfig()[0]
    print("========================================")
    print("  Access Point activo!")
    print("  SSID    : " + ssid)
    print("  Password: " + password)
    print("  IP      : " + ip)
    print("========================================")
    return ip
 
 
# ═════════════════════════════════════════════
#  MÓDULO 3 — SERVIDOR HTTP
# ═════════════════════════════════════════════
 
def parsear_accion(request_str):
    """Extrae el valor de ?action=XXX de la petición HTTP."""
    try:
        linea = request_str.split("\r\n")[0]
        if "action=" in linea:
            parte  = linea.split("action=")[1]
            accion = parte.split(" ")[0].split("&")[0].strip().upper()
            return accion
    except Exception:
        pass
    return None
 
 
def responder(conn, status, body):
    """Envía respuesta HTTP con cabeceras CORS y cierra la conexión."""
    resp = (
        "HTTP/1.1 " + status + "\r\n"
        "Content-Type: text/plain\r\n"
        "Connection: close\r\n"
        "Access-Control-Allow-Origin: *\r\n"
        "Access-Control-Allow-Methods: GET, OPTIONS\r\n"
        "Access-Control-Allow-Headers: *\r\n"
        "Content-Length: " + str(len(body)) + "\r\n"
        "\r\n" +
        body
    )
    conn.send(resp)
    conn.close()
 
 
def iniciar_servidor(puerto):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", puerto))
    s.listen(5)
    print("[HTTP] Servidor escuchando en puerto " + str(puerto) + "...")
    return s
 
 
def manejar_cliente(conn, addr):
    try:
        request = conn.recv(512).decode("utf-8", "ignore")
        linea   = request.split("\r\n")[0] if request else ""
        print("[HTTP] " + str(addr[0]) + " -> " + linea)

        # Preflight CORS (OPTIONS)
        if linea.startswith("OPTIONS"):
            responder(conn, "204 No Content", "")
            return

        if "/ping" in linea:
            responder(conn, "200 OK", "pong")
            return

        if "/cmd" in linea:
            accion = parsear_accion(request)
            if accion and accion in ACCIONES:
                ACCIONES[accion]()
                responder(conn, "200 OK", "OK:" + accion)
            else:
                responder(conn, "400 Bad Request", "Accion desconocida")
            return

        responder(conn, "404 Not Found", "Ruta no encontrada")

    except Exception as e:
        print("[ERROR] " + str(e))
        try:
            conn.close()
        except Exception:
            pass
 
 
# ═════════════════════════════════════════════
#  PROGRAMA PRINCIPAL
# ═════════════════════════════════════════════
 
def main():
    cmd_stop()
    iniciar_ap("RobotESP32", "12345678")
    servidor = iniciar_servidor(80)
    print("[INFO] Esperando comandos...\n")
 
    while True:
        try:
            conn, addr = servidor.accept()
            manejar_cliente(conn, addr)
        except OSError as e:
            print("[WARN] " + str(e))
            time.sleep(0.1)
        except Exception as e:
            print("[ERROR] " + str(e))
            time.sleep(0.1)
 
main()