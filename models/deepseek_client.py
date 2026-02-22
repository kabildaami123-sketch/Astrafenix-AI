import aiohttp
import asyncio
import json
import re
from typing import Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential

from core.config import config
from utils.logger import logger

class DeepSeekClient:
    """
    DeepSeek API client for code understanding
    """
    
    def __init__(self):
        self.api_key = config.DEEPSEEK_API_KEY
        self.base_url = "https://api.deepseek.com/v1"
        self.model = config.DEEPSEEK_MODEL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def analyze_code(self, code: str, file_path: str, file_type: str) -> Dict[str, Any]:
        """
        Send code to DeepSeek for deep understanding
        """
        # FIXED: Properly formatted f-string with clear closing
        prompt = (
            f"You are an expert software architect analyzing a {file_type} file.\n\n"
            f"File: {file_path}\n\n"
            f"Code:\n"
            f"```{file_type}\n"
            f"{code[:3000]}\n"
            f"```\n\n"
            f"Analyze this code and provide a JSON response with:\n"
            f"1. purpose: What this code does (1 sentence)\n"
            f"2. functions: List of key functions with their purpose\n"
            f"3. business_rules: List of business rules/logic found\n"
            f"4. data_flow: How data moves through this code\n"
            f"5. dependencies: External libraries/APIs used\n"
            f"6. security_concerns: Any security issues spotted\n"
            f"7. complexity: Simple/Moderate/Complex\n"
            f"8. confidence: Score 0.0-1.0 of your understanding\n\n"
            f"Return ONLY valid JSON, no other text."
        )

        try:
            async with self.session.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are a code analysis expert. Return only JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 2000
                }
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    content = result['choices'][0]['message']['content']
                    
                    # Extract JSON from response
                    try:
                        # Find JSON in the response
                        json_match = re.search(r'\{.*\}', content, re.DOTALL)
                        if json_match:
                            return json.loads(json_match.group())
                        else:
                            return json.loads(content)
                    except Exception as e:
                        logger.error(f"Failed to parse DeepSeek response: {e}")
                        logger.error(f"Response content: {content[:200]}")
                        return self._fallback_analysis(file_type)
                else:
                    error_text = await resp.text()
                    logger.error(f"DeepSeek API error: {resp.status} - {error_text[:200]}")
                    return self._fallback_analysis(file_type)
                    
        except Exception as e:
            logger.error(f"DeepSeek client error: {e}")
            return self._fallback_analysis(file_type)
    
    def _fallback_analysis(self, file_type: str) -> Dict:
        """Fallback when API fails"""
        return {
            "purpose": f"Unknown {file_type} file",
            "functions": [],
            "business_rules": [],
            "data_flow": "Unknown",
            "dependencies": [],
            "security_concerns": [],
            "complexity": "Unknown",
            "confidence": 0.3
        }