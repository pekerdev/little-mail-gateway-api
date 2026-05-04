# little-mail-gateway-api

API Django para centralizar el envio de correos SMTP. Recibe destinatario(s), asunto, cuerpo HTML y adjuntos; guarda cada solicitud en base de datos y un worker propio la envia respetando el orden de llegada.

## Componentes

- Django + Gunicorn para la API.
- Nginx como proxy frontal.
- Worker Django propio (`send_queued_mail`) sin Celery ni Redis.
- SQLite para desarrollo local.
- PostgreSQL para Docker/produccion.
- Configuracion SMTP desde `config.yml` o `config.json`.

## Preparacion

```powershell
Copy-Item .env.example .env
Copy-Item config.example.yml config.yml
```

Edita `.env` y `config.yml` con tus credenciales reales.

## Ejecutar en Docker Compose

```powershell
docker compose up --build
```

La API queda disponible en `http://localhost:8080`.

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

## API

Si `EMAIL_GATEWAY_API_KEY` esta definido, enviar `Authorization: Bearer <token>` o `X-API-Key: <token>`.

### Encolar correo con JSON

```bash
curl -X POST http://localhost:8080/api/v1/emails/ \
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
curl -X POST http://localhost:8080/api/v1/emails/ \
  -H "Authorization: Bearer change-this-token" \
  -F 'recipients=["persona@example.com","equipo@example.com"]' \
  -F "subject=Prueba con adjunto" \
  -F "html_body=<h1>Hola</h1><p>Con archivo.</p>" \
  -F "attachments=@./archivo.pdf"
```

### Consultar estado

```bash
curl -H "Authorization: Bearer change-this-token" \
  http://localhost:8080/api/v1/emails/<uuid>/
```

Estados posibles: `pending`, `processing`, `sent`, `failed`.
