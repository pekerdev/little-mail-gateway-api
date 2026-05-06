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
NGINX_SERVER_NAME=_
NGINX_TEMPLATE_FILE=./nginx/templates/http.conf.template
NGINX_CONTAINER_PORT=8080
NGINX_HEALTHCHECK_URL=http://127.0.0.1:8080/health/
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

El Compose incluye un servicio corto `setup-permissions` que prepara permisos de `data/media` y `data/staticfiles` para el usuario no root de Django (`uid 10001`). Si venis de una version anterior y ya existen archivos con otro propietario, recrea con:

```bash
docker compose down
docker compose up --build -d setup-permissions
docker compose up --build -d
```

## Configuracion `.env`

El archivo `.env` controla Django, Docker, PostgreSQL y el comportamiento del procesador de cola. Para empezar:

```powershell
Copy-Item .env.example .env
```

Ejemplo recomendado para Docker:

```env
DJANGO_SECRET_KEY=generar-una-clave-larga-y-secreta
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,web,mail-api.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://mail-api.example.com
EMAIL_GATEWAY_API_KEY=token-largo-para-los-clientes
EMAIL_GATEWAY_CONFIG=/app/config.yml
EMAIL_GATEWAY_INLINE_WORKER_ENABLED=true
EMAIL_GATEWAY_INLINE_WORKER_START_DELAY_SECONDS=1
EMAIL_GATEWAY_WORKER_SLEEP_SECONDS=2
EMAIL_GATEWAY_BATCH_SIZE=10
EMAIL_GATEWAY_PROCESSING_TIMEOUT_SECONDS=600
POSTGRES_DB=mail_gateway
POSTGRES_USER=mail_gateway
POSTGRES_PASSWORD=password-largo-de-postgres
HTTP_PORT=8184
```

Detalle de cada variable:

| Variable | Descripcion | Ejemplo |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | Clave interna de Django. Debe ser larga, privada y distinta por ambiente. | `DJANGO_SECRET_KEY=...` |
| `DJANGO_ALLOWED_HOSTS` | Hosts desde donde Django acepta requests. Separar por comas. Incluir `web` para pruebas internas de Compose y la IP/dominio real para acceso externo. | `localhost,127.0.0.1,web,mail-api.example.com` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Origenes HTTPS confiables si publicas detras de dominio/proxy. Separar por comas. | `https://mail-api.example.com` |
| `EMAIL_GATEWAY_API_KEY` | Token que deben mandar los clientes. Si queda vacio, la API queda sin autenticacion. | `Authorization: Bearer token-largo` |
| `EMAIL_GATEWAY_CONFIG` | Ruta del archivo SMTP dentro del contenedor. En Docker debe ser `/app/config.yml`. | `/app/config.yml` |
| `EMAIL_GATEWAY_INLINE_WORKER_ENABLED` | Activa el hilo interno que envia la cola desde el servicio `web`. | `true` |
| `EMAIL_GATEWAY_INLINE_WORKER_START_DELAY_SECONDS` | Espera inicial antes de arrancar el hilo interno. | `1` |
| `EMAIL_GATEWAY_WORKER_SLEEP_SECONDS` | Segundos de espera cuando no hay correos elegibles. | `2` |
| `EMAIL_GATEWAY_BATCH_SIZE` | Cantidad maxima de correos procesados por vuelta. | `10` |
| `EMAIL_GATEWAY_PROCESSING_TIMEOUT_SECONDS` | Libera correos trabados en `processing` despues de este tiempo. | `600` |
| `POSTGRES_DB` | Nombre de la base PostgreSQL usada en Docker. | `mail_gateway` |
| `POSTGRES_USER` | Usuario PostgreSQL. | `mail_gateway` |
| `POSTGRES_PASSWORD` | Password PostgreSQL. Cambiar siempre en produccion. | `password-largo` |
| `HTTP_PORT` | Puerto expuesto en el host para Nginx. | `8184` |
| `NGINX_SERVER_NAME` | Dominio o IP que Nginx acepta en `server_name`. Usar `_` para catch-all. | `_` o `mail-api.example.com` |
| `NGINX_TEMPLATE_FILE` | Template Nginx a usar. HTTP por defecto, SSL opcional. | `./nginx/templates/http.conf.template` |
| `NGINX_CONTAINER_PORT` | Puerto interno donde escucha Nginx. HTTP usa `8080`, SSL usa `8443`. | `8080` |
| `NGINX_HEALTHCHECK_URL` | URL interna para healthcheck de Nginx. | `http://127.0.0.1:8080/health/` |

El Compose limita `envsubst` a variables `NGINX_*`, para no reemplazar variables internas de Nginx como `$host` o `$proxy_add_x_forwarded_for`.

Notas:

