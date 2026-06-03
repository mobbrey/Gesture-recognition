Gesture recognition
Proyecto G.R
Este repositorio contiene el código fuente del proyecto , cuyo objetivo es el CONTROL DE MOTORES a través de la identificación de gestos manuales mediante visión artificial.

NOTA IMPORTANTE SOBRE LA VERSIÓN DE PYTHON
El proyecto DEBE ejecutarse utilizando Python 3.10.x, ya que existen incompatibilidades y excepciones en librerías críticas (como MediaPipe) cuando se utiliza una versión diferente (3.11+ o 3.9-). El branch main está validado únicamente para esta versión de Python.

REQUISITOS DEL SISTEMA
Lenguaje: Python 3.10 (Obligatorio)
Librerías: OpenCV, MediaPipe, NumPy
Hardware: Cámara web y archivo de video gato.mp4 en el directorio raíz.
INSTALACIÓN Y CONFIGURACIÓN (BASH)
Sigue estos pasos para preparar tu entorno de ejecución:


1. Crear y activar entorno virtual
Es altamente recomendable usar un entorno virtual para evitar conflictos con otras librerías de Python:

python -m venv .venv
# En Windows:
.venv\Scripts\activate
# En macOS/Linux:
source .venv/bin/activate
3. Instalar las dependencias
Asegúrate de tener pip actualizado y luego instala las librerías necesarias:

python -m pip install --upgrade pip
pip install -r requirements.txt
EJECUCIÓN DEL PROYECTO
Con el entorno configurado y las dependencias instaladas, ya puedes ejecutar el proyecto.

1. Asegúrate de tener conectada tu cámara web y que el archivo de video gato.mp4 esté en la misma carpeta que el script.
2. Ejecuta el script principal
