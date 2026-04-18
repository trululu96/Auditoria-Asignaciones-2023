"""
Extracción de logs de actividad del archivo copia.

Propósito (auditoría interna):
    Registrar la actividad del archivo copia desde su creación. Se espera
    que el listado muestre únicamente la creación y cambios de permisos
    documentados (p.ej. compartir con la service account). Cualquier
    evento de edición sería una señal de alarma sobre la integridad del
    archivo preservado.

El script no procesa ni filtra la respuesta de Google: los eventos se
guardan tal como los devuelve la API en un archivo aparte. Los metadatos
de la ejecución quedan en un archivo separado.

Autenticación:
    OAuth de usuario. La Drive Activity API no acepta service accounts
    sin domain-wide delegation.

Requisitos:
    1. Habilitar la Drive Activity API en Google Cloud Console.
    2. Credenciales OAuth tipo "Desktop app" guardadas como
       `credenciales/credentialsOauth.json` (no versionar ni compartir).
    3. pip install google-api-python-client google-auth google-auth-oauthlib

Estructura esperada (las carpetas deben existir):
    ./credenciales/credentialsOauth.json
    ./logsArchivoCopia/
"""

import json
import os
from datetime import datetime, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

config = dict(l.split("=", 1) for l in open("configuracion.txt") if "=" in l)
FILE_ID = config["FILE_ID_COPIA"].strip()

CREDENTIALS_FILE = "credenciales/credentialsOauth.json"
TOKEN_FILE = "credenciales/token.json"
SCOPES = ["https://www.googleapis.com/auth/drive.activity.readonly"]


def obtener_credenciales():
    """Flujo OAuth: refresca token si existe, si no abre el navegador."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return creds


def main():
    """Ejecuta la consulta a Drive Activity sobre la copia y guarda el JSON crudo."""
    inicio = datetime.now(timezone.utc).isoformat()
    print(f"Inicio: {inicio}")
    print(f"Archivo: {FILE_ID}")

    service = build("driveactivity", "v2", credentials=obtener_credenciales(),
                    cache_discovery=False)

    # Consulta paginada sin filtro de tiempo: la copia es reciente, traemos
    # toda su historia de actividad.
    actividades = []
    cuerpo = {
        "itemName": f"items/{FILE_ID}",
        "pageSize": 100,
    }
    while True:
        respuesta = service.activity().query(body=cuerpo).execute()
        actividades.extend(respuesta.get("activities", []))
        print(f"  Eventos acumulados: {len(actividades)}")
        token = respuesta.get("nextPageToken")
        if not token:
            break
        cuerpo["pageToken"] = token

    fin = datetime.now(timezone.utc).isoformat()
    marca = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")

    carpeta = "logsArchivoCopia"

    # 1. Eventos crudos: tal cual los devolvió la API.
    nombre_eventos = f"eventos_copia_{FILE_ID}_{marca}.json"
    ruta_eventos = os.path.join(carpeta, nombre_eventos)
    with open(ruta_eventos, "w", encoding="utf-8") as f:
        json.dump(actividades, f, indent=2, ensure_ascii=False)

    # 2. Metadatos de la ejecución, separados.
    nombre_ejecucion = f"ejecucion_copia_{FILE_ID}_{marca}.json"
    ruta_ejecucion = os.path.join(carpeta, nombre_ejecucion)
    with open(ruta_ejecucion, "w", encoding="utf-8") as f:
        json.dump({
            "inicio_utc": inicio,
            "fin_utc": fin,
            "file_id": FILE_ID,
            "total_eventos": len(actividades),
            "archivo_eventos": nombre_eventos,
        }, f, indent=2, ensure_ascii=False)

    print(f"Fin: {fin}")
    print(f"Eventos crudos: {ruta_eventos}")
    print(f"Metadatos de ejecución: {ruta_ejecucion}")


# Ejecuta main() solo cuando el archivo se corre directamente
# (python pull_activity_copia.py). Si se importara desde otro módulo,
# las funciones quedan disponibles pero nada se ejecuta automáticamente.
if __name__ == "__main__":
    main()