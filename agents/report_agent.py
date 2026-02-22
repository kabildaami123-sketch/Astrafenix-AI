# agents/report_agent.py
"""
Agent 2: Generates detailed text-based business reports
"""

from typing import Dict, Any, List
from datetime import datetime
import textwrap

from models.ollama_client import OllamaClient
from utils.logger import logger

class ReportGeneratorAgent:
    """
    Generates detailed text-based business reports
    """
    
    def __init__(self):
        self.ollama = OllamaClient()
        
    async def generate(self, business_context: Dict, metadata: Dict) -> Dict[str, Any]:
        """
        Generate detailed text report from business context
        """
        logger.info("🤖 Agent 2: Generating text business report...")
        
        # Translate technical findings to business language
        business_translation = self._translate_to_business(business_context)
        
        # Generate narrative with Ollama
        async with self.ollama as client:
            narrative = await client.generate_business_narrative(
                business_translation,
                metadata.get('report_type', 'sprint')
            )
        
        # Create the text report
        text_report = self._create_text_report(
            business_translation,
            narrative,
            metadata
        )
        
        logger.info("✅ Agent 2: Text report generated!")
        
        return {
            'text': text_report,
            'summary': narrative.get('executive_summary', ''),
            'features_count': len(business_translation.get('features', [])),
            'rules_count': len(business_translation.get('business_rules', []))
        }
    
    def _translate_to_business(self, context: Dict) -> Dict[str, Any]:
        """
        Translate technical findings to business language
        """
        business = {
            'features': [],
            'improvements': [],
            'security': [],
            'infrastructure': [],
            'business_rules': [],
            'ui_components': []
        }
        
        # Translate business rules
        for rule in context.get('business_rules', []):
            rule_type = rule.get('type', '')
            description = rule.get('description', '')
            
            if 'validation' in rule_type:
                business['business_rules'].append({
                    'title': '✅ Data Validation',
                    'description': description,
                    'impact': 'Ensures data quality and prevents errors'
                })
            elif 'pricing' in rule_type or 'calculation' in rule_type:
                business['business_rules'].append({
                    'title': '💰 Pricing Logic',
                    'description': description,
                    'impact': 'Automates financial calculations'
                })
            elif 'access' in rule_type or 'authentication' in rule_type:
                business['security'].append({
                    'title': '🔐 Access Control',
                    'description': description,
                    'impact': 'Protects sensitive business data'
                })
        
        # Translate routes/endpoints
        for route in context.get('routes', []):
            route_path = route.get('route', '')
            if 'login' in route_path.lower():
                business['features'].append({
                    'title': '🔑 Customer Login Portal',
                    'description': 'Secure authentication system for users',
                    'impact': 'Enables personalized user experiences'
                })
            elif 'checkout' in route_path.lower() or 'payment' in route_path.lower():
                business['features'].append({
                    'title': '🛒 Checkout Process',
                    'description': 'Shopping cart and payment flow',
                    'impact': 'Enables revenue generation'
                })
            elif 'api' in route_path.lower():
                business['infrastructure'].append({
                    'title': '🔌 API Integration Points',
                    'description': f'REST endpoints at {route_path}',
                    'impact': 'Allows third-party integrations'
                })
        
        # Translate database operations
        for db_call in context.get('database_calls', []):
            if 'user' in db_call.get('function', '').lower():
                business['infrastructure'].append({
                    'title': '👥 User Data Management',
                    'description': 'Customer information storage',
                    'impact': 'Securely stores user data'
                })
            elif 'order' in db_call.get('function', '').lower():
                business['features'].append({
                    'title': '📦 Order Processing',
                    'description': 'Order management system',
                    'impact': 'Tracks customer purchases'
                })
        
        # Translate UI components from file analysis
        for file_analysis in context.get('file_analyses', []):
            if file_analysis.get('type') == 'html':
                for form in file_analysis.get('forms', []):
                    business['ui_components'].append(form)
                for element in file_analysis.get('ui_elements', []):
                    business['ui_components'].append(element)
        
        return business
    
    def _create_text_report(self, translation: Dict, narrative: Dict, metadata: Dict) -> str:
        """
        Create a beautiful, detailed text report
        """
        lines = []
        
        # Header
        lines.append("=" * 80)
        lines.append("📊 BUSINESS IMPACT REPORT - DETAILED ANALYSIS")
        lines.append("=" * 80)
        lines.append(f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
        lines.append(f"Repository: {metadata.get('repo_url', 'N/A')}")
        lines.append(f"Files Analyzed: {metadata.get('files_fetched', 0)}")
        lines.append(f"Analysis Confidence: {metadata.get('confidence', 0)*100:.1f}%")
        lines.append("=" * 80)
        lines.append("")
        
        # Executive Summary
        lines.append("📋 EXECUTIVE SUMMARY")
        lines.append("-" * 40)
        summary = narrative.get('executive_summary', 'Analysis complete. See details below.')
        # Wrap text to 80 characters
        wrapped_summary = textwrap.fill(summary, width=76)
        lines.append(wrapped_summary)
        lines.append("")
        
        # Key Metrics
        lines.append("📊 KEY METRICS")
        lines.append("-" * 40)
        lines.append(f"• Total Features: {len(translation.get('features', []))}")
        lines.append(f"• Business Rules: {len(translation.get('business_rules', []))}")
        lines.append(f"• UI Components: {len(translation.get('ui_components', []))}")
        lines.append(f"• Security Updates: {len(translation.get('security', []))}")
        lines.append(f"• API Integrations: {len(translation.get('infrastructure', []))}")
        lines.append("")
        
        # New Features
        if translation.get('features'):
            lines.append("✨ NEW FEATURES")
            lines.append("-" * 40)
            for i, feature in enumerate(translation['features'], 1):
                lines.append(f"{i}. {feature.get('title', 'New Feature')}")
                # Indent and wrap description
                desc = textwrap.fill(feature.get('description', ''), width=74, initial_indent='   ', subsequent_indent='   ')
                lines.append(desc)
                impact = textwrap.fill(f"Impact: {feature.get('impact', '')}", width=74, initial_indent='   ', subsequent_indent='   ')
                lines.append(impact)
                lines.append("")
        
        # Business Rules
        if translation.get('business_rules'):
            lines.append("🧮 BUSINESS RULES DETECTED")
            lines.append("-" * 40)
            for i, rule in enumerate(translation['business_rules'], 1):
                lines.append(f"{i}. {rule.get('title', 'Business Rule')}")
                desc = textwrap.fill(rule.get('description', ''), width=74, initial_indent='   ', subsequent_indent='   ')
                lines.append(desc)
                impact = textwrap.fill(f"Impact: {rule.get('impact', '')}", width=74, initial_indent='   ', subsequent_indent='   ')
                lines.append(impact)
                lines.append("")
        
        # UI Components
        if translation.get('ui_components'):
            lines.append("🖥️ USER INTERFACE COMPONENTS")
            lines.append("-" * 40)
            for i, ui in enumerate(translation['ui_components'][:10], 1):  # Show first 10
                lines.append(f"{i}. {ui}")
            if len(translation['ui_components']) > 10:
                lines.append(f"   ... and {len(translation['ui_components']) - 10} more")
            lines.append("")
        
        # Security Updates
        if translation.get('security'):
            lines.append("🔐 SECURITY UPDATES")
            lines.append("-" * 40)
            for i, security in enumerate(translation['security'], 1):
                lines.append(f"{i}. {security.get('title', 'Security Update')}")
                desc = textwrap.fill(security.get('description', ''), width=74, initial_indent='   ', subsequent_indent='   ')
                lines.append(desc)
                impact = textwrap.fill(f"Impact: {security.get('impact', '')}", width=74, initial_indent='   ', subsequent_indent='   ')
                lines.append(impact)
                lines.append("")
        
        # Infrastructure/Integrations
        if translation.get('infrastructure'):
            lines.append("🔌 INTEGRATIONS & INFRASTRUCTURE")
            lines.append("-" * 40)
            for i, infra in enumerate(translation['infrastructure'], 1):
                lines.append(f"{i}. {infra.get('title', 'Integration')}")
                desc = textwrap.fill(infra.get('description', ''), width=74, initial_indent='   ', subsequent_indent='   ')
                lines.append(desc)
                impact = textwrap.fill(f"Impact: {infra.get('impact', '')}", width=74, initial_indent='   ', subsequent_indent='   ')
                lines.append(impact)
                lines.append("")
        
        # Next Steps (from narrative)
        if narrative.get('next_steps'):
            lines.append("🚀 RECOMMENDED NEXT STEPS")
            lines.append("-" * 40)
            for i, step in enumerate(narrative['next_steps'], 1):
                lines.append(f"{i}. {step}")
            lines.append("")
        
        # File Analysis Summary
        if metadata.get('file_details'):
            lines.append("📁 FILES ANALYZED")
            lines.append("-" * 40)
            for file_path, file_type in metadata['file_details'].items():
                type_icon = {
                    'python': '🐍',
                    'html': '🌐',
                    'javascript': '📜',
                    'css': '🎨',
                    'documentation': '📚'
                }.get(file_type, '📄')
                lines.append(f"  {type_icon} {file_path}")
            lines.append("")
        
        # Performance Metrics
        lines.append("⚡ PERFORMANCE METRICS")
        lines.append("-" * 40)
        lines.append(f"• Processing Time: {metadata.get('processing_time', 0):.2f} seconds")
        lines.append(f"• GitHub API Calls: {metadata.get('api_calls', 0)}")
        lines.append(f"• Cache Hits: {metadata.get('cache_hits', 0)}")
        lines.append(f"• Sampling Rate: {metadata.get('files_fetched', 0)}/{metadata.get('total_files', 0)} files")
        lines.append("")
        
        # Footer
        lines.append("=" * 80)
        lines.append("✨ Report generated by AI Agents • DeepSeek + Ollama")
        lines.append("=" * 80)
        
        return "\n".join(lines)