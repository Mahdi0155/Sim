# ──────────────────────── config.py ────────────────────────

import os
import secrets

# IMPORTANT: Set via Render environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBHOOK_BASE = os.getenv("WEBHOOK_BASE", "https://your-service.onrender.com")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", secrets.token_urlsafe(16))
CHANNEL_UPLOAD_ID = int(os.getenv("CHANNEL_UPLOAD_ID", "0"))  # e.g. -1001234567890
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

# Default TTL for deletion
DELETE_AFTER_SECONDS_DEFAULT = int(os.getenv("DELETE_AFTER_SECONDS", "120"))
SELF_PING_INTERVAL_SECONDS = int(os.getenv("SELF_PING_INTERVAL", "240"))

# Timezone for stats formatting
TZ_NAME = os.getenv("TZ_NAME", "Europe/Amsterdam")

# Database (async)
# Convert provided sync URL to async for SQLAlchemy
DATABASE_URL_SYNC = os.getenv("DATABASE_URL", "")
if not DATABASE_URL_SYNC:
    # Example from Render input (External URL)
    # postgresql://user:pass@host:5432/dbname
    DATABASE_URL_SYNC = "postgresql://mehdi:IqD3OBcfFJ4UppwMZAxnDx4leVdMDDiP@dpg-d27puo63jp1c73fk3fog-a.oregon-postgres.render.com/database_xei2"

DATABASE_URL_ASYNC = DATABASE_URL_SYNC.replace("postgresql://", "postgresql+asyncpg://")
