#!/usr/bin/env python3
"""
Logging configuration for strategic intelligence system.
"""

import logging
import os
from datetime import datetime
from pathlib import Path

def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Setup logging configuration for strategic intelligence operations."""
    
    # Ensure logs directory exists
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure logging
    log_filename = log_dir / f"strategic_intelligence_{datetime.now().strftime('%Y%m%d')}.log"
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger("strategic_intelligence")
    logger.info("Strategic intelligence logging initialized")
    return logger