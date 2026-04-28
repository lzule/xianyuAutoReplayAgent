"""项目配置加载。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


def load_dotenv(env_path: Path) -> None:
    """读取本地 .env 文件，不依赖额外包。"""
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data or {}


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    app_dir: Path
    data_dir: Path
    runtime_dir: Path
    exports_dir: Path
    configs_dir: Path
    knowledge_dir: Path


@dataclass(frozen=True)
class RuntimeSettings:
    log_level: str
    auto_reply_enabled: bool
    start_admin_server: bool
    admin_host: str
    admin_port: int
    xianyu_enabled: bool
    simulate_human_typing: bool
    websocket_url: str
    heartbeat_interval: int
    heartbeat_timeout: int
    message_expire_ms: int
    use_system_proxy: bool
    xianyu_user_agent: str
    agent_core_enabled: bool
    agent_core_timeout_ms: int


@dataclass(frozen=True)
class ModelSettings:
    api_key: str
    base_url: str
    model_name: str


@dataclass(frozen=True)
class IntegrationSettings:
    cookies_str: str
    feishu_webhook: str
    agent_core_base_url: str


@dataclass(frozen=True)
class AppSettings:
    paths: ProjectPaths
    runtime: RuntimeSettings
    model: ModelSettings
    integration: IntegrationSettings


def get_project_paths() -> ProjectPaths:
    root = Path(__file__).resolve().parents[2]
    return ProjectPaths(
        root=root,
        app_dir=root / "app",
        data_dir=root / "data",
        runtime_dir=root / "data" / "runtime",
        exports_dir=root / "data" / "exports",
        configs_dir=root / "configs",
        knowledge_dir=root / "knowledge",
    )


def load_settings() -> AppSettings:
    paths = get_project_paths()
    load_dotenv(paths.root / ".env")

    runtime = RuntimeSettings(
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        auto_reply_enabled=os.getenv("AUTO_REPLY_ENABLED", "true").lower() == "true",
        start_admin_server=os.getenv("START_ADMIN_SERVER", "true").lower() == "true",
        admin_host=os.getenv("ADMIN_HOST", "127.0.0.1"),
        admin_port=int(os.getenv("ADMIN_PORT", "8765")),
        xianyu_enabled=os.getenv("XIANYU_ENABLED", "true").lower() == "true",
        simulate_human_typing=os.getenv("SIMULATE_HUMAN_TYPING", "false").lower() == "true",
        websocket_url=os.getenv("XIANYU_WEBSOCKET_URL", "wss://wss-goofish.dingtalk.com/"),
        heartbeat_interval=int(os.getenv("HEARTBEAT_INTERVAL", "15")),
        heartbeat_timeout=int(os.getenv("HEARTBEAT_TIMEOUT", "5")),
        message_expire_ms=int(os.getenv("MESSAGE_EXPIRE_MS", "300000")),
        use_system_proxy=os.getenv("USE_SYSTEM_PROXY", "false").lower() == "true",
        xianyu_user_agent=os.getenv(
            "XIANYU_USER_AGENT",
            (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/146.0.0.0 Safari/537.36"
            ),
        ),
        agent_core_enabled=os.getenv("AGENT_CORE_ENABLED", "false").lower() == "true",
        agent_core_timeout_ms=int(os.getenv("AGENT_CORE_TIMEOUT_MS", "6000")),
    )
    model = ModelSettings(
        api_key=os.getenv("API_KEY", ""),
        base_url=os.getenv("MODEL_BASE_URL", ""),
        model_name=os.getenv("MODEL_NAME", ""),
    )
    integration = IntegrationSettings(
        cookies_str=os.getenv("COOKIES_STR", ""),
        feishu_webhook=os.getenv("FEISHU_WEBHOOK", ""),
        agent_core_base_url=os.getenv("AGENT_CORE_BASE_URL", ""),
    )
    return AppSettings(paths=paths, runtime=runtime, model=model, integration=integration)
