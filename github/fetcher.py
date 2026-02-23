import aiohttp
import asyncio
import base64
import time
from typing import Dict, Any, List, Tuple, Optional
from urllib.parse import urlparse
from datetime import datetime

from utils.cache import cache
from utils.logger import logger
from core.config import config

class GitHubFetcher:
    """
    Smart GitHub fetcher with sampling to demonstrate scalability
    Fully error-handled and production-ready
    """
    
    def __init__(self):
        # Validate token exists
        if not config.GITHUB_TOKEN:
            raise ValueError(
                "❌ GITHUB_TOKEN not found in environment variables!\n"
                "Please add it to your .env file: GITHUB_TOKEN=your_token_here"
            )
        
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {config.GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Multi-Agent-System-Hackathon/1.0"
        }
        self.session: Optional[aiohttp.ClientSession] = None
        self.api_calls = 0
        self.cache_hits = 0
        self.semaphore = asyncio.Semaphore(5)  # Max 5 concurrent requests
        self.rate_limit_remaining = 5000
        self.rate_limit_reset = 0
        
        logger.info(f"✅ GitHubFetcher initialized - Token present and validated")
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _make_request(self, url: str, retry_count: int = 0) -> Optional[Dict]:
        """
        Make authenticated request with rate limit handling and retries
        """
        max_retries = 3
        
        # Check rate limit before making request
        if self.rate_limit_remaining < 10:
            wait_time = max(0, self.rate_limit_reset - time.time())
            if wait_time > 0:
                logger.warning(f"⏳ Rate limit low. Waiting {wait_time:.0f}s")
                await asyncio.sleep(wait_time)
        
        try:
            async with self.semaphore:
                async with self.session.get(url) as resp:
                    self.api_calls += 1
                    
                    # Update rate limit info from headers
                    self.rate_limit_remaining = int(resp.headers.get('X-RateLimit-Remaining', 5000))
                    self.rate_limit_reset = int(resp.headers.get('X-RateLimit-Reset', 0))
                    
                    # Handle rate limiting
                    if resp.status == 403 and 'rate limit' in await resp.text():
                        reset_time = int(resp.headers.get('X-RateLimit-Reset', 0))
                        wait_time = max(0, reset_time - time.time())
                        
                        if wait_time > 0 and wait_time < 3600:  # Don't wait more than 1 hour
                            logger.warning(f"⏳ Rate limited! Waiting {wait_time:.0f}s")
                            await asyncio.sleep(wait_time)
                            return await self._make_request(url, retry_count)  # Retry
                        else:
                            logger.error("❌ Rate limit exceeded and reset time too far")
                            return None
                    
                    # Handle server errors (retry)
                    if resp.status >= 500 and retry_count < max_retries:
                        wait = 2 ** retry_count  # Exponential backoff
                        logger.warning(f"⚠️ Server error {resp.status}, retrying in {wait}s")
                        await asyncio.sleep(wait)
                        return await self._make_request(url, retry_count + 1)
                    
                    # Handle success
                    if resp.status == 200:
                        return await resp.json()
                    
                    # Handle other errors
                    if resp.status == 404:
                        logger.debug(f"🔍 Resource not found: {url}")
                        return None
                    
                    if resp.status == 401:
                        logger.error("❌ GitHub token is invalid or expired")
                        raise ValueError("Invalid GitHub token - please regenerate")
                    
                    logger.error(f"❌ HTTP {resp.status} for {url}")
                    return None
                    
        except aiohttp.ClientError as e:
            logger.error(f"🌐 Network error: {e}")
            if retry_count < max_retries:
                wait = 2 ** retry_count
                await asyncio.sleep(wait)
                return await self._make_request(url, retry_count + 1)
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            return None
    
    async def fetch_with_sampling(self, repo_url: str, max_files: int = 20) -> Tuple[Dict[str, Any], int]:
        """
        Fetch code with smart sampling - shows scalability
        Only fetches max_files, but knows total count
        """
        try:
            async with self:
                # Parse URL
                repo_info = self._parse_url(repo_url)
                logger.info(f"📦 Fetching repository: {repo_info['full_name']}")
                
                # Check cache
                cache_key = f"repo:{repo_info['full_name']}"
                cached = cache.get(cache_key)
                if cached:
                    self.cache_hits += 1
                    logger.info(f"✅ Cache hit for {repo_info['full_name']}")
                    return cached['files'], cached['total']
                
                # First, get repo info to know total size and default branch
                repo_data = await self._get_repo_info(repo_info)
                if not repo_data:
                    logger.error(f"❌ Failed to fetch repository info for {repo_info['full_name']}")
                    return {}, 0
                
                # Determine branch to use
                default_branch = repo_data.get('default_branch', 'main')
                logger.info(f"🌿 Using branch: {default_branch}")
                
                # Get tree to see all files
                tree = await self._get_repo_tree(repo_info, branch=default_branch)
                
                # Try fallback branches if needed
                if not tree or 'tree' not in tree:
                    logger.warning(f"⚠️ Branch '{default_branch}' failed, trying fallbacks")
                    for branch in ['main', 'master']:
                        if branch == default_branch:
                            continue
                        tree = await self._get_repo_tree(repo_info, branch=branch)
                        if tree and 'tree' in tree:
                            logger.info(f"✅ Found files on branch: {branch}")
                            break
                
                if not tree or 'tree' not in tree:
                    logger.error(f"❌ Could not fetch file tree for {repo_info['full_name']}")
                    return {}, 0
                
                all_files = tree.get('tree', [])
                total_count = len(all_files)
                logger.info(f"📊 Total files in repo: {total_count}")
                
                # Filter for relevant files
                relevant_files = [
                    f for f in all_files 
                    if f['type'] == 'blob' and self._is_relevant_file(f['path'])
                ]
                logger.info(f"📄 Relevant files: {len(relevant_files)}")
                
                # Sample if too many
                if len(relevant_files) > max_files:
                    logger.info(f"🎯 Sampling {max_files} from {len(relevant_files)} relevant files")
                    sampled_files = self._smart_sample(relevant_files, max_files)
                else:
                    sampled_files = relevant_files
                    logger.info(f"📋 Fetching all {len(sampled_files)} relevant files")
                
                # Fetch content for sampled files
                files = await self._fetch_file_contents(repo_info, sampled_files)
                logger.info(f"✅ Successfully fetched {len(files)} files")
                
                # Cache results
                cache.set(cache_key, {
                    'files': files,
                    'total': total_count
                }, ttl=config.CACHE_TTL)
                
                return files, total_count
                
        except Exception as e:
            logger.error(f"❌ Fatal error in fetch_with_sampling: {e}")
            return {}, 0
    
    def _smart_sample(self, files: List[Dict], max_files: int) -> List[Dict]:
        """
        Smart sampling to get representative files
        Ensures we get a good mix of file types
        """
        try:
            # Group by extension
            by_extension = {}
            extension_counts = {}
            
            for f in files:
                ext = self._get_extension(f['path'])
                if ext not in by_extension:
                    by_extension[ext] = []
                    extension_counts[ext] = 0
                by_extension[ext].append(f)
                extension_counts[ext] += 1
            
            # Log what we found
            logger.info(f"📁 Files by extension: {extension_counts}")
            
            # Calculate sampling strategy
            sampled = []
            extensions = list(by_extension.keys())
            
            # Ensure we get at least 1 from each extension if possible
            per_extension = max(1, max_files // len(extensions))
            
            # First pass: take from each extension
            for ext in extensions:
                take = min(per_extension, len(by_extension[ext]))
                sampled.extend(by_extension[ext][:take])
                logger.debug(f"   • .{ext}: taking {take}/{len(by_extension[ext])}")
            
            # Second pass: fill remaining slots from largest groups
            if len(sampled) < max_files:
                remaining = max_files - len(sampled)
                # Sort extensions by count (largest first)
                sorted_ext = sorted(extensions, 
                                  key=lambda e: len(by_extension[e]), 
                                  reverse=True)
                
                for ext in sorted_ext:
                    if remaining <= 0:
                        break
                    
                    # Get files not already sampled
                    current = [f for f in by_extension[ext] 
                              if f not in sampled]
                    
                    if current:
                        take = min(remaining, len(current))
                        sampled.extend(current[:take])
                        remaining -= take
                        logger.debug(f"   • .{ext}: adding {take} more")
            
            result = sampled[:max_files]
            logger.info(f"✅ Smart sampling complete: {len(result)} files from {len(extensions)} types")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in smart sampling: {e}")
            # Fallback: simple sampling
            return files[:max_files]
    
    async def _get_repo_info(self, repo_info: Dict) -> Optional[Dict]:
        """Get repository information"""
        url = f"{self.base_url}/repos/{repo_info['full_name']}"
        return await self._make_request(url)
    
    async def _get_repo_tree(self, repo_info: Dict, branch: str = 'main') -> Dict:
        """Get repository tree"""
        url = f"{self.base_url}/repos/{repo_info['full_name']}/git/trees/{branch}?recursive=1"
        result = await self._make_request(url)
        return result if result else {}
    
    async def _fetch_file_contents(self, repo_info: Dict, files: List[Dict]) -> Dict[str, Any]:
        """Fetch file contents in parallel with proper error handling"""
        tasks = []
        valid_files = []
        
        for file in files:
            task = self._fetch_single_file(repo_info, file['path'])
            tasks.append(task)
            valid_files.append(file)
        
        if not tasks:
            return {}
        
        # Gather results, handling exceptions
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results
        contents = {}
        for file, result in zip(valid_files, results):
            path = file['path']
            
            if isinstance(result, Exception):
                logger.error(f"❌ Failed to fetch {path}: {result}")
                continue
                
            if result:  # Successfully got content
                contents[path] = {
                    'path': path,
                    'content': result,
                    'size': len(result),
                    'extension': self._get_extension(path)
                }
                logger.debug(f"✅ Fetched: {path}")
        
        logger.info(f"📥 Fetched {len(contents)}/{len(valid_files)} files successfully")
        return contents
    
    async def _fetch_single_file(self, repo_info: Dict, path: str) -> Optional[str]:
        """Fetch single file content with improved error handling"""
        try:
            # Check cache first
            cache_key = f"file:{repo_info['full_name']}:{path}"
            cached = cache.get(cache_key)
            if cached:
                self.cache_hits += 1
                logger.debug(f"💾 Cache hit: {path}")
                return cached
            
            # Fetch from GitHub
            url = f"{self.base_url}/repos/{repo_info['full_name']}/contents/{path}"
            data = await self._make_request(url)
            
            if data and data.get('content') and data.get('encoding') == 'base64':
                try:
                    # Decode base64 content
                    content = base64.b64decode(data['content']).decode('utf-8')
                    
                    # Cache for next time
                    cache.set(cache_key, content, ttl=config.CACHE_TTL)
                    logger.debug(f"📄 Downloaded: {path}")
                    
                    return content
                except UnicodeDecodeError:
                    logger.warning(f"⚠️ Binary file (can't decode): {path}")
                    return None
                except Exception as e:
                    logger.error(f"❌ Error decoding {path}: {e}")
                    return None
            else:
                logger.debug(f"⚠️ No content for {path}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error fetching {path}: {e}")
            return None
    
    def _parse_url(self, repo_url: str) -> Dict:
        """Parse GitHub URL with robust error handling"""
        try:
            # Remove trailing .git and clean URL
            repo_url = repo_url.rstrip('/')
            if repo_url.endswith('.git'):
                repo_url = repo_url[:-4]
            
            parsed = urlparse(repo_url)
            path_parts = parsed.path.strip('/').split('/')
            
            if len(path_parts) < 2:
                raise ValueError(f"Invalid GitHub URL format: {repo_url}")
            
            owner = path_parts[0]
            repo = path_parts[1]
            
            return {
                'owner': owner,
                'repo': repo,
                'full_name': f"{owner}/{repo}"
            }
        except Exception as e:
            logger.error(f"❌ Failed to parse URL {repo_url}: {e}")
            raise ValueError(f"Invalid GitHub URL: {repo_url}")
    
    def _get_extension(self, path: str) -> str:
        """Get file extension safely"""
        if '.' in path:
            return path.split('.')[-1].lower()
        return 'no_ext'
    
    def _is_relevant_file(self, path: str) -> bool:
        """Check if file is relevant for analysis"""
        try:
            # Relevant extensions
            relevant_extensions = {'py', 'js', 'jsx', 'ts', 'html', 'css', 'json', 'md', 'txt'}
            
            filename = path.split('/')[-1].lower()
            
            # Check extension
            if '.' in filename:
                ext = filename.split('.')[-1]
                return ext in relevant_extensions
            
            # No extension - check whitelist
            no_ext_whitelist = {
                'readme', 'license', 'makefile', 'dockerfile',
                'contributing', 'changelog', 'authors', 'todo'
            }
            return filename in no_ext_whitelist
            
        except Exception:
            return False  # If any error, skip the file
    
    def get_stats(self) -> Dict[str, Any]:
        """Get fetcher statistics"""
        return {
            'api_calls': self.api_calls,
            'cache_hits': self.cache_hits,
            'cache_hit_rate': f"{(self.cache_hits / max(1, self.api_calls + self.cache_hits)) * 100:.1f}%",
            'rate_limit_remaining': self.rate_limit_remaining
        }