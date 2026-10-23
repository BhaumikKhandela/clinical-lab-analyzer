"""Launch one service with the shared local configuration; no secrets in argv.

Usage: python3 scripts/run_service.py auth|patient|analyzer|frontend
Uses python-dotenv from the analyzer requirements.
"""

import argparse
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / "Analyzer Service/backend/.env"


def database_environment(url):
    """Convert a Neon/libpq URL to pgJDBC configuration without losing SSL."""
    parsed = urlsplit(url)
    if parsed.scheme not in ("postgres", "postgresql") or not parsed.hostname or not parsed.path.strip("/"):
        raise ValueError("Expected a PostgreSQL URL with a host and database name.")
    host = parsed.hostname
    if ":" in host:
        host = f"[{host}]"
    authority = host + (f":{parsed.port}" if parsed.port else "")
    # libpq uses channel_binding; pgJDBC spells the property channelBinding.
    query = [("channelBinding" if k == "channel_binding" else k, v)
             for k, v in parse_qsl(parsed.query, keep_blank_values=True)
             if k not in ("user", "password")]
    jdbc = f"jdbc:postgresql://{authority}{parsed.path}"
    if query:
        jdbc += "?" + urlencode(query)
    return {
        "SPRING_DATASOURCE_URL": jdbc,
        "SPRING_DATASOURCE_USERNAME": unquote(parsed.username or ""),
        "SPRING_DATASOURCE_PASSWORD": unquote(parsed.password or ""),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("service", choices=("auth", "patient", "analyzer", "frontend"))
    args = parser.parse_args()
    try:
        from dotenv import dotenv_values
    except ImportError:
        parser.error("Install the analyzer requirements, then run with that Python environment.")
    env = {**os.environ, **{k: v for k, v in dotenv_values(ENV_FILE).items() if v is not None}}
    # Explicit shell overrides take precedence over the local file.
    env.update(os.environ)
    if args.service in ("auth", "patient"):
        key = "AUTH_DATABASE_URL" if args.service == "auth" else "DATABASE_URL"
        if not env.get(key):
            parser.error(f"Set {key} in {ENV_FILE}; auth and patient need separate databases.")
        if args.service == "auth" and env.get("DATABASE_URL"):
            auth = urlsplit(env[key])
            patient = urlsplit(env["DATABASE_URL"])
            if (auth.hostname, auth.port, auth.path) == (patient.hostname, patient.port, patient.path):
                parser.error("AUTH_DATABASE_URL must point to a different database from DATABASE_URL.")
        try:
            env.update(database_environment(env[key]))
        except ValueError:
            parser.error(f"Invalid {key}; expected a PostgreSQL connection URL.")
        cwd = ROOT / ("authService" if args.service == "auth" else "patientService/patientService")
        command = (["cmd", "/c", "mvnw.cmd"] if os.name == "nt" else ["sh", "./mvnw"]) + ["spring-boot:run"]
    elif args.service == "analyzer":
        cwd = ROOT / "Analyzer Service/backend"
        command = [sys.executable, "-m", "app.main"]
    else:
        cwd = ROOT / "frontend"
        command = ["npm.cmd" if os.name == "nt" else "npm", "run", "dev"]
    # Database and provider secrets belong only in the backend processes.
    if args.service in ("frontend", "analyzer"):
        for key in ("DATABASE_URL", "AUTH_DATABASE_URL", "SPRING_DATASOURCE_URL",
                    "SPRING_DATASOURCE_USERNAME", "SPRING_DATASOURCE_PASSWORD"):
            env.pop(key, None)
    if args.service != "analyzer":
        for key in ("OPENROUTER_API_KEY", "GROQ_API_KEY", "GEMINI_API_KEY", "INFERENCE_API_KEY",
                    "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL", "LANGFUSE_HOST"):
            env.pop(key, None)
    return subprocess.call(command, cwd=cwd, env=env)


if __name__ == "__main__":
    sys.exit(main())
