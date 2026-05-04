import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml
from django.conf import settings


@dataclass(frozen=True)
class SmtpConfig:
    host: str
    port: int
    username: str
    password: str
    from_email: str
    from_name: str
    use_tls: bool = True
    use_ssl: bool = False
    timeout: int = 30


@lru_cache(maxsize=1)
def get_smtp_config() -> SmtpConfig:
    path = Path(settings.EMAIL_GATEWAY_CONFIG)
    if not path.exists():
        raise FileNotFoundError(f"SMTP config file not found: {path}")

    with path.open("r", encoding="utf-8") as fh:
        if path.suffix.lower() == ".json":
            data = json.load(fh)
        else:
            data = yaml.safe_load(fh)

    smtp = data.get("smtp", data)
    return SmtpConfig(
        host=smtp["host"],
        port=int(smtp.get("port", 587)),
        username=smtp.get("username", ""),
        password=smtp.get("password", ""),
        from_email=smtp["from_email"],
        from_name=smtp.get("from_name", smtp["from_email"]),
        use_tls=bool(smtp.get("use_tls", True)),
        use_ssl=bool(smtp.get("use_ssl", False)),
        timeout=int(smtp.get("timeout", 30)),
    )
