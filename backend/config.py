from pathlib import Path

#
# Project Root
#
# /opt/pg_sa
#
PROJECT_ROOT = Path(__file__).resolve().parent.parent

#
# /opt/pg_sa/backend
#
BACKEND_DIR = PROJECT_ROOT / "backend"

#
# /opt/pg_sa/frontend
#
FRONTEND_DIR = PROJECT_ROOT / "frontend"

#
# /opt/pg_sa/pg_an
#
ANSIBLE_DIR = PROJECT_ROOT / "pg_an"

#
# /opt/pg_sa/backend/logs
#
LOG_DIR = BACKEND_DIR / "logs"

#
# /opt/pg_sa/backend/output
#
OUTPUT_DIR = BACKEND_DIR / "output"

#
# /tmp/postgres_summary.json
#
SUMMARY_FILE = OUTPUT_DIR / "postgres_summary.json"

