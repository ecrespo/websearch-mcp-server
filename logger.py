import sys
from pathlib import Path
from loguru import logger
from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install as install_rich_traceback
from rich.theme import Theme
from rich.markup import escape
from config import settings

# Instalar Rich traceback para mejores mensajes de error
install_rich_traceback(show_locals=True)

# Tema personalizado para los logs
custom_theme = Theme({
    "log.time": "dim cyan",
    "log.message": "white",
    "log.path": "dim blue",
    "logging.level.debug": "dim blue",
    "logging.level.info": "green",
    "logging.level.warning": "yellow",
    "logging.level.error": "bold red",
    "logging.level.critical": "bold white on red",
    "log.level": "bold",
})

# Console de Rich para salida personalizada
console = Console(theme=custom_theme)


class RichLogHandler:
    """Handler personalizado que integra Rich con Loguru"""

    def __init__(self, console: Console):
        self.console = console

    def write(self, message):
        """Escribe el mensaje usando Rich"""
        message = message.rstrip()
        if message:
            self.console.print(message, markup=False, highlight=False)


def format_record(record: dict) -> str:
    """Formatea el registro de log para Rich"""
    level_colors = {
        "TRACE": "dim blue",
        "DEBUG": "cyan",
        "INFO": "green",
        "SUCCESS": "bold green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "bold white on red"
    }

    level = record["level"].name
    level_color = level_colors.get(level, "white")

    timestamp = record["time"].strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    file_info = f"{record['name']}:{record['function']}:{record['line']}"
    message = record["message"]

    formatted = (
        f"[dim cyan]{timestamp}[/dim cyan] | "
        f"[{level_color}]{level: <8}[/{level_color}] | "
        f"[dim blue]{file_info}[/dim blue] - "
        f"[white]{escape(message)}[/white]"
    )

    return formatted


def setup_logger():
    """Configura loguru con Rich para la aplicación"""

    logger.remove()

    # Handler para consola con Rich
    rich_handler = RichLogHandler(console)

    logger.add(
        rich_handler.write,
        format=format_record,
        level=settings.LOG_LEVEL,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # Handler para archivo
    log_path = Path(settings.LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level: <8} | "
        "{name}:{function}:{line} - "
        "{message}"
    )

    logger.add(
        settings.LOG_FILE,
        format=file_format,
        level=settings.LOG_LEVEL,
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        compression="zip",
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )

    # Handler para errores
    error_log_file = log_path.parent / "errors.log"

    logger.add(
        str(error_log_file),
        format=file_format,
        level="ERROR",
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        compression="zip",
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )

    logger.info("✨ Logger configurado con Rich y Loguru")
    logger.debug(f"📁 Logs guardados en: {settings.LOG_FILE}")
    logger.debug(f"📊 Nivel de log: {settings.LOG_LEVEL}")

    return logger


def log_section(title: str, style: str = "bold cyan"):
    """Imprime una sección destacada"""
    console.rule(f"[{style}]{title}[/{style}]")


def log_table(title: str, data: dict, style: str = "cyan"):
    """Imprime una tabla formateada"""
    from rich.table import Table

    table = Table(title=title, style=style)
    table.add_column("Campo", style="cyan", no_wrap=True)
    table.add_column("Valor", style="white")

    for key, value in data.items():
        table.add_row(str(key), str(value))

    console.print(table)


def log_json(data: dict, title: str = "JSON Data"):
    """Imprime JSON formateado"""
    from rich.json import JSON

    console.print(f"[bold cyan]{title}:[/bold cyan]")
    console.print(JSON.from_data(data))


def log_panel(message: str, title: str = None, style: str = "cyan"):
    """Imprime un mensaje en un panel"""
    from rich.panel import Panel

    console.print(Panel(message, title=title, style=style))


def log_tree(data: dict, title: str = "Tree View"):
    """Imprime una estructura de árbol"""
    from rich.tree import Tree

    def add_to_tree(tree, data):
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    branch = tree.add(f"[cyan]{key}[/cyan]")
                    add_to_tree(branch, value)
                else:
                    tree.add(f"[cyan]{key}[/cyan]: [white]{value}[/white]")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    branch = tree.add(f"[yellow][{i}][/yellow]")
                    add_to_tree(branch, item)
                else:
                    tree.add(f"[yellow][{i}][/yellow]: [white]{item}[/white]")

    tree = Tree(f"[bold]{title}[/bold]")
    add_to_tree(tree, data)
    console.print(tree)


def log_status(message: str, spinner: str = "dots"):
    """Context manager para mostrar un spinner"""
    return console.status(message, spinner=spinner)


class LogContext:
    """Context manager para agrupar logs"""

    def __init__(self, title: str, style: str = "cyan"):
        self.title = title
        self.style = style

    def __enter__(self):
        log_section(f"BEGIN: {self.title}", self.style)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            log_section(f"END: {self.title} ✓", "green")
        else:
            log_section(f"END: {self.title} ✗", "red")
        return False


# Inicializar logger
log = setup_logger()

__all__ = [
    'log',
    'console',
    'log_section',
    'log_table',
    'log_json',
    'log_panel',
    'log_tree',
    'log_status',
    'LogContext'
]