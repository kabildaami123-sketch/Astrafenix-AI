import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

class Config:
    # GitHub
    GITHUB_TOKEN: str = os.getenv('GITHUB_TOKEN', '')
    
    # DeepSeek API
    DEEPSEEK_API_KEY: str = os.getenv('DEEPSEEK_API_KEY', '')
    DEEPSEEK_MODEL: str = os.getenv('DEEPSEEK_MODEL', 'deepseek-coder')
    
    # Ollama
    OLLAMA_URL: str = os.getenv('OLLAMA_URL', 'http://localhost:11434')
    OLLAMA_MODEL: str = os.getenv('OLLAMA_MODEL', 'llama3.1:8b')
    
    # Performance
    MAX_FILES_TO_FETCH: int = int(os.getenv('MAX_FILES_TO_FETCH', '20'))
    BATCH_SIZE: int = int(os.getenv('BATCH_SIZE', '5'))
    CACHE_TTL: int = int(os.getenv('CACHE_TTL', '300'))
    
    # Analysis
    CONFIDENCE_THRESHOLD: float = float(os.getenv('CONFIDENCE_THRESHOLD', '0.6'))
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.GITHUB_TOKEN:
            raise ValueError("❌ GITHUB_TOKEN is required!")
        if not cls.DEEPSEEK_API_KEY:
            raise ValueError("❌ DEEPSEEK_API_KEY is required!")
        return True

config = Config()