# core/orchestrator.py
"""
Main orchestrator that coordinates the entire workflow
"""

import asyncio
from datetime import datetime
from typing import Dict, Any

from github.file_downloader import GitHubFileDownloader
from agents.code_analyzer import CodeAnalyzer
from agents.business_translator import BusinessTranslator
from feedback.collector import FeedbackCollector
from models.ollama_client import OllamaClient
from utils.logger import logger
from utils.cache import cache

class BusinessReportOrchestrator:
    """
    Orchestrates the complete workflow:
    1. Download files from GitHub
    2. Analyze each file
    3. Translate to business language
    4. Generate beautiful report
    """
    
    def __init__(self):
        self.downloader = GitHubFileDownloader()
        self.analyzer = CodeAnalyzer()
        self.translator = BusinessTranslator()
        self.ollama = OllamaClient()
        self.feedback_collector = FeedbackCollector()

        # In-memory state for the last run (simple persistence)
        self.state: Dict[str, Any] = {}
        self.last_analyses: Dict[str, Any] = {}
        self.last_business_report: Dict[str, Any] = {}
    
    async def generate_report(self, repo_url: str, files_to_download: list = None):
        """
        Main method: Download files, analyze, and generate business report
        """
        logger.info(f"🚀 Starting business report generation for {repo_url}")
        start_time = datetime.now()
        
        # Step 1: Parse GitHub URL
        repo_info = self.downloader.parse_github_url(repo_url)
        logger.info(f"📦 Repository: {repo_info['owner']}/{repo_info['repo']}")
        
        # Step 2: Download files
        if not files_to_download:
            # Default important files to check
            files_to_download = [
                "README.md",
                "app.py",
                "main.py",
                "routes.py",
                "models.py",
                "templates/index.html",
                "templates/login.html",
                "static/js/main.js",
                "static/css/style.css"
            ]
        
        logger.info(f"📥 Downloading {len(files_to_download)} files...")
        async with self.downloader as downloader:
            downloaded_files = await downloader.download_multiple_files(
                repo_info['owner'],
                repo_info['repo'],
                files_to_download
            )
        
        logger.info(f"✅ Downloaded {len(downloaded_files)} files")
        
        # Step 3: Analyze each file
        logger.info("🔍 Analyzing files...")
        file_analyses = {}
        for path, file_info in downloaded_files.items():
            analysis = self.analyzer.analyze_file(file_info)
            file_analyses[path] = analysis
            logger.info(f"   ✅ Analyzed {path} - {analysis.get('type', 'unknown')}")

        # Store latest analyses for potential feedback reconciliation
        self.last_analyses = file_analyses
        
        # Step 4: Translate to business language
        logger.info("💼 Translating to business language...")
        business_report = self.translator.translate(file_analyses)

        # Keep last business report for feedback handlers
        self.last_business_report = business_report
        
        # Step 5: Generate final HTML report
        logger.info("📊 Generating business report...")
        html_report = await self._generate_html_report(
            repo_url,
            downloaded_files,
            file_analyses,
            business_report,
            start_time
        )
        
        # Step 6: Print the report (no saving)
        print("\n" + "="*80)
        print(html_report)
        print("="*80)
        
        # Also print a quick summary
        self._print_summary(business_report, len(downloaded_files), start_time)
        # Update simple state
        self.state.update({
            'repo_url': repo_url,
            'files': downloaded_files,
            'files_fetched': len(downloaded_files),
            'business_context': business_report,
            'confidence_score': business_report.get('confidence', 0.85),
            'report': html_report,
        })

        return html_report

    def ingest_feedback(self, message: str, structured: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Accept a user's feedback message (free-text) plus optional structured
        corrections, normalize via FeedbackCollector, route to the
        CodeAnalyzer for lightweight application, and persist the result.
        Returns a reconciliation summary dict.
        """
        # Normalize the incoming feedback
        feedback = self.feedback_collector.ingest_user_feedback(message, structured)

        # Process feedback against last analyses
        result = self.analyzer.process_feedback(feedback, self.last_analyses)

        # Persist feedback and result to in-memory state and cache
        self.state['feedback'] = feedback
        self.state['feedback_result'] = result
        try:
            cache.set('last_feedback', {'feedback': feedback, 'result': result}, ttl=3600)
        except Exception:
            # cache is optional — don't fail if persistence isn't available
            logger.debug('Could not persist feedback to cache')

        logger.info(f"📝 Ingested feedback: {result.get('summary')}")
        return result
    
    async def _generate_html_report(self, repo_url, files, analyses, business_report, start_time):
        """Generate beautiful HTML report"""
        
        # Count business items
        features_count = len(business_report.get('features', []))
        ui_count = len(business_report.get('user_interfaces', []))
        rules_count = len(business_report.get('business_logic', []))
        
        # Build features HTML
        features_html = ""
        for feature in business_report.get('features', [])[:5]:
            features_html += f"""
            <div class="feature-item">
                <span class="feature-icon">✨</span>
                <span>{feature}</span>
            </div>
            """
        
        # Build UI HTML
        ui_html = ""
        for ui in business_report.get('user_interfaces', [])[:5]:
            ui_html += f"""
            <div class="feature-item">
                <span class="feature-icon">🖥️</span>
                <span>{ui}</span>
            </div>
            """
        
        # Build business rules HTML
        rules_html = ""
        for rule in business_report.get('business_logic', [])[:5]:
            if isinstance(rule, dict):
                rules_html += f"""
                <div class="feature-item">
                    <span class="feature-icon">🧮</span>
                    <span><strong>Rule:</strong> {rule.get('description', '')[:100]}</span>
                </div>
                """
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>📊 Business Impact Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            background: white;
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
        }}
        .header h1 {{
            font-size: 2.5em;
            margin: 0;
            font-weight: 300;
        }}
        .header h1 strong {{
            font-weight: 700;
        }}
        .header .repo {{
            font-size: 1.2em;
            opacity: 0.9;
            margin-top: 10px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            padding: 30px;
            background: #f8fafc;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}
        .stat-label {{
            color: #666;
            font-size: 0.9em;
            margin-top: 5px;
        }}
        .section {{
            padding: 30px;
            border-bottom: 1px solid #e0e0e0;
        }}
        .section-title {{
            font-size: 1.5em;
            color: #333;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .section-title::after {{
            content: '';
            flex: 1;
            height: 2px;
            background: linear-gradient(90deg, #667eea, transparent);
        }}
        .feature-item {{
            padding: 15px;
            background: #f8fafc;
            border-radius: 8px;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 10px;
            border-left: 3px solid #667eea;
        }}
        .feature-icon {{
            font-size: 1.2em;
        }}
        .summary-box {{
            background: linear-gradient(135deg, #f5f7fa 0%, #e4e8f0 100%);
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 20px;
            font-size: 1.1em;
        }}
        .file-list {{
            background: #f8fafc;
            padding: 20px;
            border-radius: 8px;
        }}
        .file-item {{
            padding: 8px;
            border-bottom: 1px solid #e0e0e0;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .file-item:last-child {{
            border-bottom: none;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
            margin-left: 10px;
        }}
        .badge-python {{ background: #3776ab; color: white; }}
        .badge-js {{ background: #f7df1e; color: black; }}
        .badge-html {{ background: #e34c26; color: white; }}
        .badge-css {{ background: #264de4; color: white; }}
        .badge-docs {{ background: #28a745; color: white; }}
        .feedback-box {{
            background: linear-gradient(135deg, #f0f4ff 0%, #f5f0ff 100%);
            padding: 20px;
            border-radius: 8px;
            border: 2px solid #e0e4ff;
        }}
        .footer {{
            text-align: center;
            padding: 30px;
            color: #666;
            background: #f8fafc;
        }}
        .timestamp {{
            color: #999;
            font-size: 0.9em;
            margin-top: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 <strong>Business Impact</strong> Report</h1>
            <p class="repo">🔗 {repo_url}</p>
            <p class="timestamp">Generated in {processing_time:.1f} seconds</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{len(files)}</div>
                <div class="stat-label">Files Analyzed</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{features_count}</div>
                <div class="stat-label">New Features</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{ui_count}</div>
                <div class="stat-label">UI Components</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{rules_count}</div>
                <div class="stat-label">Business Rules</div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">📋 Executive Summary</div>
            <div class="summary-box">
                {business_report.get('summary', 'Analysis complete. See details below.')}
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">✨ What's New</div>
            {features_html if features_html else '<p>No new features detected in this update.</p>'}
        </div>
        
        <div class="section">
            <div class="section-title">🖥️ User Interface Updates</div>
            {ui_html if ui_html else '<p>No UI changes detected.</p>'}
        </div>
        
        <div class="section">
            <div class="section-title">🧮 Business Logic</div>
            {rules_html if rules_html else '<p>No new business rules detected.</p>'}
        </div>
        
        <div class="section">
            <div class="section-title">📁 Files Analyzed</div>
            <div class="file-list">
"""

        # Add file list
        for path, analysis in analyses.items():
            file_type = analysis.get('type', 'unknown')
            badge_class = {
                'python': 'badge-python',
                'javascript': 'badge-js',
                'html': 'badge-html',
                'css': 'badge-css',
                'documentation': 'badge-docs'
            }.get(file_type, '')
            
            html_report += f"""
                <div class="file-item">
                    <span>📄 {path}</span>
                    <span class="badge {badge_class}">{file_type}</span>
                </div>
            """
        
        html_report += f"""
            </div>
        </div>

        <div class="section">
            <div class="section-title">💬 Feedback & Improvements</div>
            <div class="feedback-box">
                <p style="color: #666; margin-bottom: 15px;">Found something inaccurate? Help us improve the analysis!</p>
                <textarea id="feedback-input" placeholder="Example: 'function calculate_discount should apply 15% discount on orders over $100'&#10;&#10;Or list specific corrections like:&#10;- function_name: new_or_corrected_purpose&#10;- another_function: fixed_description" style="width: 100%; height: 120px; padding: 10px; border: 1px solid #ddd; border-radius: 5px; font-family: monospace; font-size: 0.9em;"></textarea>
                <button id="submit-feedback-btn" onclick="submitFeedback()" style="margin-top: 10px; padding: 10px 20px; background: #667eea; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;">Submit Feedback</button>
                <div id="feedback-status" style="margin-top: 10px; color: #666; font-size: 0.9em;"></div>
            </div>
        </div>

        <div class="footer">
            <p>🤖 Generated by AI Agents • DeepSeek + Ollama</p>
            <p>This report translates code changes into business value</p>
            <p style="font-size: 0.85em; color: #999; margin-top: 10px;">💡 Tip: Use the feedback box above to help us improve future analyses!</p>
        </div>
    </div>

    <script>
        function submitFeedback() {{
            const feedbackText = document.getElementById('feedback-input').value.trim();
            const statusDiv = document.getElementById('feedback-status');
            
            if (!feedbackText) {{
                statusDiv.textContent = '⚠️ Please enter feedback before submitting.';
                statusDiv.style.color = '#ff9800';
                return;
            }}
            
            statusDiv.textContent = '📤 Submitting feedback...';
            statusDiv.style.color = '#667eea';
            
            // In a real app, this would POST to your backend
            // For now, show instructions
            setTimeout(() => {{
                statusDiv.innerHTML = '✅ Feedback captured! Pass this to the code analyzer:<br><code style="background: #f0f0f0; padding: 5px; display: block; margin-top: 5px; word-break: break-all;">' + feedbackText + '</code>';
                statusDiv.style.color = '#4caf50';
            }}, 500);
        }}
    </script>
</body>
</html>
"""
    
    def _print_summary(self, business_report, files_count, start_time):
        """Print a quick console summary"""
        processing_time = (datetime.now() - start_time).total_seconds()
        
        print("\n" + "="*60)
        print("📊 BUSINESS IMPACT SUMMARY")
        print("="*60)
        print(f"📁 Files analyzed: {files_count}")
        print(f"⏱️  Processing time: {processing_time:.1f}s")
        print("\n✨ Key Business Impact:")
        
        for feature in business_report.get('features', [])[:3]:
            print(f"   • {feature}")
        for ui in business_report.get('user_interfaces', [])[:3]:
            print(f"   • {ui}")
        for rule in business_report.get('business_logic', [])[:3]:
            if isinstance(rule, dict):
                print(f"   • {rule.get('description', '')[:80]}")
        
        print("\n" + "="*60)
    # In core/orchestrator.py, update the generate_report method:

async def generate_report(self, repo_url: str, files_to_download: list = None):
    """
    Main method: Download files, analyze, and generate business report
    """
    logger.info(f"🚀 Starting business report generation for {repo_url}")
    start_time = datetime.now()
    
    # ... (existing download and analysis code remains the same)
    
    # After analysis, prepare metadata for report
    file_details = {}
    for path, analysis in file_analyses.items():
        file_details[path] = analysis.get('type', 'unknown')
    
    metadata = {
        'repo_url': repo_url,
        'files_fetched': len(downloaded_files),
        'total_files': len(files_to_download),
        'processing_time': (datetime.now() - start_time).total_seconds(),
        'api_calls': self.downloader.api_calls,
        'cache_hits': 0,  # You can track this if needed
        'confidence': business_report.get('confidence', 0.85),
        'file_details': file_details
    }
    
    # Generate text report
    logger.info("📊 Generating text business report...")
    text_report = await self.report_agent.generate(business_report, metadata)
    
    # Print the beautiful text report
    print("\n" + "="*80)
    print(text_report['text'])
    print("="*80)
    
    # Also print quick summary
    self._print_summary(text_report, len(downloaded_files), start_time)
    
    return text_report