- En desarrollo local con SQLite, `EMAIL_GATEWAY_CONFIG` puede omitirse y Django busca `config.yml` en la raiz del proyecto.
- En Docker, `config.yml` se monta en `/app/config.yml`, por eso `EMAIL_GATEWAY_CONFIG=/app/config.yml`.
- En Docker conviene mantener `web` dentro de `DJANGO_ALLOWED_HOSTS` para diagnosticar desde la red interna de Compose.
- Si usas varios procesos Gunicorn, desactiva el hilo interno y usa un unico worker externo para preservar el orden de envio.

## Configuracion `config.yml`

El archivo `config.yml` contiene solo la configuracion SMTP. Para empezar:

```powershell
Copy-Item config.example.yml config.yml
```

Formato completo:

```yaml
smtp:
  host: smtp.example.com
  port: 587
  username: notifications@example.com
  password: password-o-app-password
  from_email: notifications@example.com
  from_name: Little Mail Gateway
  use_tls: true
  use_ssl: false
  timeout: 30
```

Detalle de cada campo:

| Campo | Descripcion | Requerido |
| --- | --- | --- |
| `host` | Servidor SMTP real. No dejar `smtp.example.com`. | Si |
| `port` | Puerto SMTP. Normalmente `587` con TLS o `465` con SSL. | No, default `587` |
| `username` | Usuario SMTP. Suele ser el correo completo. | Depende del proveedor |
| `password` | Password SMTP o app password. | Depende del proveedor |
| `from_email` | Correo remitente visible. | Si |
| `from_name` | Nombre visible del remitente. | No |
| `use_tls` | Usa STARTTLS, comunmente con puerto `587`. | No, default `true` |
| `use_ssl` | Usa SSL directo, comunmente con puerto `465`. No usar junto con `use_tls`. | No, default `false` |
| `timeout` | Timeout de conexion SMTP en segundos. | No, default `30` |

Ejemplo con puerto 587:

```yaml
smtp:
  host: smtp.tu-proveedor.com
  port: 587
  username: robotinfra@example.com
  password: app-password
  from_email: robotinfra@example.com
  from_name: Robot Infra
  use_tls: true
  use_ssl: false
  timeout: 30
```

Ejemplo con puerto 465:

```yaml
smtp:
  host: smtp.tu-proveedor.com
  port: 465
  username: robotinfra@example.com
  password: app-password
  from_email: robotinfra@example.com
  from_name: Robot Infra
  use_tls: false
  use_ssl: true
  timeout: 30
```

Tambien se puede usar `config.json` si cambias `EMAIL_GATEWAY_CONFIG` a esa ruta:

```json
{
  "smtp": {
    "host": "smtp.tu-proveedor.com",
    "port": 587,
    "username": "robotinfra@example.com",
    "password": "app-password",
    "from_email": "robotinfra@example.com",
    "from_name": "Robot Infra",
    "use_tls": true,
    "use_ssl": false,
    "timeout": 30
  }
}
```

Errores comunes:

- `[Errno 11001] getaddrinfo failed`: el `host` SMTP no existe, no resuelve DNS o sigue siendo `smtp.example.com`.
- `SMTP config file not found`: `EMAIL_GATEWAY_CONFIG` apunta a una ruta incorrecta o no se monto `config.yml`.
- Error de autenticacion SMTP: revisar `username`, `password`, app password, permisos SMTP y politicas del proveedor.
- Timeout: revisar puerto, firewall, bloqueo de salida SMTP o si corresponde `use_tls`/`use_ssl`.

## Ejecutar en Docker Compose

```powershell
docker compose up --build
```

La API queda disponible en `http://localhost:8184`.

Mapa de puertos en Docker:

```text
HTTP:  Host 8184 -> contenedor nginx 8080 -> contenedor web 8000 -> Django
HTTPS: Host 8184 -> contenedor nginx 8443 -> contenedor web 8000 -> Django
```

Por eso `nginx/default.conf` debe tener:

```nginx
listen 8080;
```

Y `docker-compose.yml` debe publicar:

```yaml
ports:
  - "0.0.0.0:${HTTP_PORT:-8184}:${NGINX_CONTAINER_PORT:-8080}"
```

Por defecto Docker levanta el hilo interno de envio dentro del servicio `web`. El servicio `worker` queda como respaldo/manual y no arranca salvo que lo pidas:

```powershell
docker compose --profile worker up -d worker
```

Como el hilo interno vive dentro de `web`, el Compose deja Gunicorn con `--workers 1` para preservar un unico proceso enviador y mantener el orden de cola. Si queres escalar a varios procesos web, desactiva `EMAIL_GATEWAY_INLINE_WORKER_ENABLED=false` y usa un unico worker externo.

## SSL Opcional En Nginx

Por defecto el stack usa HTTP en el puerto externo `8184`. Si ya tenes certificado y key probados, colocalos asi:

