"""项目启动入口。"""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.api.server import AdminServer
from app.core.log_setup import setup_logging
from app.core.service import BotApplication
from app.core.settings import load_settings


def main() -> None:
    settings = load_settings()
    setup_logging(
        log_level=settings.runtime.log_level,
        log_file=settings.paths.runtime_dir / "bot.log",
    )

    app = BotApplication(settings)
    admin_server = AdminServer(
        host=settings.runtime.admin_host,
        port=settings.runtime.admin_port,
        app_service=app,
    )
    if settings.runtime.start_admin_server:
        admin_server.start()

    try:
        asyncio.run(app.run())
    finally:
        admin_server.stop()


if __name__ == "__main__":
    main()
