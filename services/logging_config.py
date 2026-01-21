"""
Centralized logging configuration for PhotoSense-AI.

Logs are stored in the OS-specific app data directory:
- macOS: ~/Library/Application Support/PhotoSense-AI/logs/
- Windows: %APPDATA%/PhotoSense-AI/logs/
- Linux: ~/.local/share/PhotoSense-AI/logs/

Log rotation: 10MB per file, keeps 5 backup files.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from services.config import LOG_DIR, APP_NAME, APP_VERSION

# Log format with timestamp, level, module, and message
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Rotation settings
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5

_configured = False


def configure_logging(
    level: int = logging.INFO,
    console: bool = True,
    file_logging: bool = True,
    log_file: Optional[str] = None,
) -> logging.Logger:
    """
    Configure centralized logging with file rotation and console output.
    
    Args:
        level: Logging level (default: INFO)
        console: Whether to log to console (default: True)
        file_logging: Whether to log to file (default: True)
        log_file: Custom log file name (default: photosense.log)
    
    Returns:
        The root logger instance
    """
    global _configured
    
    if _configured:
        return logging.getLogger()
    
    # Ensure log directory exists
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create formatters
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    handlers = []
    
    # File handler with rotation
    if file_logging:
        log_path = LOG_DIR / (log_file or "photosense.log")
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=MAX_LOG_SIZE,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)
    
    # Add handlers to root logger
    for handler in handlers:
        root_logger.addHandler(handler)
    
    # Log startup message
    root_logger.info(f"{'='*60}")
    root_logger.info(f"{APP_NAME} v{APP_VERSION} - Logging initialized")
    root_logger.info(f"Log directory: {LOG_DIR}")
    root_logger.info(f"{'='*60}")
    
    _configured = True
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def set_log_level(level: int) -> None:
    """
    Change the logging level at runtime.
    
    Args:
        level: New logging level (e.g., logging.DEBUG)
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    for handler in root_logger.handlers:
        handler.setLevel(level)


def get_log_file_path() -> Path:
    """Get the path to the main log file."""
    return LOG_DIR / "photosense.log"
