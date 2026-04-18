# Paquete de evidencia de auditoría interna — Asignación de personas 2023

Este repositorio contiene los scripts y outputs de la extracción de evidencia del archivo operacional de asignación de recursos humanos correspondiente al año fiscal 2023. El objetivo es documentar, de forma trazable y no repudiable, el estado del archivo al cierre del período.

---

## Scripts

### `Pull actividad original.py`
Consulta la Drive Activity API sobre el **archivo original** ("Asignación de personas_2023") y extrae el historial de eventos de edición y acceso desde el 1 de enero de 2023 hasta el momento de ejecución. Usa autenticación OAuth de usuario.

### `Extraer Copia.py`
Sobre el **archivo copia** creado desde la UI de Drive, obtiene: metadata del archivo, metadata de sus revisiones, descarga del contenido como XLSX y cálculo del SHA256. Usa service account.

### `Pull actividad copia.py`
Consulta la Drive Activity API sobre el **archivo copia** y extrae su historial completo de actividad desde la creación. Sirve para verificar que el archivo no ha sido modificado después de generado. Usa autenticación OAuth de usuario.

---

## Configuración

### `configuracion.txt`
Contiene los IDs de los archivos de Google Drive. Se edita manualmente antes de cada ejecución:

```
FILE_ID_ORIGINAL=<ID del archivo operacional original>
FILE_ID_COPIA=<ID del archivo copia creado desde la UI>
```

---

## Credenciales

Carpeta `credenciales/` — **no versionar ni compartir**.

| Archivo | Descripción |
|---|---|
| `credentialsOauth.json` | Client ID OAuth tipo "Desktop app" (para los scripts de actividad) |
| `credencialesService.json` | Llave de service account (para `Extraer Copia.py`) |
| `token.json` | Token OAuth generado automáticamente en el primer login |

---

## Estructura de carpetas y archivos de salida

```
.
├── configuracion.txt
├── Pull actividad original.py
├── Extraer Copia.py
├── Pull actividad copia.py
├── credenciales/
│   ├── credentialsOauth.json
│   ├── credencialesService.json
│   └── token.json
├── logsArchivoOriginal/
│   ├── eventos_original_{FILE_ID}_{marca}.json      — respuesta cruda de Drive Activity API
│   └── ejecucion_original_{FILE_ID}_{marca}.json    — metadatos de la ejecución
├── extraccionArchivoCopia/
│   ├── copia_{FILE_ID}_{marca}.xlsx                 — archivo descargado
│   ├── copia_{FILE_ID}_{marca}.xlsx.sha256          — checksum SHA256
│   ├── metadata_archivo_{FILE_ID}_{marca}.json      — respuesta cruda de files.get
│   ├── metadata_revisiones_{FILE_ID}_{marca}.json   — respuesta cruda de revisions.list
│   └── ejecucion_copia_{FILE_ID}_{marca}.json       — metadatos de la ejecución
└── logsArchivoCopia/
    ├── eventos_copia_{FILE_ID}_{marca}.json         — respuesta cruda de Drive Activity API
    └── ejecucion_copia_{FILE_ID}_{marca}.json       — metadatos de la ejecución
```

Las carpetas de output deben existir antes de correr los scripts — si faltan, el script falla.

---

## Dependencias

```bash
pip install google-api-python-client google-auth google-auth-oauthlib requests
```

---

## Orden de ejecución

1. Crear la copia del archivo original desde la UI de Google Drive.
2. Pegar los IDs correspondientes en `configuracion.txt`.
3. Correr `Pull actividad original.py`.
4. Correr `Extraer Copia.py`.
5. Correr `Pull actividad copia.py`.
