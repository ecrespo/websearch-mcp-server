"""
Centralized Loguru logger configuration for the application.

- Logs to file with daily rotation at midnight
- Keeps logs for 31 days (retention)
- Ensures the log directory exists
- Exposes a configured `logger` for import across the app

Usage:
    from loguru_config import logger
    logger.info("Something happened")
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from loguru import logger
from rich.console import Console
from rich.text import Text
from rich.traceback import install as rich_traceback_install

# Resolve log directory and file from env (optional), with sensible defaults
LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)
_default_log_file = LOG_DIR / "app.log"
LOG_FILE = Path(os.getenv("LOG_FILE", str(_default_log_file)))

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Reset default sinks to have full control
logger.remove()

# Setup Rich console and traceback
console = Console(stderr=True)
rich_traceback_install(console=console, show_locals=False)

# Rich-styled console sink
_LEVEL_STYLES = {
    "TRACE": "dim",
    "DEBUG": "cyan",
    "INFO": "green",
    "SUCCESS": "bold green",
    "WARNING": "yellow",
    "ERROR": "bold red",
    "CRITICAL": "reverse red",
}

def _rich_console_sink(message):
    record = message.record
    level_name = record["level"].name
    style = _LEVEL_STYLES.get(level_name, "white")
    time_str = record["time"].strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    location = f"{record['name']}:{record['function']}:{record['line']}"
    text = Text()
    text.append(time_str, style="dim")
    text.append(" | ")
    text.append(f"{level_name:<8}", style=style)
    text.append(" | ")
    text.append(location, style="cyan")
    text.append(" - ")
    text.append(record["message"])
    console.print(text, highlight=False, soft_wrap=False)

# Add Rich console sink
logger.add(
    _rich_console_sink,
    level=LOG_LEVEL,
    backtrace=True,
    diagnose=False,
    enqueue=False,
)

# File sink with rotation and retention as requested
logger.add(
    LOG_FILE,
    rotation="00:00",        # rotate daily at midnight
    retention="31 days",     # keep 31 days of logs
    compression=None,         # no compression by default
    level=LOG_LEVEL,
    backtrace=True,
    diagnose=False,
    enqueue=True,             # safer in multi-process environments
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {process.name}:{thread.name} | {name}:{function}:{line} - {message}",
)

__all__ = ["logger", "LOG_FILE", "LOG_DIR"]
