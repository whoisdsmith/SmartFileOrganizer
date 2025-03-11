"""
Logging configuration for Smart File Organizer
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict


def setup_logging(config: Optional[Dict] = None) -> None:
    """Setup logging configuration"""
    config = config or {}

    # Create logs directory if it doesn't exist
    log_dir = os.path.join('src', 'logs')
    os.makedirs(log_dir, exist_ok=True)

    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Create file handlers
    main_handler = RotatingFileHandler(
        os.path.join(log_dir, 'smart_file_organizer.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    main_handler.setLevel(logging.INFO)

    error_handler = RotatingFileHandler(
        os.path.join(log_dir, 'error.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)

    # Create OCR-specific handler
    ocr_handler = RotatingFileHandler(
        os.path.join(log_dir, 'ocr.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    ocr_handler.setLevel(logging.INFO)

    # Create formatters
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    main_handler.setFormatter(formatter)
    error_handler.setFormatter(formatter)
    ocr_handler.setFormatter(formatter)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(main_handler)
    root_logger.addHandler(error_handler)

    # Setup OCR logger
    ocr_logger = logging.getLogger('ocr')
    ocr_logger.addHandler(ocr_handler)
    ocr_logger.setLevel(logging.INFO)

    # Configure logging levels from config
    if 'log_levels' in config:
        for logger_name, level in config['log_levels'].items():
            logging.getLogger(logger_name).setLevel(level)

    # Log startup message
    logging.info('Logging system initialized')