```text
certs/server.crt
certs/server.key
```

`certs/` esta ignorado por git para no versionar secretos.

Para activar HTTPS en el mismo puerto externo `8184`, cambia estas variables en `.env`:

```env
HTTP_PORT=8184
NGINX_SERVER_NAME=mail-api.example.com
NGINX_TEMPLATE_FILE=./nginx/templates/ssl.conf.template
NGINX_CONTAINER_PORT=8443
NGINX_HEALTHCHECK_URL=https://127.0.0.1:8443/health/
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,web,mail-api.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://mail-api.example.com:8184
```

Si vas a entrar por IP en vez de dominio:

```env
NGINX_SERVER_NAME=_
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,web,129.148.40.98
DJANGO_CSRF_TRUSTED_ORIGINS=https://129.148.40.98:8184
```

Recrear Nginx:

```bash
docker compose rm -sf nginx
docker compose up -d nginx
```

Probar HTTPS:

```bash
docker compose exec nginx wget --no-check-certificate -S -O - https://127.0.0.1:8443/health/
curl -vk https://127.0.0.1:8184/health/
curl -vk https://mail-api.example.com:8184/health/
```

Para volver a HTTP:

```env
NGINX_SERVER_NAME=_
NGINX_TEMPLATE_FILE=./nginx/templates/http.conf.template
NGINX_CONTAINER_PORT=8080
NGINX_HEALTHCHECK_URL=http://127.0.0.1:8080/health/
DJANGO_CSRF_TRUSTED_ORIGINS=
```

Y recrear:

```bash
docker compose rm -sf nginx
docker compose up -d nginx
```

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

- Solo Nginx expone puerto al host: `8184:8080` en HTTP o `8184:8443` en HTTPS.
- PostgreSQL no publica puertos fuera de la red interna de Compose.
- La red `backend` es interna; solo `web`, `worker` y `db` participan. Nginx queda en `frontend` y no accede directo a PostgreSQL.
- `config.yml` se monta de solo lectura en `/app/config.yml`.
- Adjuntos, static files y datos de PostgreSQL quedan delimitados a `./data/`.
- Los contenedores `web` y `worker` usan `read_only`, `tmpfs` para rutas temporales y `no-new-privileges:true`.
- `web` y `worker` usan `cap_drop: [ALL]`.
- Nginx usa la imagen `nginxinc/nginx-unprivileged`, escucha en `8080` para HTTP o `8443` para HTTPS dentro del contenedor y no corre como root. El hardening extra de capabilities queda desactivado en Nginx para evitar resets del puerto publicado en algunos runtimes Docker.
- La imagen de Django corre con usuario no root `app` (`uid 10001`).
- `setup-permissions` corre como root solo para preparar ownership de `data/media` y `data/staticfiles`, termina y no queda expuesto.
- Usa siempre `EMAIL_GATEWAY_API_KEY` con un token largo y no publiques `.env` ni `config.yml`.
- Cambia `DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD` y las credenciales SMTP antes de produccion.
- Si publicas detras de un proxy externo con TLS, agrega el dominio real a `DJANGO_ALLOWED_HOSTS` y `DJANGO_CSRF_TRUSTED_ORIGINS`.

## Problemas Comunes En Docker

### Verificacion rapida de red

Despues de levantar el stack, estos checks deberian responder `200 OK` o `{"status":"ok"}`:

```bash
docker compose ps
docker compose exec nginx wget -S -O - http://web:8000/health/
docker compose exec nginx wget -S -O - http://127.0.0.1:8080/health/
curl -v http://127.0.0.1:8184/health/
```

El primer `wget` prueba `nginx -> web`. El segundo prueba que Nginx este escuchando dentro de su propio contenedor. El `curl` prueba el puerto publicado en el host.

### `PermissionError: /app/staticfiles/admin`

Significa que `collectstatic` no puede escribir en `./data/staticfiles` desde el usuario no root `10001`. Ejecuta:

```bash
docker compose down
docker compose up --build -d setup-permissions
docker compose up --build -d
```

En Linux tambien podes corregirlo desde el host:

```bash
sudo chown -R 10001:10001 data/media data/staticfiles
```

### `nginx: chown("/var/cache/nginx/client_temp", 101) failed`

Este error aparece con la imagen oficial de Nginx cuando corre con hardening estricto. El Compose usa `nginxinc/nginx-unprivileged`, que arranca sin root, escucha en `8080` dentro del contenedor y evita el `chown` de arranque de la imagen oficial.

### `host not found in upstream "web"`

Suele aparecer cuando Nginx arranca mientras `web` esta fallando o reiniciando. El Compose ahora agrega `healthcheck` en `web` y Nginx espera a que Django responda `/health/`.

