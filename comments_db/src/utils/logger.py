"""
Logging configuration for lexical analysis pipeline.
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional

from rich.logging import RichHandler
from rich.console import Console

from ..config import LOGGING_CONFIG


def setup_logging(
    level: Optional[str] = None,
    log_file: Optional[Path] = None,
    use_rich: bool = True
) -> logging.Logger:
    """
    Set up logging configuration.

    Args:
        level: Logging level (default from config)
        log_file: Log file path (default from config)
        use_rich: Whether to use rich console handler

    Returns:
        Configured logger instance
    """
    level = level or LOGGING_CONFIG["level"]

    # Create logger
    logger = logging.getLogger("lexical_analysis")
    logger.setLevel(getattr(logging, level))

    # Remove existing handlers
    logger.handlers.clear()

    # File handler with rotation (log file is per-project: ctx.logs_dir)
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=LOGGING_CONFIG["max_bytes"],
            backupCount=LOGGING_CONFIG["backup_count"]
        )
        file_formatter = logging.Formatter(LOGGING_CONFIG["format"])
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    # Console handler
    if use_rich:
        console = Console()
        console_handler = RichHandler(
            console=console,
            show_path=False,
            markup=True
        )
    else:
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(LOGGING_CONFIG["format"])
        console_handler.setFormatter(console_formatter)

    logger.addHandler(console_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (typically module name)

    Returns:
        Logger instance
    """
    return logging.getLogger(f"lexical_analysis.{name}")