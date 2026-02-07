"""
Centralized logging configuration for the trading bot.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logger(
    name: str = "trading_bot",
    level: int = logging.INFO,
    log_to_file: bool = True,
    log_dir: str = "logs",
    verbose: bool = False
) -> logging.Logger:
    """
    Setup and return a configured logger.
    
    Args:
        name: Logger name
        level: Logging level
        log_to_file: Whether to log to file
        log_dir: Directory for log files
        verbose: Enable debug logging
        
    Returns:
        Configured logger instance
    """
    # Use DEBUG level if verbose
    if verbose:
        level = logging.DEBUG
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Detailed formatter with more context
    detailed_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Simple formatter for console
    simple_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S"
    )
    
    # Console handler - shows INFO and above
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(simple_formatter)
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)
    
    # File handler - logs everything including DEBUG
    if log_to_file:
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Main log file
        file_handler = logging.FileHandler(
            log_path / f"{name}_{today}.log",
            encoding="utf-8"
        )
        file_handler.setFormatter(detailed_formatter)
        file_handler.setLevel(logging.DEBUG)  # Capture all DEBUG logs in file
        logger.addHandler(file_handler)
        
        # Also add debug handler for detailed logs
        debug_handler = logging.FileHandler(
            log_path / f"{name}_{today}_debug.log",
            encoding="utf-8"
        )
        debug_handler.setFormatter(detailed_formatter)
        debug_handler.setLevel(logging.DEBUG)
        logger.addHandler(debug_handler)
    
    # Also configure root logger for library modules
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    return logger


# Default logger
LOG = setup_logger()


def enable_debug_logging():
    """Enable debug level logging for all trading_bot loggers."""
    # Update all loggers
    for name in logging.Logger.manager.loggerDict:
        if name.startswith("src.") or name == "trading_bot":
            logger = logging.getLogger(name)
            logger.setLevel(logging.DEBUG)
            for handler in logger.handlers:
                handler.setLevel(logging.DEBUG)
    
    LOG.info("🔧 Debug logging enabled")