### `curl :8184` conecta pero devuelve `Connection reset by peer`

Si `docker compose exec nginx wget -S -O - http://web:8000/health/` responde `200 OK`, pero el curl al host falla con reset, revisa que Nginx este escuchando en el mismo puerto interno publicado por Compose:

```bash
cat nginx/templates/http.conf.template
docker compose exec nginx nginx -T | grep -n "listen"
```

La configuracion correcta es:

```nginx
listen 8080;
```

con este publish:

```yaml
ports:
  - "0.0.0.0:${HTTP_PORT:-8184}:${NGINX_CONTAINER_PORT:-8080}"
```

Si el template activo quedo en `listen 80;`, Docker publica hacia `8080` pero Nginx no atiende ahi. Corregi el template o `NGINX_TEMPLATE_FILE` y recrea:

```bash
docker compose rm -sf nginx
docker compose up -d nginx
```

### `HTTP/1.1 400 Bad Request` al probar `http://web:8000/health/`

Django esta rechazando el header `Host`. Agrega `web` a `DJANGO_ALLOWED_HOSTS` y reinicia:

```env
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,web,tu-dominio-o-ip
```

Para acceso externo, tambien agrega la IP o dominio usado en el curl. Por ejemplo, si llamas `http://10.0.0.20:8184`, `10.0.0.20` debe estar en `DJANGO_ALLOWED_HOSTS`.

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

JSON valido minimo:

```json
{
  "recipients": ["persona@example.com"],
  "subject": "Asunto del correo",
  "html_body": "<p>Contenido HTML</p>"
}
```

JSON valido con multiples destinatarios:

```json
{
  "recipients": [
    "persona@example.com",
    "equipo@example.com",
    "Nombre Apellido <nombre@example.com>"
  ],
  "subject": "Alerta de infraestructura",
  "html_body": "<h1>Alerta</h1><p>Se detecto un evento importante.</p>"
}
```

Tambien se aceptan alias de campos para compatibilidad:

```json
{
  "to": "persona@example.com,equipo@example.com",
  "subject": "Prueba",
  "html": "<strong>Hola</strong>"
}
```

Reglas del JSON:

- `recipients` puede ser una lista JSON o un string separado por comas.
- `subject` es obligatorio y no puede estar vacio.
- `html_body` es obligatorio. Tambien se aceptan `html` o `body`.
- Para adjuntos usar `multipart/form-data`; JSON puro no sube archivos.
- No incluir credenciales SMTP en el payload. Las credenciales viven solo en `config.yml`.

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

## Checklist De Puesta En Marcha

- Copiar `.env.example` a `.env`.
- Copiar `config.example.yml` a `config.yml`.
- Cambiar `DJANGO_SECRET_KEY`.
- Cambiar `EMAIL_GATEWAY_API_KEY` por un token largo.
- Verificar `HTTP_PORT=8184`.
- Configurar `POSTGRES_PASSWORD`.
- Configurar `smtp.host`, `smtp.port`, `smtp.username`, `smtp.password`, `smtp.from_email` y `smtp.from_name`.
- Verificar que `smtp.host` no sea `smtp.example.com`.
- Crear carpetas locales si estas en Linux: `data/postgres`, `data/media`, `data/staticfiles`.
- Ajustar permisos de `data/media` y `data/staticfiles` para `uid 10001` si corresponde.
- Ejecutar `docker compose up --build -d`.
- Confirmar que `nginx/templates/http.conf.template` tenga `listen 8080` o que `nginx/templates/ssl.conf.template` tenga `listen 8443 ssl`, segun el modo elegido.
- Revisar `docker compose logs -f web`.
- Probar `GET /health/`.
- Enviar un correo JSON de prueba.
- Revisar el estado con `GET /api/v1/emails/<uuid>/`.
- Ejecutar `send_queued_mail --dry-run` si algo queda pendiente.

## Checklist De Produccion

- Usar dominio real en `DJANGO_ALLOWED_HOSTS`.
- Mantener `web` en `DJANGO_ALLOWED_HOSTS` para healthchecks y diagnostico interno de Compose.
- Si hay proxy/TLS externo, configurar `DJANGO_CSRF_TRUSTED_ORIGINS=https://tu-dominio`.
- No exponer PostgreSQL al host.
- No versionar `.env`, `config.yml` ni `data/`.
- Rotar `EMAIL_GATEWAY_API_KEY` si se comparte accidentalmente.
- Usar app password SMTP si el proveedor lo permite.
- Definir una sola estrategia principal de envio: hilo interno o worker dedicado.
- Configurar cron de respaldo solo con `--once` si queres recuperacion adicional.
- Monitorear logs de `web` o `worker`.
- Hacer backup de `data/postgres`.
- Hacer backup de `data/media` si los adjuntos deben conservarse.
