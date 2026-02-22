#!/usr/bin/env python3
"""
Simple GitHub Token Tester
Run this to verify your GitHub token works before using the full system
"""

import os
import sys
import json
import time
import base64
from datetime import datetime
from urllib.parse import urlparse
import requests
from dotenv import load_dotenv

# Load token from .env
load_dotenv()

class GitHubTokenTester:
    """
    Simple tester for GitHub token functionality
    """
    
    def __init__(self, token=None):
        self.token = token or os.getenv('GITHUB_TOKEN')
        if not self.token:
            raise ValueError("❌ No GitHub token found! Set GITHUB_TOKEN in .env file")
        
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Stats
        self.api_calls = 0
        
    def print_header(self, text):
        """Print a formatted header"""
        print(f"\n{'='*60}")
        print(f" {text}")
        print(f"{'='*60}")
    
    def test_token_validity(self):
        """Test 1: Check if token is valid"""
        self.print_header("TEST 1: Token Validity")
        
        try:
            response = self.session.get(f"{self.base_url}/user")
            self.api_calls += 1
            
            if response.status_code == 200:
                user_data = response.json()
                print(f"✅ Token is VALID!")
                print(f"   Authenticated as: {user_data['login']}")
                print(f"   User type: {user_data['type']}")
                print(f"   Name: {user_data.get('name', 'Not set')}")
                return True
            else:
                print(f"❌ Token is INVALID! Status: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error testing token: {e}")
            return False
    
    def test_rate_limits(self):
        """Test 2: Check rate limits"""
        self.print_header("TEST 2: Rate Limits")
        
        response = self.session.get(f"{self.base_url}/rate_limit")
        self.api_calls += 1
        
        if response.status_code == 200:
            limits = response.json()
            core = limits['resources']['core']
            
            print(f"📊 Rate Limit Status:")
            print(f"   • Limit: {core['limit']} requests/hour")
            print(f"   • Used: {core['used']}")
            print(f"   • Remaining: {core['remaining']}")
            print(f"   • Resets: {datetime.fromtimestamp(core['reset']).strftime('%H:%M:%S')}")
            
            if core['remaining'] < 100:
                print(f"⚠️  Warning: Low on rate limits!")
            else:
                print(f"✅ Good rate limit remaining")
        else:
            print(f"❌ Failed to get rate limits: {response.status_code}")
    
    def test_public_repo_access(self, owner="psf", repo="requests"):
        """Test 3: Access a public repository"""
        self.print_header(f"TEST 3: Public Repo Access - {owner}/{repo}")
        
        url = f"{self.base_url}/repos/{owner}/{repo}"
        response = self.session.get(url)
        self.api_calls += 1
        
        if response.status_code == 200:
            repo_data = response.json()
            print(f"✅ Successfully accessed public repo!")
            print(f"   📦 Repo: {repo_data['full_name']}")
            print(f"   ⭐ Stars: {repo_data['stargazers_count']}")
            print(f"   📝 Description: {repo_data['description'][:50]}...")
            print(f"   🔒 Private: {repo_data['private']}")
        else:
            print(f"❌ Failed to access repo: {response.status_code}")
    
    def test_private_repo_access(self):
        """Test 4: Check if token can access private repos"""
        self.print_header("TEST 4: Private Repo Access")
        
        # Get user's repos to check for private ones
        response = self.session.get(f"{self.base_url}/user/repos?visibility=all&per_page=5")
        self.api_calls += 1
        
        if response.status_code == 200:
            repos = response.json()
            private_repos = [r for r in repos if r['private']]
            
            if private_repos:
                print(f"✅ Token has access to {len(private_repos)} private repos:")
                for repo in private_repos[:3]:
                    print(f"   🔒 {repo['full_name']}")
            else:
                print(f"ℹ️  No private repos found or no access")
                print(f"   This is fine if you only need public repos")
        else:
            print(f"❌ Failed to check private repos: {response.status_code}")
    
    def test_repo_contents(self, owner="psf", repo="requests", path=""):
        """Test 5: Fetch repository contents"""
        self.print_header(f"TEST 5: Fetch Repo Contents - {owner}/{repo}")
        
        url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
        response = self.session.get(url)
        self.api_calls += 1
        
        if response.status_code == 200:
            contents = response.json()
            
            if isinstance(contents, list):
                files = [c for c in contents if c['type'] == 'file']
                dirs = [c for c in contents if c['type'] == 'dir']
                
                print(f"📁 Root contents:")
                print(f"   • {len(files)} files")
                print(f"   • {len(dirs)} directories")
                
                # Show some files
                if files:
                    print(f"\n📄 Sample files:")
                    for f in files[:5]:
                        print(f"   • {f['name']} ({f['size']} bytes)")
            else:
                print(f"📄 Single file: {contents['name']}")
                print(f"   Size: {contents['size']} bytes")
                print(f"   Type: {contents['type']}")
        else:
            print(f"❌ Failed to fetch contents: {response.status_code}")
    
    def test_file_download(self, owner="psf", repo="requests", file_path="README.md"):
        """Test 6: Download and read a file"""
        self.print_header(f"TEST 6: Download File - {file_path}")
        
        url = f"{self.base_url}/repos/{owner}/{repo}/contents/{file_path}"
        response = self.session.get(url)
        self.api_calls += 1
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('content'):
                # Decode base64 content
                content = base64.b64decode(data['content']).decode('utf-8')
                print(f"✅ Successfully downloaded {file_path}")
                print(f"   📏 Size: {len(content)} characters")
                print(f"   📝 Preview:")
                print(f"   {'-'*40}")
                print(content[:200] + "..." if len(content) > 200 else content)
                print(f"   {'-'*40}")
            else:
                print(f"❌ No content in response")
        else:
            print(f"❌ Failed to download file: {response.status_code}")
    
    def test_search_code(self, query="requests"):
        """Test 7: Search code (tests token search capability)"""
        self.print_header(f"TEST 7: Code Search - '{query}'")
        
        url = f"{self.base_url}/search/code"
        params = {"q": query, "per_page": 3}
        
        response = self.session.get(url, params=params)
        self.api_calls += 1
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Search successful!")
            print(f"   🔍 Found {data['total_count']} results")
            print(f"   📋 Top results:")
            for item in data['items'][:3]:
                print(f"      • {item['path']} in {item['repository']['full_name']}")
        else:
            print(f"❌ Search failed: {response.status_code}")
    
    def test_smart_fetch_demo(self, repo_url="https://github.com/psf/requests", max_files=5):
        """Test 8: Demo of our smart fetching logic"""
        self.print_header(f"TEST 8: Smart Fetch Demo - Sampling {max_files} files")
        
        # Parse URL
        parsed = urlparse(repo_url)
        path_parts = parsed.path.strip('/').split('/')
        owner, repo = path_parts[0], path_parts[1].replace('.git', '')
        
        print(f"📦 Repo: {owner}/{repo}")
        
        # Get the full tree
        url = f"{self.base_url}/repos/{owner}/{repo}/git/trees/main?recursive=1"
        response = self.session.get(url)
        self.api_calls += 1
        
        if response.status_code == 200:
            tree_data = response.json()
            all_files = [f for f in tree_data['tree'] if f['type'] == 'blob']
            
            print(f"📊 Total files in repo: {len(all_files)}")
            
            # Smart sampling by extension
            by_extension = {}
            for f in all_files:
                ext = f['path'].split('.')[-1] if '.' in f['path'] else 'no_ext'
                if ext not in by_extension:
                    by_extension[ext] = []
                by_extension[ext].append(f)
            
            print(f"\n📁 Files by extension:")
            for ext, files in sorted(by_extension.items(), key=lambda x: len(x[1]), reverse=True)[:8]:
                print(f"   .{ext}: {len(files)} files")
            
            # Sample intelligently
            sampled = []
            extensions = list(by_extension.keys())
            per_extension = max(1, max_files // len(extensions))
            
            print(f"\n🎯 Smart sampling (taking ~{per_extension} from each extension):")
            for ext in extensions[:5]:  # Show first 5 extensions
                take = min(per_extension, len(by_extension[ext]))
                sampled.extend(by_extension[ext][:take])
                print(f"   • .{ext}: taking {take}/{len(by_extension[ext])} files")
            
            print(f"\n✅ Sampled {len(sampled)}/{max_files} files intelligently")
            print(f"   This is EXACTLY what our system does!")
            
        else:
            print(f"❌ Failed to get tree: {response.status_code}")
    
    def run_all_tests(self):
        """Run all tests"""
        print("\n🔧 GITHUB TOKEN TESTER")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Test 1: Token validity
        if not self.test_token_validity():
            print("\n❌ Token invalid - stopping tests")
            return False
        
        # Test 2: Rate limits
        self.test_rate_limits()
        
        # Test 3: Public repo access
        self.test_public_repo_access()
        
        # Test 4: Private repo check
        self.test_private_repo_access()
        
        # Test 5: Repo contents
        self.test_repo_contents()
        
        # Test 6: File download
        self.test_file_download()
        
        # Test 7: Code search
        self.test_search_code()
        
        # Test 8: Smart fetch demo
        self.test_smart_fetch_demo()
        
        # Summary
        self.print_header("TEST SUMMARY")
        print(f"📊 Total API calls made: {self.api_calls}")
        print(f"⏱️  Rate limit remaining: Check test 2")
        print(f"\n{'✅' if self.api_calls > 0 else '❌'} Token is working perfectly!")
        print(f"\nYour token is ready to use in the full system! 🚀")
        
        return True

def test_feedback_system():
    """
    Test the feedback system - demonstrate how to use ingest_feedback
    """
    print("\n" + "="*60)
    print(" FEEDBACK SYSTEM TESTER")
    print("="*60)
    
    # Import the orchestrator
    from core.orchestrator import BusinessReportOrchestrator
    
    orchestrator = BusinessReportOrchestrator()
    
    # Simulate some analyses (normally these would come from the analyzer)
    simulated_analyses = {
        'app.py': {
            'type': 'python',
            'key_functions': [
                {'name': 'authenticate', 'line': 10, 'purpose': '🔐 Handles user login'},
                {'name': 'calculate_discount', 'line': 25, 'purpose': '🧮 Performs calculations'}
            ],
            'business_rules': [
                {'description': 'if user_age > 18: allow_checkout', 'line': 45, 'type': 'age_check'}
            ]
        },
        'checkout.py': {
            'type': 'python',
            'key_functions': [
                {'name': 'process_payment', 'line': 50, 'purpose': '💰 Processes payments'}
            ]
        }
    }
    
    # Set the orchestrator state with these analyses
    orchestrator.last_analyses = simulated_analyses
    
    print("\n📊 Simulated code analysis loaded:")
    for path, analysis in simulated_analyses.items():
        print(f"   • {path}: {len(analysis.get('key_functions', []))} functions, {len(analysis.get('business_rules', []))} rules")
    
    # Test 1: Free-text feedback with pattern matching
    print("\n" + "-"*60)
    print("TEST 1: Free-text Feedback with Pattern Matching")
    print("-"*60)
    
    feedback_msg = "function authenticate should validate email format and check for SQL injection"
    print(f"\n📝 User feedback: \"{feedback_msg}\"")
    
    result = orchestrator.ingest_feedback(feedback_msg)
    print(f"✅ Result: {result.get('summary')}")
    if result['applied']:
        print(f"\n📋 Applied {len(result['applied'])} correction(s):")
        for item in result['applied']:
            print(f"   • {item['file'].split('/')[-1]} → {item['target']}: {item['correction']}")
    
    # Test 2: Structured feedback with explicit corrections
    print("\n" + "-"*60)
    print("TEST 2: Structured Feedback with Corrections")
    print("-"*60)
    
    structured_feedback = {
        'message': 'Found issues in discount logic',
        'corrections': [
            {
                'original': 'calculate_discount',
                'corrected': 'Applies 15% discount on orders over $100',
                'type': 'function_purpose'
            },
            {
                'original': 'if user_age > 18: allow_checkout',
                'corrected': 'Only users age 18+ can purchase restricted items',
                'type': 'business_rule'
            }
        ]
    }
    
    print(f"\n📝 Structured feedback with {len(structured_feedback['corrections'])} corrections:")
    for c in structured_feedback['corrections']:
        print(f"   • {c['original']} → {c['corrected']}")
    
    result = orchestrator.ingest_feedback(
        structured_feedback['message'],
        structured_feedback
    )
    
    print(f"\n✅ Result: {result.get('summary')}")
    if result['applied']:
        print(f"\n📋 Applied {len(result['applied'])} correction(s):")
        for item in result['applied']:
            print(f"   • {item['file'].split('/')[-1]} → {item['target']}: {item['correction']}")
    
    # Test 3: Invalid feedback (no matches)
    print("\n" + "-"*60)
    print("TEST 3: Invalid/Unmatched Feedback")
    print("-"*60)
    
    invalid_feedback = "function xyz_nonexistent should do something"
    print(f"\n📝 Invalid feedback: \"{invalid_feedback}\"")
    
    result = orchestrator.ingest_feedback(invalid_feedback)
    print(f"✅ Result: {result.get('summary')}")
    if result['skipped']:
        print(f"\n⚠️ Skipped {len(result['skipped'])} unmatched item(s)")
        for item in result['skipped']:
            print(f"   • Could not match: {item.get('original')}")
    
    print("\n" + "="*60)
    print("✅ All feedback tests completed!")
    print("="*60)

def main():
    """Main entry point"""
    import sys
    
    print("\n" + "="*60)
    print(" SYSTEM TESTER")
    print("="*60)
    print("\nChoose what to test:")
    print("  1. GitHub Token (default)")
    print("  2. Feedback System")
    print("  3. Both")
    
    try:
        choice = input("\nEnter choice (1-3) or press Enter for #1: ").strip() or "1"
        
        if choice in ["1", "3"]:
            try:
                tester = GitHubTokenTester()
                tester.run_all_tests()
            except ValueError as e:
                print(f"\n❌ {e}")
                print("\n📝 To fix:")
                print("   1. Create a .env file")
                print("   2. Add: GITHUB_TOKEN=your_token_here")
                print("   3. Get token from: https://github.com/settings/tokens")
        
        if choice in ["2", "3"]:
            test_feedback_system()
            
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()