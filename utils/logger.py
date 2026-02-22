# utils/logger.py
"""
Simple logging configuration without emojis
"""

import logging
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('agent-system')

# Add file handler
file_handler = logging.FileHandler(f'agent_{datetime.now().strftime("%Y%m%d")}.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# Remove emojis from logger messages by using a custom adapter if needed
# But for now, just don't use emojis in log messages