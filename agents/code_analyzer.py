# agents/code_analyzer.py
"""
Analyzes downloaded code files to extract business meaning
"""

import re
from typing import Dict, Any, List

from utils.logger import logger

class CodeAnalyzer:
    """
    Analyzes code files to understand what they do for the business
    """
    
    def analyze_file(self, file_info: Dict) -> Dict[str, Any]:
        """
        Analyze a single downloaded file
        """
        content = file_info['content']
        file_path = file_info['path']
        file_name = file_info['name']
        
        # Determine file type
        if file_path.endswith('.py'):
            return self._analyze_python(content, file_name)
        elif file_path.endswith('.js') or file_path.endswith('.jsx'):
            return self._analyze_javascript(content, file_name)
        elif file_path.endswith('.html'):
            return self._analyze_html(content, file_name)
        elif file_path.endswith('.css'):
            return self._analyze_css(content, file_name)
        elif file_path.endswith('.md') or file_path.endswith('.txt'):
            return self._analyze_documentation(content, file_name)
        else:
            return self._analyze_generic(content, file_name)
    
    def _analyze_python(self, content: str, file_name: str) -> Dict[str, Any]:
        """
        Analyze Python files - find business logic
        """
        analysis = {
            'type': 'python',
            'file': file_name,
            'business_purpose': [],
            'key_functions': [],
            'business_rules': []
        }
        
        lines = content.split('\n')
        
        # Look for business indicators
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            # Find function definitions
            if line.strip().startswith('def '):
                func_name = line.split('def ')[1].split('(')[0].strip()
                analysis['key_functions'].append({
                    'name': func_name,
                    'line': i + 1,
                    'purpose': self._guess_function_purpose(func_name, line)
                })
            
            # Find business rules (if statements with business terms)
            if 'if ' in line_lower and any(term in line_lower for term in ['user', 'price', 'total', 'discount', 'email', 'age', 'role']):
                analysis['business_rules'].append({
                    'type': 'business_rule',
                    'description': line.strip(),
                    'line': i + 1
                })
            
            # Find database operations
            if any(db in line_lower for db in ['db.', 'query', 'session.', 'cursor']):
                analysis['business_purpose'].append(f"Database operation: {line.strip()}")
            
            # Find API endpoints (Flask/FastAPI routes)
            if '@app.route' in line or '@api.route' in line:
                analysis['business_purpose'].append(f"API endpoint: {line.strip()}")
            
            # Find authentication
            if 'login' in line_lower or 'authenticate' in line_lower:
                analysis['business_purpose'].append(f"Authentication: {line.strip()}")
        
        return analysis
    
    def _analyze_javascript(self, content: str, file_name: str) -> Dict[str, Any]:
        """
        Analyze JavaScript files
        """
        analysis = {
            'type': 'javascript',
            'file': file_name,
            'business_purpose': [],
            'key_functions': [],
            'ui_components': []
        }
        
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            # Find functions
            if 'function ' in line_lower or '=>' in line:
                analysis['key_functions'].append({
                    'name': line.strip()[:50],
                    'line': i + 1
                })
            
            # Find UI components (React)
            if 'return (' in line and ('<' in line):
                analysis['ui_components'].append(f"UI Component at line {i+1}")
            
            # Find API calls
            if 'fetch(' in line_lower or 'axios.' in line_lower:
                analysis['business_purpose'].append(f"API call: {line.strip()}")
            
            # Find user interactions
            if 'onclick' in line_lower or 'onsubmit' in line_lower:
                analysis['business_purpose'].append(f"User interaction: {line.strip()}")
        
        return analysis
    
    def _analyze_html(self, content: str, file_name: str) -> Dict[str, Any]:
        """
        Analyze HTML files - find user interface elements
        """
        analysis = {
            'type': 'html',
            'file': file_name,
            'ui_elements': [],
            'forms': [],
            'business_purpose': []
        }
        
        # Look for forms (data collection)
        form_matches = re.findall(r'<form.*?</form>', content, re.DOTALL)
        for form in form_matches:
            # Check what kind of form
            if 'login' in form.lower() or 'signin' in form.lower():
                analysis['forms'].append("🔑 Login form - collects user credentials")
                analysis['business_purpose'].append("User authentication interface")
            elif 'register' in form.lower() or 'signup' in form.lower():
                analysis['forms'].append("📝 Registration form - collects new user data")
                analysis['business_purpose'].append("New user signup interface")
            elif 'checkout' in form.lower() or 'payment' in form.lower():
                analysis['forms'].append("💰 Checkout form - collects payment information")
                analysis['business_purpose'].append("Payment processing interface")
            elif 'contact' in form.lower():
                analysis['forms'].append("📧 Contact form - collects user messages")
                analysis['business_purpose'].append("Customer communication interface")
        
        # Look for buttons (user actions)
        button_matches = re.findall(r'<button.*?</button>', content, re.DOTALL)
        for button in button_matches:
            button_text = re.search(r'>(.*?)<', button)
            if button_text:
                text = button_text.group(1).lower()
                if 'login' in text:
                    analysis['ui_elements'].append("🔑 Login button - lets users access accounts")
                elif 'buy' in text or 'purchase' in text or 'checkout' in text:
                    analysis['ui_elements'].append("🛒 Purchase button - completes transactions")
                elif 'submit' in text:
                    analysis['ui_elements'].append("📤 Submit button - sends data")
                elif 'search' in text:
                    analysis['ui_elements'].append("🔍 Search button - finds content")
        
        return analysis
    
    def _analyze_css(self, content: str, file_name: str) -> Dict[str, Any]:
        """
        Analyze CSS files - find styling and layout
        """
        analysis = {
            'type': 'css',
            'file': file_name,
            'purpose': [],
            'components': []
        }
        
        # Look for component styling
        if 'button' in content.lower():
            analysis['components'].append("Button styling - consistent look for all buttons")
        if 'form' in content.lower():
            analysis['components'].append("Form styling - professional form appearance")
        if 'navbar' in content.lower() or 'header' in content.lower():
            analysis['components'].append("Navigation styling - easy site navigation")
        if 'card' in content.lower():
            analysis['components'].append("Card styling - beautiful content presentation")
        
        # Check for responsive design
        if '@media' in content:
            analysis['purpose'].append("📱 Responsive design - works on mobile and desktop")
        
        return analysis
    
    def _analyze_documentation(self, content: str, file_name: str) -> Dict[str, Any]:
        """
        Analyze documentation files
        """
        analysis = {
            'type': 'documentation',
            'file': file_name,
            'purpose': [],
            'key_info': []
        }
        
        first_lines = content.split('\n')[:10]
        for line in first_lines:
            if '# ' in line or '## ' in line:
                analysis['key_info'].append(line.strip())
        
        if 'setup' in content.lower() or 'install' in content.lower():
            analysis['purpose'].append("📚 Setup instructions for developers")
        if 'api' in content.lower():
            analysis['purpose'].append("🔌 API documentation - how to integrate")
        if 'contribut' in content.lower():
            analysis['purpose'].append("🤝 Contribution guidelines for team")
        
        return analysis
    
    def _analyze_generic(self, content: str, file_name: str) -> Dict[str, Any]:
        """
        Generic analysis for unknown file types
        """
        lines = len(content.split('\n'))
        return {
            'type': 'unknown',
            'file': file_name,
            'size_lines': lines,
            'note': f"File with {lines} lines - may contain configuration or data"
        }
    
    def _guess_function_purpose(self, func_name: str, func_line: str) -> str:
        """
        Guess what a function does for the business
        """
        name_lower = func_name.lower()
        
        if 'login' in name_lower or 'authenticate' in name_lower:
            return "🔐 Handles user login - secures access"
        elif 'checkout' in name_lower or 'purchase' in name_lower:
            return "💰 Processes payments - generates revenue"
        elif 'calculate' in name_lower or 'compute' in name_lower:
            return "🧮 Performs business calculations - automates math"
        elif 'validate' in name_lower or 'check' in name_lower:
            return "✅ Validates data - ensures quality"
        elif 'send' in name_lower and 'email' in name_lower:
            return "📧 Sends emails - communicates with customers"
        elif 'save' in name_lower or 'store' in name_lower:
            return "💾 Saves data - persists information"
        elif 'get' in name_lower or 'fetch' in name_lower or 'load' in name_lower:
            return "📤 Retrieves data - displays information"
        elif 'delete' in name_lower or 'remove' in name_lower:
            return "🗑️ Removes data - manages records"
        elif 'update' in name_lower or 'edit' in name_lower:
            return "✏️ Updates information - keeps data current"
        elif 'search' in name_lower or 'find' in name_lower:
            return "🔍 Searches content - helps users find things"
        
        return f"Function {func_name} - check code for details"

    def process_feedback(self, feedback: Dict[str, Any], analyses: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Accept structured feedback or free-text and apply lightweight corrections
        to the provided analyses. This is intentionally simple: it records
        corrections and returns a short reconciliation result that higher-level
        orchestrator code can persist or display.
        """
        result = {
            'applied': [],
            'skipped': [],
            'summary': ''
        }

        if analyses is None:
            analyses = {}

        # Prefer explicit corrections payload
        corrections = feedback.get('corrections') or []

        # If the feedback is a free-text message, try to extract simple patterns
        if not corrections and isinstance(feedback.get('message'), str):
            msg = feedback.get('message')
            # Very small heuristic: look for "function <name> -> <purpose>" patterns
            import re
            matches = re.findall(r'function\s+(\w+)\s*[:\-]>?\s*([\w\s]+)', msg, re.IGNORECASE)
            for m in matches:
                corrections.append({'original': m[0], 'corrected': m[1].strip(), 'type': 'function_purpose'})

        # Apply corrections into analyses: try to match by function name or rule text
        for c in corrections:
            applied = False
            orig = c.get('original', '')
            corrected = c.get('corrected', '')

            # Try to update function purposes
            for path, analysis in analyses.items():
                funcs = analysis.get('key_functions', [])
                for f in funcs:
                    # match by name either exact or substring
                    if orig and (orig == f.get('name') or orig in f.get('name')):
                        # attach an override
                        f.setdefault('feedback_overrides', []).append({'corrected_purpose': corrected})
                        result['applied'].append({'file': path, 'target': f.get('name'), 'correction': corrected})
                        applied = True
                        break
                if applied:
                    break

            # If not applied to functions, try business_rules
            if not applied:
                for path, analysis in analyses.items():
                    rules = analysis.get('business_rules', [])
                    for r in rules:
                        if orig and (orig in r.get('description', '') or orig == r.get('description')):
                            r.setdefault('feedback_overrides', []).append({'corrected': corrected})
                            result['applied'].append({'file': path, 'target': 'business_rule', 'correction': corrected})
                            applied = True
                            break
                    if applied:
                        break

            if not applied:
                # Nothing matched — record skipped for manual review
                result['skipped'].append(c)

        # Build a human summary
        applied_n = len(result['applied'])
        skipped_n = len(result['skipped'])
        result['summary'] = f"Applied {applied_n} correction(s); {skipped_n} unhandled."

        return result