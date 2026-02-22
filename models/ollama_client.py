"""
Ollama client for report generation using local LLM models
"""

import aiohttp
import json
import re
from typing import Dict, Any, Optional, List

from core.config import config
from utils.logger import logger

class OllamaClient:
    """
    Ollama client for rich report generation
    Uses llama3.1:8b for narrative generation
    """
    
    def __init__(self):
        """Initialize the Ollama client with settings from config"""
        self.base_url = config.OLLAMA_URL
        self.model = config.OLLAMA_MODEL
        self.session: Optional[aiohttp.ClientSession] = None
        logger.info(f"🦙 OllamaClient initialized with URL: {self.base_url}, Model: {self.model}")
        
    async def __aenter__(self):
        """Enter async context manager"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager"""
        if self.session:
            await self.session.close()
    
    async def generate_narrative(self, business_context: Dict, report_type: str) -> Dict[str, str]:
        """
        Generate rich narrative for report sections
        
        Args:
            business_context: The analyzed business context from Agent 1
            report_type: Type of report (sprint, milestone, kickoff)
            
        Returns:
            Dictionary with narrative sections
        """
        # Prepare context summary for Ollama
        context_summary = self._prepare_context_summary(business_context)
        
        prompt = f"""You are a client-friendly report writer for a software agency.
        
Generate a professional, warm narrative for a {report_type} report based on this technical analysis:

{context_summary}

Create 3 sections:
1. EXECUTIVE_SUMMARY: A 2-3 sentence overview for executives (focus on business value)
2. KEY_ACHIEVEMENTS: 3-4 bullet points of what was accomplished (business-focused, not technical)
3. NEXT_STEPS: 2-3 recommended next steps (what should happen next)

Make it:
- Professional but warm and engaging
- Focus on business value, not technical details
- Positive and confident tone
- Concise (max 250 words total)

Return as JSON with these exact keys:
- executive_summary (string)
- key_achievements (array of strings)
- next_steps (array of strings)
"""

        try:
            logger.info(f"🦙 Sending request to Ollama for {report_type} report...")
            
            async with self.session.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.7,
                    "max_tokens": 800
                }
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    response_text = result.get('response', '')
                    
                    logger.info("✅ Ollama response received")
                    
                    # Extract JSON from response
                    try:
                        # Try to find JSON in the response
                        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                        if json_match:
                            parsed = json.loads(json_match.group())
                            logger.info(f"✅ Successfully parsed JSON response")
                            return parsed
                        else:
                            logger.warning("⚠️ No JSON found in response, parsing text")
                            return self._parse_text_response(response_text)
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Failed to parse JSON: {e}")
                        return self._parse_text_response(response_text)
                else:
                    error_text = await resp.text()
                    logger.error(f"❌ Ollama API error: {resp.status} - {error_text[:200]}")
                    return self._fallback_narrative(business_context)
                    
        except aiohttp.ClientConnectorError:
            logger.error(f"❌ Cannot connect to Ollama at {self.base_url}")
            logger.error("   Make sure Ollama is running with: ollama serve")
            return self._fallback_narrative(business_context)
        except Exception as e:
            logger.error(f"❌ Ollama client error: {e}")
            return self._fallback_narrative(business_context)
    
    def _prepare_context_summary(self, context: Dict) -> str:
        """
        Prepare business context for Ollama in a readable format
        """
        # Extract key information
        files_analyzed = context.get('files_analyzed', 0)
        total_files = context.get('total_files', 0)
        rules = context.get('business_rules', [])
        confidence = context.get('confidence', 0) * 100
        
        # Get language breakdown
        languages = context.get('languages', {})
        lang_str = ", ".join([f"{ext}: {count}" for ext, count in list(languages.items())[:5]])
        
        # Build summary
        summary = f"""
PROJECT STATISTICS:
- Files Analyzed: {files_analyzed}/{total_files} ({files_analyzed/total_files*100:.1f}% coverage)
- Business Rules Found: {len(rules)}
- Analysis Confidence: {confidence:.1f}%
- Languages: {lang_str or 'Various'}
"""
        
        # Add sample business rules
        if rules:
            summary += "\nKEY BUSINESS RULES FOUND:\n"
            for i, rule in enumerate(rules[:5], 1):
                rule_type = rule.get('type', 'business_rule')
                desc = rule.get('description', '')[:100]
                summary += f"{i}. [{rule_type}] {desc}\n"
        
        # Add security info
        security_issues = context.get('security_issues', 0)
        if security_issues > 0:
            summary += f"\n⚠️ Security Issues Detected: {security_issues}\n"
        else:
            summary += "\n✅ No security issues detected\n"
        
        return summary
    
    def _parse_text_response(self, text: str) -> Dict:
        """
        Parse non-JSON response into structured format
        """
        lines = text.split('\n')
        
        narrative = {
            'executive_summary': '',
            'key_achievements': [],
            'next_steps': []
        }
        
        current_section = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect sections
            upper_line = line.upper()
            if 'EXECUTIVE' in upper_line or 'SUMMARY' in upper_line:
                current_section = 'executive'
            elif 'ACHIEVEMENT' in upper_line:
                current_section = 'achievements'
            elif 'NEXT' in upper_line or 'STEPS' in upper_line:
                current_section = 'steps'
            elif current_section == 'executive' and not narrative['executive_summary']:
                narrative['executive_summary'] = line
            elif current_section == 'achievements' and line.startswith(('-', '•', '*', '1.', '2.')):
                clean_line = line.lstrip('-•* 123456789.').strip()
                if clean_line:
                    narrative['key_achievements'].append(clean_line)
            elif current_section == 'steps' and line.startswith(('-', '•', '*', '1.', '2.')):
                clean_line = line.lstrip('-•* 123456789.').strip()
                if clean_line:
                    narrative['next_steps'].append(clean_line)
        
        # Ensure we have at least something
        if not narrative['executive_summary']:
            narrative['executive_summary'] = "Analysis completed successfully."
        if not narrative['key_achievements']:
            narrative['key_achievements'] = ["Code analysis completed", "Business rules extracted", "Report generated"]
        if not narrative['next_steps']:
            narrative['next_steps'] = ["Review the findings", "Provide feedback", "Run additional analyses"]
        
        return narrative
    
    def _fallback_narrative(self, context: Dict) -> Dict:
        """
        Fallback when Ollama is unavailable
        """
        files = context.get('files_analyzed', 0)
        total = context.get('total_files', 0)
        rules_count = len(context.get('business_rules', []))
        confidence = context.get('confidence', 0) * 100
        
        return {
            'executive_summary': f"Analysis complete on {files}/{total} files with {confidence:.0f}% confidence. Found {rules_count} business rules and potential insights for your project.",
            'key_achievements': [
                f"Successfully analyzed {files} source files",
                f"Identified {rules_count} business rules and logic patterns",
                f"Achieved {confidence:.0f}% confidence in analysis accuracy",
                "Generated comprehensive report with key findings"
            ],
            'next_steps': [
                "Review the detailed findings in the report",
                "Provide feedback to improve future analyses",
                "Run analysis on additional files for broader coverage",
                "Schedule a demo to discuss the results"
            ]
        }
    
    async def test_connection(self) -> bool:
        """
        Test if Ollama is reachable
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        models = data.get('models', [])
                        logger.info(f"✅ Ollama connection successful. Available models: {[m['name'] for m in models]}")
                        return True
                    else:
                        logger.error(f"❌ Ollama returned status {resp.status}")
                        return False
        except Exception as e:
            logger.error(f"❌ Cannot connect to Ollama: {e}")
            return False
    async def generate_business_narrative(self, business_translation: Dict, changes: List, report_type: str) -> Dict:
        """
        Generate business-friendly narrative from technical changes
        """
        
        # Prepare a business-focused summary of what changed
        changes_summary = ""
        for change in changes[:3]:
            changes_summary += f"- {change.get('description', '')}: {change.get('business_value', '')}\n"
        
        features_summary = ""
        for feature in business_translation.get('features', [])[:3]:
            features_summary += f"- {feature.get('title', '')}: {feature.get('business_value', '')}\n"
        
        prompt = f"""You are a Business Analyst translating technical updates into business value.

    Based on this development update, write a brief, enthusiastic summary for business stakeholders:

    KEY CHANGES:
    {changes_summary}

    NEW FEATURES:
    {features_summary}

    Write a short paragraph (2-3 sentences) that:
    1. Starts with an exciting headline about what was accomplished
    2. Explains the business benefit in plain language
    3. Ends with what this means for the business

    Make it sound like a product update email - professional but warm and exciting.

    Return ONLY the paragraph, no JSON, no labels.
    """

        try:
            async with self.session.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.7,
                    "max_tokens": 200
                }
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    narrative = result.get('response', '').strip()
                    
                    return {
                        'executive_summary': narrative,
                        'headline': narrative.split('.')[0] + '.' if '.' in narrative else narrative
                    }
        except Exception as e:
            logger.error(f"Ollama error: {e}")
        
        # Fallback
        return {
            'executive_summary': "This update brings new features and improvements to enhance your business operations.",
            'headline': "Exciting New Updates for Your Platform"
        }
    # models/ollama_client.py - Add this method

async def generate_business_narrative(self, business_translation: Dict, report_type: str) -> Dict:
    """
    Generate business-friendly narrative for text report
    """
    
    # Count items for summary
    features_count = len(business_translation.get('features', []))
    rules_count = len(business_translation.get('business_rules', []))
    ui_count = len(business_translation.get('ui_components', []))
    
    prompt = f"""You are a Business Analyst writing a summary for business stakeholders.

Based on this development update, write a brief, professional summary:

Project Statistics:
- New Features: {features_count}
- Business Rules: {rules_count}
- UI Components: {ui_count}

Write a concise 2-3 sentence executive summary that:
1. Highlights the main business value delivered
2. Mentions key improvements
3. Sounds professional and confident

Return ONLY the summary paragraph, no labels, no JSON.
"""

    try:
        async with self.session.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.7,
                "max_tokens": 200
            }
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                summary = result.get('response', '').strip()
                
                # Generate some default next steps
                next_steps = [
                    "Review the new features in a staging environment",
                    "Provide feedback to the development team",
                    "Schedule a demo to see the changes in action",
                    "Plan the next sprint based on these updates"
                ]
                
                return {
                    'executive_summary': summary,
                    'next_steps': next_steps[:3]  # Return first 3
                }
    except Exception as e:
        logger.error(f"Ollama error: {e}")
    
    # Fallback
    return {
        'executive_summary': f"This update adds {features_count} new features and {rules_count} business rules to enhance your platform.",
        'next_steps': [
            "Review the changes in detail",
            "Test the new functionality",
            "Provide feedback for improvements"
        ]
    }