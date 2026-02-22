import ast
import re
from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime

from models.deepseek_client import DeepSeekClient
from utils.logger import logger

class CodeUnderstandingAgent:
    """
    Agent 1: Deep code understanding with AST parsing
    """
    
    def __init__(self):
        self.deepseek = DeepSeekClient()
        
    async def analyze_batch(self, files: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze files with REAL code navigation using AST
        """
        logger.info(f"🤖 Agent 1: Starting deep code analysis on {len(files)} files")
        
        all_analyses = []
        
        for path, file_info in files.items():
            content = file_info['content']
            ext = file_info['extension']
            
            # STEP 1: Parse code structure (AST for Python, regex for others)
            structure = self._parse_code_structure(content, ext, path)
            
            # STEP 2: Use DeepSeek for deep understanding
            async with self.deepseek as client:
                deep_analysis = await client.analyze_code(
                    content, path, ext
                )
            
            # Combine structural + deep analysis
            analysis = {
                'file': path,
                'extension': ext,
                'structure': structure,
                'deep': deep_analysis
            }
            all_analyses.append(analysis)
            
            # Log progress
            logger.info(f"  ✅ Analyzed {path} - Found {len(structure.get('functions', []))} functions, {len(structure.get('business_rules', []))} business rules")
        
        # Merge all analyses
        return self._merge_analyses(all_analyses)
    
    def _parse_code_structure(self, content: str, ext: str, file_path: str) -> Dict[str, Any]:
        """
        Parse code structure using appropriate parser
        """
        if ext == '.py':
            return self._parse_python(content, file_path)
        elif ext in ['.js', '.jsx', '.ts']:
            return self._parse_javascript(content, file_path)
        elif ext == '.html':
            return self._parse_html(content, file_path)
        else:
            return self._parse_generic(content, file_path)
    
    def _parse_python(self, content: str, file_path: str) -> Dict[str, Any]:
        """
        Parse Python code using AST (Abstract Syntax Tree)
        This is REAL code navigation!
        """
        structure = {
            'imports': [],
            'classes': [],
            'functions': [],
            'routes': [],
            'database_calls': [],
            'business_rules': [],
            'decorators': [],
            'variables': [],
            'calls': []
        }
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                # Track imports
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        structure['imports'].append({
                            'module': alias.name,
                            'alias': alias.asname,
                            'line': node.lineno
                        })
                
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        structure['imports'].append({
                            'module': node.module,
                            'name': alias.name,
                            'alias': alias.asname,
                            'line': node.lineno
                        })
                
                # Track classes
                elif isinstance(node, ast.ClassDef):
                    methods = []
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            methods.append(item.name)
                    
                    structure['classes'].append({
                        'name': node.name,
                        'line': node.lineno,
                        'methods': methods,
                        'decorators': [self._get_decorator_name(d) for d in node.decorator_list]
                    })
                
                # Track functions
                elif isinstance(node, ast.FunctionDef):
                    # Check for Flask routes
                    route = None
                    for decorator in node.decorator_list:
                        decorator_name = self._get_decorator_name(decorator)
                        if 'app.route' in decorator_name or 'blueprint.route' in decorator_name:
                            # Extract route path
                            if isinstance(decorator, ast.Call) and decorator.args:
                                if isinstance(decorator.args[0], ast.Constant):
                                    route = decorator.args[0].value
                            structure['routes'].append({
                                'function': node.name,
                                'route': route,
                                'methods': self._extract_http_methods(decorator),
                                'line': node.lineno
                            })
                    
                    structure['functions'].append({
                        'name': node.name,
                        'line': node.lineno,
                        'args': [arg.arg for arg in node.args.args],
                        'decorators': [self._get_decorator_name(d) for d in node.decorator_list],
                        'returns': self._get_return_annotation(node),
                        'route': route
                    })
                
                # Track function calls
                elif isinstance(node, ast.Call):
                    call_info = self._extract_call(node)
                    if call_info:
                        structure['calls'].append(call_info)
                        
                        # Detect database calls
                        if any(db in call_info['function'].lower() for db in ['query', 'session', 'db.', 'cursor']):
                            structure['database_calls'].append({
                                'function': call_info['function'],
                                'line': node.lineno
                            })
                
                # Track assignments (variables)
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            structure['variables'].append({
                                'name': target.id,
                                'line': node.lineno
                            })
            
            # Detect business rules from patterns
            structure['business_rules'] = self._detect_business_rules(tree, content)
            
        except SyntaxError as e:
            logger.warning(f"⚠️ Syntax error in {file_path}: {e}")
            # Fallback to regex parsing
            return self._parse_python_regex(content, file_path)
        
        return structure
    
    def _get_decorator_name(self, decorator) -> str:
        """Extract decorator name"""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return f"{self._get_attribute_base(decorator)}.{decorator.attr}"
        elif isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Name):
                return decorator.func.id
            elif isinstance(decorator.func, ast.Attribute):
                return f"{self._get_attribute_base(decorator.func)}.{decorator.func.attr}"
        return str(decorator)
    
    def _get_attribute_base(self, node) -> str:
        """Get base of attribute chain"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_attribute_base(node.value)}.{node.attr}"
        return ''
    
    def _extract_call(self, node) -> Optional[Dict]:
        """Extract function call information"""
        if isinstance(node.func, ast.Name):
            return {
                'function': node.func.id,
                'line': node.lineno,
                'args': len(node.args)
            }
        elif isinstance(node.func, ast.Attribute):
            return {
                'function': f"{self._get_attribute_base(node.func)}.{node.func.attr}",
                'line': node.lineno,
                'args': len(node.args)
            }
        return None
    
    def _extract_http_methods(self, decorator) -> List[str]:
        """Extract HTTP methods from route decorator"""
        methods = ['GET']  # Default
        if isinstance(decorator, ast.Call):
            for keyword in decorator.keywords:
                if keyword.arg == 'methods':
                    if isinstance(keyword.value, ast.List):
                        methods = []
                        for elt in keyword.value.elts:
                            if isinstance(elt, ast.Constant):
                                methods.append(elt.value)
        return methods
    
    def _get_return_annotation(self, node) -> Optional[str]:
        """Get return type annotation"""
        if node.returns:
            if isinstance(node.returns, ast.Name):
                return node.returns.id
            return str(node.returns)
        return None
    
    def _detect_business_rules(self, tree, content: str) -> List[Dict]:
        """Detect business rules from code patterns"""
        rules = []
        
        # Pattern 1: Validation rules (if statements with validation logic)
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                # Check if condition looks like validation
                condition_str = ast.unparse(node.test)
                if any(word in condition_str.lower() for word in ['validate', 'check', 'verify', 'is_', 'has_']):
                    rules.append({
                        'type': 'validation',
                        'description': f"Validation: {condition_str[:100]}",
                        'line': node.lineno
                    })
            
            # Pattern 2: Pricing/calculation rules
            elif isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Mult, ast.Add, ast.Sub)):
                if 'price' in ast.unparse(node).lower() or 'total' in ast.unparse(node).lower():
                    rules.append({
                        'type': 'calculation',
                        'description': f"Price calculation: {ast.unparse(node)[:100]}",
                        'line': node.lineno
                    })
            
            # Pattern 3: Access control
            elif isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    decorator_name = self._get_decorator_name(decorator)
                    if any(auth in decorator_name.lower() for auth in ['login', 'permission', 'role', 'admin']):
                        rules.append({
                            'type': 'access_control',
                            'description': f"Access control on {node.name}",
                            'line': node.lineno
                        })
        
        return rules
    
    def _parse_python_regex(self, content: str, file_path: str) -> Dict[str, Any]:
        """Fallback regex parsing for Python"""
        structure = {
            'imports': [],
            'functions': [],
            'classes': [],
            'business_rules': []
        }
        
        # Find imports
        import_matches = re.finditer(r'^(?:from\s+(\S+)\s+)?import\s+(\S+)', content, re.MULTILINE)
        for match in import_matches:
            structure['imports'].append(match.group(0))
        
        # Find functions
        func_matches = re.finditer(r'def\s+(\w+)\s*\(', content)
        for match in func_matches:
            structure['functions'].append({
                'name': match.group(1),
                'line': content[:match.start()].count('\n') + 1
            })
        
        # Find classes
        class_matches = re.finditer(r'class\s+(\w+)', content)
        for match in class_matches:
            structure['classes'].append({
                'name': match.group(1),
                'line': content[:match.start()].count('\n') + 1
            })
        
        return structure
    
    def _parse_javascript(self, content: str, file_path: str) -> Dict[str, Any]:
        """Parse JavaScript code"""
        structure = {
            'imports': [],
            'functions': [],
            'classes': [],
            'routes': [],
            'business_rules': []
        }
        
        # Find imports
        import_matches = re.finditer(r'import\s+.*?from\s+[\'"]([^\'"]+)[\'"]', content)
        for match in import_matches:
            structure['imports'].append(match.group(1))
        
        # Find functions
        func_matches = re.finditer(r'(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>|(\w+)\s*:\s*function)', content)
        for match in func_matches:
            name = match.group(1) or match.group(2) or match.group(3)
            if name:
                structure['functions'].append({
                    'name': name,
                    'line': content[:match.start()].count('\n') + 1
                })
        
        # Find Express routes
        route_matches = re.finditer(r'app\.(get|post|put|delete)\([\'"]([^\'"]+)[\'"]', content)
        for match in route_matches:
            structure['routes'].append({
                'method': match.group(1).upper(),
                'path': match.group(2),
                'line': content[:match.start()].count('\n') + 1
            })
        
        return structure
    
    def _parse_html(self, content: str, file_path: str) -> Dict[str, Any]:
        """Parse HTML code"""
        from bs4 import BeautifulSoup
        
        structure = {
            'forms': [],
            'inputs': [],
            'buttons': [],
            'links': []
        }
        
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            for form in soup.find_all('form'):
                structure['forms'].append({
                    'action': form.get('action', ''),
                    'method': form.get('method', 'get')
                })
            
            for input_tag in soup.find_all('input'):
                structure['inputs'].append({
                    'type': input_tag.get('type', 'text'),
                    'name': input_tag.get('name', '')
                })
            
            for button in soup.find_all('button'):
                structure['buttons'].append(button.get_text(strip=True))
            
            for link in soup.find_all('a'):
                structure['links'].append({
                    'href': link.get('href', ''),
                    'text': link.get_text(strip=True)
                })
                
        except Exception as e:
            logger.warning(f"⚠️ HTML parsing error in {file_path}: {e}")
        
        return structure
    
    def _parse_generic(self, content: str, file_path: str) -> Dict[str, Any]:
        """Generic fallback parser"""
        return {
            'lines': len(content.split('\n')),
            'size': len(content),
            'type': 'generic'
        }
    
    def _merge_analyses(self, analyses: List[Dict]) -> Dict[str, Any]:
        """Merge all analyses into business context"""
        business_context = {
            'files_analyzed': len(analyses),
            'by_type': {},
            'imports': [],
            'classes': [],
            'functions': [],
            'routes': [],
            'database_calls': [],
            'business_rules': [],
            'security_concerns': [],
            'confidence': 0.0
        }
        
        all_rules = []
        total_confidence = 0
        
        for item in analyses:
            ext = item['extension']
            business_context['by_type'][ext] = business_context['by_type'].get(ext, 0) + 1
            
            # Collect structure data
            structure = item.get('structure', {})
            business_context['imports'].extend(structure.get('imports', []))
            business_context['classes'].extend(structure.get('classes', []))
            business_context['functions'].extend(structure.get('functions', []))
            business_context['routes'].extend(structure.get('routes', []))
            business_context['database_calls'].extend(structure.get('database_calls', []))
            
            # Collect business rules
            rules = structure.get('business_rules', [])
            all_rules.extend(rules)
            
            # Add deep analysis rules if available
            deep = item.get('deep', {})
            if deep.get('business_rules'):
                all_rules.extend(deep['business_rules'])
            
            # Track confidence
            total_confidence += deep.get('confidence', 0.5)
        
        # Deduplicate business rules
        unique_rules = []
        seen = set()
        for rule in all_rules:
            rule_key = f"{rule.get('type', '')}:{rule.get('description', '')[:50]}"
            if rule_key not in seen:
                seen.add(rule_key)
                unique_rules.append(rule)
        
        business_context['business_rules'] = unique_rules
        business_context['confidence'] = total_confidence / len(analyses) if analyses else 0.5
        
        logger.info(f"✅ Agent 1: Found {len(unique_rules)} business rules, {len(business_context['routes'])} routes, {len(business_context['database_calls'])} DB calls")
        
        return business_context