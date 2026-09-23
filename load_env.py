"""Load repo-root .env for local runs.

Does not override variables already in the environment, so Cloud Run Secret
Manager mounts and CI env win over a laptop .env.
"""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env", override=False)
