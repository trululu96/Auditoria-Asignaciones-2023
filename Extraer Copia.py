"""
Extracción del archivo copia: metadata, revisión, descarga XLSX y hash.

Propósito (auditoría interna):
    Una vez creada la copia del archivo original vía la opción "Make a copy"
    de la UI de Google Drive, este script materializa la evidencia: obtiene
    la metadata del archivo copia, la metadata de su única revisión,
    descarga el contenido como XLSX y calcula su SHA256.

El script no procesa ni filtra las respuestas de la API: las guarda tal
como las devuelve Google. Los metadatos de ejecución quedan en un archivo
separado.

Autenticación:
    Service account. El archivo copia debe compartirse con la service
    account como Viewer antes de ejecutar el script.

Requisitos:
    1. Habilitar la Drive API en Google Cloud Console.
    2. Guardar la llave de la service account como
       `credenciales/credencialesService.json` (no versionar ni compartir).
    3. pip install google-api-python-client google-auth requests

Estructura esperada (las carpetas deben existir):
    ./credenciales/credencialesService.json
    ./extraccionArchivoCopia/
"""

import hashlib
import json
import os
from datetime import datetime, timezone

import requests
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build

config = dict(l.split("=", 1) for l in open("configuracion.txt") if "=" in l)
FILE_ID = config["FILE_ID_COPIA"].strip()

CREDENTIALS_FILE = "credenciales/credencialesService.json"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def obtener_credenciales():
    """Credenciales de service account con scope de solo lectura."""
    return service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE, scopes=SCOPES
    )


def main():
    """Obtiene metadata, descarga el XLSX de la copia y calcula su SHA256."""
    inicio = datetime.now(timezone.utc).isoformat()
    print(f"Inicio: {inicio}")
    print(f"Archivo: {FILE_ID}")

    creds = obtener_credenciales()
    service = build("drive", "v3", credentials=creds, cache_discovery=False)

    # 1. Metadata del archivo copia. Pedimos exportLinks porque es el
    # camino que evita el límite de 10 MB que tiene files.export.
    file_meta = service.files().get(
        fileId=FILE_ID,
        fields="id, name, mimeType, createdTime, modifiedTime, owners, lastModifyingUser, exportLinks",
    ).execute()

    # 2. Metadata de las revisiones del archivo. Puede venir vacío si el
    # archivo no ha sido editado después de su creación. Guardamos la
    # respuesta tal cual — un array vacío también es evidencia válida de
    # que no ha habido ediciones.
    revisiones = service.revisions().list(
        fileId=FILE_ID,
        fields="revisions(id, modifiedTime, mimeType, lastModifyingUser, exportLinks, published)",
    ).execute().get("revisions", [])

    # 3. Descargar el archivo actual como XLSX usando el exportLink
    # de files.get. Este camino no tiene el límite de 10 MB de files.export.
    export_url = file_meta["exportLinks"][XLSX_MIME]
    creds.refresh(Request())
    headers = {"Authorization": f"Bearer {creds.token}"}

    marca = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    carpeta = "extraccionArchivoCopia"
    nombre_xlsx = f"copia_{FILE_ID}_{marca}.xlsx"
    ruta_xlsx = os.path.join(carpeta, nombre_xlsx)

    with requests.get(export_url, headers=headers, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        with open(ruta_xlsx, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

    # 4. SHA256 del XLSX descargado.
    h = hashlib.sha256()
    with open(ruta_xlsx, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    sha256 = h.hexdigest()

    nombre_sha = f"{nombre_xlsx}.sha256"
    ruta_sha = os.path.join(carpeta, nombre_sha)
    with open(ruta_sha, "w") as f:
        f.write(f"{sha256}  {nombre_xlsx}\n")

    # 5. Metadata cruda de Google: un archivo por tipo, sin envoltorio.
    nombre_meta_archivo = f"metadata_archivo_{FILE_ID}_{marca}.json"
    with open(os.path.join(carpeta, nombre_meta_archivo), "w", encoding="utf-8") as f:
        json.dump(file_meta, f, indent=2, ensure_ascii=False)

    nombre_meta_revisiones = f"metadata_revisiones_{FILE_ID}_{marca}.json"
    with open(os.path.join(carpeta, nombre_meta_revisiones), "w", encoding="utf-8") as f:
        json.dump(revisiones, f, indent=2, ensure_ascii=False)

    # 6. Metadatos de la ejecución, separados.
    fin = datetime.now(timezone.utc).isoformat()
    nombre_ejecucion = f"ejecucion_copia_{FILE_ID}_{marca}.json"
    with open(os.path.join(carpeta, nombre_ejecucion), "w", encoding="utf-8") as f:
        json.dump({
            "inicio_utc": inicio,
            "fin_utc": fin,
            "file_id": FILE_ID,
            "total_revisiones": len(revisiones),
            "archivo_xlsx": nombre_xlsx,
            "archivo_sha256": nombre_sha,
            "archivo_metadata": nombre_meta_archivo,
            "archivo_revisiones": nombre_meta_revisiones,
            "sha256": sha256,
        }, f, indent=2, ensure_ascii=False)

    print(f"Fin: {fin}")
    print(f"XLSX: {ruta_xlsx}")
    print(f"SHA256: {sha256}")


# Ejecuta main() solo cuando el archivo se corre directamente
# (python extract_copia.py). Si se importara desde otro módulo,
# las funciones quedan disponibles pero nada se ejecuta automáticamente.
if __name__ == "__main__":
    main()