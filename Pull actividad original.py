"""
Extracción de logs de actividad del archivo operacional original.

Propósito (auditoría interna):
    Generar un registro crudo de actividad del archivo operacional de
    asignación de recursos humanos. La información se usa para documentar
    patrones de uso histórico como parte de las buenas prácticas de
    trazabilidad de procesos internos.

El script no procesa ni filtra la respuesta de Google: los eventos se
guardan tal como los devuelve la API en un archivo aparte. Los metadatos
de la ejecución (inicio, fin, ventana) quedan en un archivo separado
para no alterar la respuesta original.

Autenticación:
    OAuth de usuario. La Drive Activity API no acepta service accounts sin
    domain-wide delegation.

Requisitos:
    1. Habilitar la Drive Activity API en Google Cloud Console.
    2. Crear credenciales OAuth tipo "Desktop app" y guardarlas como
       `credenciales/credentialsOauth.json` (no versionar ni compartir).
    3. pip install google-api-python-client google-auth google-auth-oauthlib
"""

import json
import os
from datetime import datetime, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

config = dict(l.split("=", 1) for l in open("configuracion.txt") if "=" in l)
FILE_ID = config["FILE_ID_ORIGINAL"].strip()

CREDENTIALS_FILE = "credenciales/credentialsOauth.json"
TOKEN_FILE = "credenciales/token.json"
SCOPES = ["https://www.googleapis.com/auth/drive.activity.readonly"]

# Ventana: desde inicio de 2023 hasta el momento de ejecución.
START = "2023-01-01T00:00:00Z"
END = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
    """Ejecuta la consulta paginada a Drive Activity y guarda el JSON crudo."""
    inicio = datetime.now(timezone.utc).isoformat()
    print(f"Inicio: {inicio}")
    print(f"Archivo: {FILE_ID}")
    print(f"Ventana: {START} -> {END}")

    service = build("driveactivity", "v2", credentials=obtener_credenciales(),
                    cache_discovery=False)

    # Consulta paginada. No se procesa ni filtra: se acumulan los eventos
    # tal como los devuelve la API.
    actividades = []
    cuerpo = {
        "itemName": f"items/{FILE_ID}",
        "filter": f'time >= "{START}" AND time < "{END}"',
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

    # Subcarpeta dedicada para los logs. Debe existir previamente.
    carpeta = "logsArchivoOriginal"

    # 1. Eventos crudos: tal cual los devolvió la API, sin envoltorio.
    nombre_eventos = f"eventos_original_{FILE_ID}_{marca}.json"
    ruta_eventos = os.path.join(carpeta, nombre_eventos)
    with open(ruta_eventos, "w", encoding="utf-8") as f:
        json.dump(actividades, f, indent=2, ensure_ascii=False)

    # Resumen de eventos anteriores o iguales al 11 de enero de 2024
    # (fecha de cierre del FY2023). Cuenta eventos hasta ese día inclusive.
    CIERRE_FY2023 = "2024-01-11"
    eventos_hasta_cierre = sum(
        1 for a in actividades
        if (a.get("timestamp") or a.get("timeRange", {}).get("startTime", ""))[:10] <= CIERRE_FY2023
    )

    # 2. Metadatos de la ejecución: separados, para no alterar los eventos.
    nombre_ejecucion = f"ejecucion_original_{FILE_ID}_{marca}.json"
    ruta_ejecucion = os.path.join(carpeta, nombre_ejecucion)
    with open(ruta_ejecucion, "w", encoding="utf-8") as f:
        json.dump({
            "inicio_utc": inicio,
            "fin_utc": fin,
            "file_id": FILE_ID,
            "ventana_inicio": START,
            "ventana_fin": END,
            "total_eventos": len(actividades),
            "eventos_hasta_cierre_fy2023": eventos_hasta_cierre,
            "fecha_cierre_fy2023": CIERRE_FY2023,
            "archivo_eventos": nombre_eventos,
        }, f, indent=2, ensure_ascii=False)

    print(f"Fin: {fin}")
    print(f"Eventos crudos: {ruta_eventos}")
    print(f"Metadatos de ejecución: {ruta_ejecucion}")


# Ejecuta main() solo cuando el archivo se corre directamente
# (python pull_activity_original.py). Si se importara desde otro módulo,
# las funciones quedan disponibles pero nada se ejecuta automáticamente.
if __name__ == "__main__":
    main()