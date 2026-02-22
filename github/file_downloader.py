# github/file_downloader.py
"""
Simple file downloader from GitHub - exactly like your test
"""

import base64
import aiohttp
import asyncio
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

from core.config import config
from utils.logger import logger

class GitHubFileDownloader:
    """
    Downloads files from GitHub - exactly like your test function
    """
    
    def __init__(self):
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {config.GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.session: Optional[aiohttp.ClientSession] = None
        self.api_calls = 0
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def download_file(self, owner: str, repo: str, file_path: str) -> Optional[Dict]:
        """
        Download a single file - exactly like your test!
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/contents/{file_path}"
        
        async with self.session.get(url) as response:
            self.api_calls += 1
            
            if response.status == 200:
                data = await response.json()
                
                if data.get('content'):
                    # Decode base64 content
                    content = base64.b64decode(data['content']).decode('utf-8')
                    
                    return {
                        'path': file_path,
                        'content': content,
                        'size': len(content),
                        'sha': data.get('sha'),
                        'download_url': data.get('download_url'),
                        'name': file_path.split('/')[-1]
                    }
                else:
                    logger.warning(f"⚠️ No content in {file_path}")
            else:
                logger.error(f"❌ Failed to download {file_path}: {response.status}")
        
        return None
    
    async def download_multiple_files(self, owner: str, repo: str, file_paths: List[str]) -> Dict[str, Any]:
        """
        Download multiple files in parallel
        """
        tasks = []
        for file_path in file_paths:
            task = self.download_file(owner, repo, file_path)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        files = {}
        for result in results:
            if result:
                files[result['path']] = result
        
        return files
    
    def parse_github_url(self, repo_url: str) -> Dict[str, str]:
        """
        Parse GitHub URL to get owner and repo
        """
        parsed = urlparse(repo_url)
        path_parts = parsed.path.strip('/').split('/')
        
        return {
            'owner': path_parts[0],
            'repo': path_parts[1].replace('.git', '')
        }