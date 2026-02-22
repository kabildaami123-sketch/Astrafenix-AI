# agents/business_translator.py
"""
Translates code analysis into business-friendly language
"""

from typing import Dict, Any, List

class BusinessTranslator:
    """
    Takes code analysis and explains what it means for the business
    """
    
    def translate(self, file_analyses: Dict[str, Any]) -> Dict[str, Any]:
        """
        Translate all file analyses into business impact
        """
        business_report = {
            'features': [],
            'user_interfaces': [],
            'business_logic': [],
            'data_management': [],
            'integrations': [],
            'security': [],
            'summary': {}
        }
        
        for file_path, analysis in file_analyses.items():
            file_type = analysis.get('type', 'unknown')
            
            # Translate based on file type
            if file_type == 'python':
                self._translate_python(analysis, business_report)
            elif file_type == 'javascript':
                self._translate_javascript(analysis, business_report)
            elif file_type == 'html':
                self._translate_html(analysis, business_report)
            elif file_type == 'css':
                self._translate_css(analysis, business_report)
            elif file_type == 'documentation':
                self._translate_docs(analysis, business_report)
        
        # Generate summary
        business_report['summary'] = self._generate_summary(business_report)
        
        return business_report
    
    def _translate_python(self, analysis: Dict, report: Dict):
        """Translate Python analysis"""
        for purpose in analysis.get('business_purpose', []):
            if 'API' in purpose:
                report['integrations'].append(purpose)
            elif 'database' in purpose.lower():
                report['data_management'].append(purpose)
            elif 'authentic' in purpose.lower():
                report['security'].append(purpose)
        
        for rule in analysis.get('business_rules', []):
            report['business_logic'].append({
                'description': rule['description'],
                'impact': 'Automates business decisions'
            })
        
        for func in analysis.get('key_functions', []):
            if 'purpose' in func:
                report['features'].append(func['purpose'])
    
    def _translate_javascript(self, analysis: Dict, report: Dict):
        """Translate JavaScript analysis"""
        for ui in analysis.get('ui_components', []):
            report['user_interfaces'].append(ui)
        
        for purpose in analysis.get('business_purpose', []):
            if 'API' in purpose:
                report['integrations'].append(purpose)
            elif 'user interaction' in purpose.lower():
                report['user_interfaces'].append(purpose)
    
    def _translate_html(self, analysis: Dict, report: Dict):
        """Translate HTML analysis"""
        for form in analysis.get('forms', []):
            report['user_interfaces'].append(form)
        
        for element in analysis.get('ui_elements', []):
            report['user_interfaces'].append(element)
    
    def _translate_css(self, analysis: Dict, report: Dict):
        """Translate CSS analysis"""
        for purpose in analysis.get('purpose', []):
            report['user_interfaces'].append(purpose)
    
    def _translate_docs(self, analysis: Dict, report: Dict):
        """Translate documentation"""
        for info in analysis.get('key_info', []):
            report['features'].append(f"📚 Documentation: {info}")
    
    def _generate_summary(self, report: Dict) -> str:
        """Generate executive summary"""
        parts = []
        
        if report['features']:
            parts.append(f"✨ {len(report['features'])} new features")
        if report['user_interfaces']:
            parts.append(f"🖥️ {len(report['user_interfaces'])} UI improvements")
        if report['business_logic']:
            parts.append(f"🧮 {len(report['business_logic'])} business rules automated")
        if report['data_management']:
            parts.append(f"💾 {len(report['data_management'])} data enhancements")
        if report['integrations']:
            parts.append(f"🔌 {len(report['integrations'])} new integrations")
        if report['security']:
            parts.append(f"🔐 {len(report['security'])} security updates")
        
        if parts:
            return "This update includes: " + ", ".join(parts) + "."
        else:
            return "Maintenance and infrastructure updates to keep your system running smoothly."