# little-mail-gateway-api

API Django para centralizar el envio de correos SMTP. Recibe destinatario(s), asunto, cuerpo HTML y adjuntos; guarda cada solicitud en base de datos y un worker propio la envia respetando el orden de llegada.

## Componentes

- Django + Gunicorn para la API.
- Nginx como proxy frontal.
- Worker Django propio (`send_queued_mail`) sin Celery ni Redis.
- Hilo interno opcional dentro del proceso web para enviar la cola sin depender del worker externo.
- SQLite para desarrollo local.
- PostgreSQL para Docker/produccion.
- Configuracion SMTP desde `config.yml` o `config.json`.
- Volumenes locales bajo `./data/` para base de datos, adjuntos y static files.

## Preparacion

```powershell
Copy-Item .env.example .env
Copy-Item config.example.yml config.yml
```

Edita `.env` y `config.yml` con tus credenciales reales.

El puerto expuesto por defecto es `8184`:

```env
HTTP_PORT=8184
```

Docker crea estas carpetas locales si no existen:

```text
data/postgres/
data/media/
data/staticfiles/
```

En Linux puede ser necesario preparar permisos para el usuario no root de la app:

```bash
mkdir -p data/postgres data/media data/staticfiles
sudo chown -R 10001:10001 data/media data/staticfiles
```

PostgreSQL administra permisos propios dentro de `data/postgres`.

## Ejecutar en Docker Compose

```powershell
docker compose up --build
```

La API queda disponible en `http://localhost:8184`.

Por defecto Docker levanta el hilo interno de envio dentro del servicio `web`. El servicio `worker` queda como respaldo/manual y no arranca salvo que lo pidas:

```powershell
docker compose --profile worker up -d worker
```

Como el hilo interno vive dentro de `web`, el Compose deja Gunicorn con `--workers 1` para preservar un unico proceso enviador y mantener el orden de cola. Si queres escalar a varios procesos web, desactiva `EMAIL_GATEWAY_INLINE_WORKER_ENABLED=false` y usa un unico worker externo.

## Ejecutar local con SQLite

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DJANGO_SETTINGS_MODULE="gateway.settings.local"
python manage.py migrate
python manage.py runserver
```

En otra terminal:

```powershell
$env:DJANGO_SETTINGS_MODULE="gateway.settings.local"
python manage.py send_queued_mail
```

Para diagnosticar el worker manualmente:

```powershell
python manage.py send_queued_mail --once --verbosity 2 --traceback
python manage.py send_queued_mail --once --dry-run --verbosity 2
```

`--verbosity 2` muestra settings, base de datos, ruta del config SMTP, resumen de cola y cada job que intenta enviar. `--traceback` imprime el error completo. `--dry-run` lista los jobs elegibles sin enviarlos.

Si queres usar solamente el worker externo, desactiva `EMAIL_GATEWAY_INLINE_WORKER_ENABLED=false` y deja corriendo un unico `send_queued_mail` para conservar el orden de envio.

Si un proceso cae con un correo en `processing`, se libera automaticamente despues de `EMAIL_GATEWAY_PROCESSING_TIMEOUT_SECONDS` para volver a intentarlo.

## Worker En Docker

Procesar pendientes una sola vez:

```powershell
docker compose exec -T web python manage.py send_queued_mail --once --verbosity 2 --traceback
```

Ver pendientes sin enviar:

```powershell
docker compose exec -T web python manage.py send_queued_mail --once --dry-run --verbosity 2
```

Dejar un worker dedicado corriendo como servicio:

```powershell
docker compose --profile worker up -d worker
```

Ver logs:

```powershell
docker compose logs -f web
docker compose logs -f worker
```

## Cron Del Worker

El hilo interno suele alcanzar para esta API. Si queres un respaldo por cron, programa un `--once` cada minuto desde el host donde corre Docker. Ejemplo Linux:

```bash
crontab -e
```

Agregar:

```cron
* * * * * cd /ruta/little-mail-gateway-api && docker compose exec -T web python manage.py send_queued_mail --once --verbosity 1 >> ./data/worker-cron.log 2>&1
```

Tambien queda un ejemplo editable en `docker/worker-cron.example`.

Si preferis usar el servicio `worker` en vez del contenedor `web`:

```cron
* * * * * cd /ruta/little-mail-gateway-api && docker compose --profile worker run --rm worker python manage.py send_queued_mail --once --verbosity 1 >> ./data/worker-cron.log 2>&1
```

Usa solo una estrategia principal de envio para conservar el orden: hilo interno, worker dedicado o cron. El cron como respaldo esta bien si corre `--once`, porque toma la cola, procesa lo elegible y termina.

## Seguridad Docker

- Solo Nginx expone puerto al host: `8184:80`.
- PostgreSQL no publica puertos fuera de la red interna de Compose.
- La red `backend` es interna; solo `web`, `worker` y `db` participan. Nginx queda en `frontend` y no accede directo a PostgreSQL.
- `config.yml` se monta de solo lectura en `/app/config.yml`.
- Adjuntos, static files y datos de PostgreSQL quedan delimitados a `./data/`.
- Los contenedores `web`, `worker` y `nginx` usan `read_only`, `tmpfs` para rutas temporales, `cap_drop: [ALL]` y `no-new-privileges:true`.
- La imagen de Django corre con usuario no root `app` (`uid 10001`).
- Usa siempre `EMAIL_GATEWAY_API_KEY` con un token largo y no publiques `.env` ni `config.yml`.
- Cambia `DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD` y las credenciales SMTP antes de produccion.
- Si publicas detras de un proxy externo con TLS, agrega el dominio real a `DJANGO_ALLOWED_HOSTS` y `DJANGO_CSRF_TRUSTED_ORIGINS`.

## API

Si `EMAIL_GATEWAY_API_KEY` esta definido, enviar `Authorization: Bearer <token>` o `X-API-Key: <token>`.

### Encolar correo con JSON

```bash
curl -X POST http://localhost:8184/api/v1/emails/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer change-this-token" \
  -d '{
    "recipients": ["persona@example.com", "equipo@example.com"],
    "subject": "Prueba",
    "html_body": "<h1>Hola</h1><p>Correo de prueba.</p>"
  }'
```

### Encolar correo con adjuntos

```bash
curl -X POST http://localhost:8184/api/v1/emails/ \
  -H "Authorization: Bearer change-this-token" \
  -F 'recipients=["persona@example.com","equipo@example.com"]' \
  -F "subject=Prueba con adjunto" \
  -F "html_body=<h1>Hola</h1><p>Con archivo.</p>" \
  -F "attachments=@./archivo.pdf"
```

### Consultar estado

```bash
curl -H "Authorization: Bearer change-this-token" \
  http://localhost:8184/api/v1/emails/<uuid>/
```

Estados posibles: `pending`, `processing`, `sent`, `failed`.

Los correos `failed` no se descartan: el worker los vuelve a tomar automaticamente cuando llega su `next_attempt_at`. El estado `failed` indica que el ultimo intento fallo y que el correo esta esperando el proximo reintento.
