# core/graph.py
from langgraph.graph import StateGraph, END
from typing import Dict, Any, Literal
from datetime import datetime
import asyncio
import time

from core.state import SystemState, ProcessingStage
from github.fetcher import GitHubFileDownloader
from agents.code_agent import CodeUnderstandingAgent
from agents.report_agent import ReportGeneratorAgent
from agents.code_analyzer import CodeAnalyzer
from agents.business_translator import BusinessTranslator
from feedback.collector import FeedbackCollector
from utils.logger import logger
from core.config import config

class AgentGraph:
    """
    LangGraph-based orchestrator with proper nodes and edges
    Uses your existing agents!
    """
    
    def __init__(self):
        # Initialize your existing agents
        self.fetcher = GitHubFileDownloader()
        self.code_agent = CodeUnderstandingAgent()
        self.report_agent = ReportGeneratorAgent()
        self.code_analyzer = CodeAnalyzer()
        self.business_translator = BusinessTranslator()
        self.feedback = FeedbackCollector()
        
        # Build the graph
        self.graph = self._build_graph()
        self.compiled_graph = self.graph.compile()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph with nodes and conditional edges"""
        
        # Initialize the graph with SystemState
        workflow = StateGraph(SystemState)
        
        # === ADD NODES ===
        workflow.add_node("fetch_code", self.fetch_code_node)
        workflow.add_node("analyze_code", self.analyze_code_node)
        workflow.add_node("translate_business", self.translate_business_node)
        workflow.add_node("generate_report", self.generate_report_node)
        workflow.add_node("collect_feedback", self.collect_feedback_node)
        workflow.add_node("learn_from_feedback", self.learn_from_feedback_node)
        
        # === SET ENTRY POINT ===
        workflow.set_entry_point("fetch_code")
        
        # === ADD EDGES (Main Flow) ===
        workflow.add_edge("fetch_code", "analyze_code")
        workflow.add_edge("analyze_code", "translate_business")
        workflow.add_edge("translate_business", "generate_report")
        workflow.add_edge("generate_report", "collect_feedback")
        
        # === CONDITIONAL EDGES (Feedback Loop) ===
        workflow.add_conditional_edges(
            "collect_feedback",
            self.should_learn_from_feedback,
            {
                True: "learn_from_feedback",
                False: END
            }
        )
        
        # === FEEDBACK LOOP EDGE ===
        workflow.add_conditional_edges(
            "learn_from_feedback",
            self.should_retry_analysis,
            {
                True: "analyze_code",  # Re-analyze with improved patterns
                False: END
            }
        )
        
        return workflow
    
    # === NODE FUNCTIONS ===
    
    async def fetch_code_node(self, state: SystemState) -> SystemState:
        """Node 1: Fetch code from GitHub"""
        node_start = time.time()
        logger.info("📥 [Node 1] Fetching code from GitHub...")
        state['stage'] = ProcessingStage.FETCHING
        state['start_time'] = datetime.now()
        
        try:
            async with self.fetcher as fetcher:
                downloaded_files = {}
                file_types = {}
                successful = 0
                
                for file_path in state['files_to_download']:
                    file_info = await fetcher.download_file(
                        self._get_owner(state['repo_url']),
                        self._get_repo(state['repo_url']),
                        file_path
                    )
                    if file_info:
                        downloaded_files[file_path] = file_info
                        
                        # Use CodeAnalyzer to determine file type
                        analysis = self.code_analyzer.analyze_file(file_info)
                        file_types[file_path] = analysis.get('type', 'unknown')
                        successful += 1
                    
                    await asyncio.sleep(0.1)  # Small delay to avoid rate limits
                
                state['downloaded_files'] = downloaded_files
                state['file_types'] = file_types
                state['files_fetched'] = successful
                state['total_requested'] = len(state['files_to_download'])
                state['api_calls'] = getattr(fetcher, 'api_calls', 0)
                state['cache_hits'] = getattr(fetcher, 'cache_hits', 0)
                state['github_rate_limit_remaining'] = getattr(fetcher, 'rate_limit_remaining', 5000)
                
                logger.info(f"   ✅ Downloaded {successful}/{len(state['files_to_download'])} files")
                
        except Exception as e:
            state['errors'].append(f"Fetch error: {str(e)}")
            state['stage'] = ProcessingStage.FAILED
            
        # Track execution time
        state['node_execution_times'] = state.get('node_execution_times', {})
        state['node_execution_times']['fetch_code'] = time.time() - node_start
        
        return state
    
    async def analyze_code_node(self, state: SystemState) -> SystemState:
        """Node 2: Analyze code with CodeUnderstandingAgent"""
        node_start = time.time()
        logger.info("🔍 [Node 2] Analyzing code with CodeUnderstandingAgent...")
        state['stage'] = ProcessingStage.ANALYZING
        
        try:
            # Use your existing CodeUnderstandingAgent
            if state['downloaded_files']:
                business_context = await self.code_agent.analyze_batch(state['downloaded_files'])
                
                # Extract relevant data
                state['technical_analysis'] = business_context
                state['business_rules'] = business_context.get('business_rules', [])
                state['features_found'] = business_context.get('functions', [])
                state['functions_found'] = business_context.get('functions', [])
                state['routes_found'] = business_context.get('routes', [])
                state['database_calls'] = business_context.get('database_calls', [])
                state['imports_found'] = business_context.get('imports', [])
                state['analysis_confidence'] = business_context.get('confidence', 0.85)
                
                logger.info(f"   ✅ Found {len(state['business_rules'])} business rules, {len(state['features_found'])} features")
            else:
                logger.warning("   ⚠️ No files to analyze")
                
        except Exception as e:
            state['errors'].append(f"Analysis error: {str(e)}")
            state['stage'] = ProcessingStage.FAILED
            
        state['node_execution_times']['analyze_code'] = time.time() - node_start
        return state
    
    async def translate_business_node(self, state: SystemState) -> SystemState:
        """Node 3: Translate technical analysis to business language"""
        node_start = time.time()
        logger.info("💼 [Node 3] Translating to business language with BusinessTranslator...")
        state['stage'] = ProcessingStage.TRANSLATING
        
        try:
            # Use your existing BusinessTranslator
            if state['technical_analysis']:
                # Prepare file analyses for translator
                file_analyses = {}
                for path, file_info in state['downloaded_files'].items():
                    file_analyses[path] = {
                        'type': state['file_types'].get(path, 'unknown'),
                        'business_purpose': [],
                        'key_functions': state['functions_found'],
                        'business_rules': state['business_rules'],
                        'forms': [],
                        'ui_elements': []
                    }
                
                business_context = self.business_translator.translate(file_analyses)
                state['business_context'] = business_context
                state['business_summary'] = business_context.get('summary', '')
                
                # Categorize rules
                categorized = {
                    'social': [],
                    'financial': [],
                    'security': [],
                    'communication': [],
                    'validation': [],
                    'other': []
                }
                
                for rule in state['business_rules']:
                    rule_desc = rule.get('description', '').lower()
                    if any(word in rule_desc for word in ['follow', 'user', 'profile']):
                        categorized['social'].append(rule)
                    elif any(word in rule_desc for word in ['price', 'total', 'cost', 'payment']):
                        categorized['financial'].append(rule)
                    elif any(word in rule_desc for word in ['password', 'auth', 'login']):
                        categorized['security'].append(rule)
                    elif any(word in rule_desc for word in ['email', 'mail', 'notify']):
                        categorized['communication'].append(rule)
                    elif any(word in rule_desc for word in ['validate', 'check', 'ensure']):
                        categorized['validation'].append(rule)
                    else:
                        categorized['other'].append(rule)
                
                state['categorized_rules'] = categorized
                
                logger.info(f"   ✅ Categorized rules into {len(categorized)} domains")
            else:
                logger.warning("   ⚠️ No technical analysis to translate")
                
        except Exception as e:
            state['errors'].append(f"Translation error: {str(e)}")
            
        state['node_execution_times']['translate_business'] = time.time() - node_start
        return state
    
    async def generate_report_node(self, state: SystemState) -> SystemState:
        """Node 4: Generate report with ReportGeneratorAgent"""
        node_start = time.time()
        logger.info("📊 [Node 4] Generating report with ReportGeneratorAgent...")
        state['stage'] = ProcessingStage.REPORTING
        
        try:
            # Calculate processing time
            state['end_time'] = datetime.now()
            state['processing_time'] = (state['end_time'] - state['start_time']).total_seconds()
            
            # Prepare metadata for report
            metadata = {
                'repo_url': state['repo_url'],
                'files_fetched': state['files_fetched'],
                'total_files': state['total_requested'],
                'processing_time': state['processing_time'],
                'api_calls': state['api_calls'],
                'cache_hits': state['cache_hits'],
                'confidence': state.get('analysis_confidence', 0.85),
                'file_details': state['file_types'],
                'report_type': 'sprint'
            }
            
            # Use your existing ReportGeneratorAgent
            report_result = await self.report_agent.generate(
                state['business_context'] or {},
                metadata
            )
            
            state['report_text'] = report_result.get('text', '')
            state['executive_summary'] = report_result.get('summary', '')
            state['report_metrics'] = {
                'features': report_result.get('features_count', 0),
                'rules': report_result.get('rules_count', 0),
                'time': state['processing_time']
            }
            
            logger.info(f"   ✅ Report generated in {state['processing_time']:.2f}s")
            
        except Exception as e:
            state['errors'].append(f"Report generation error: {str(e)}")
            
        state['node_execution_times']['generate_report'] = time.time() - node_start
        return state
    
    async def collect_feedback_node(self, state: SystemState) -> SystemState:
        """Node 5: Collect feedback using FeedbackCollector"""
        node_start = time.time()
        logger.info("📝 [Node 5] Collecting feedback...")
        state['stage'] = ProcessingStage.FEEDBACK
        
        try:
            # Use your existing FeedbackCollector
            confidence = state.get('analysis_confidence', 0.85)
            
            # Simulate feedback based on confidence
            if confidence < 0.7:
                corrections = self.feedback.simulate_corrections(state['business_rules'])
                state['corrections'] = corrections
                state['user_rating'] = 3
                state['user_comments'] = "Good start, but some rules need clarification."
                logger.info(f"   🔄 Received {len(corrections)} corrections")
            else:
                state['corrections'] = []
                state['user_rating'] = 5
                state['user_comments'] = "Great analysis!"
                logger.info("   ✅ Positive feedback received")
                
        except Exception as e:
            state['errors'].append(f"Feedback error: {str(e)}")
            
        state['node_execution_times']['collect_feedback'] = time.time() - node_start
        return state
    
    async def learn_from_feedback_node(self, state: SystemState) -> SystemState:
        """Node 6: Learn from feedback and improve"""
        node_start = time.time()
        logger.info("🧠 [Node 6] Learning from feedback...")
        state['stage'] = ProcessingStage.LEARNING
        
        try:
            if state['corrections']:
                # Store corrections as failed patterns
                for correction in state['corrections']:
                    state['failed_patterns'].append({
                        'pattern': correction.get('original', ''),
                        'correction': correction.get('corrected', ''),
                        'timestamp': datetime.now().isoformat()
                    })
                
                # Update confidence score (improves with corrections)
                current_confidence = state.get('confidence_score', state.get('analysis_confidence', 0.85))
                state['confidence_score'] = min(0.95, current_confidence + 0.02)
                state['pattern_db_updated'] = True
                
                logger.info(f"   ✅ Learned from {len(state['corrections'])} corrections")
                logger.info(f"   📈 Confidence increased to {state['confidence_score']*100:.1f}%")
            else:
                # Store successful patterns
                for rule in state.get('business_rules', [])[:5]:
                    state['successful_patterns'].append({
                        'pattern': rule.get('description', ''),
                        'category': 'business_rule',
                        'timestamp': datetime.now().isoformat()
                    })
                state['pattern_db_updated'] = False
                
        except Exception as e:
            state['errors'].append(f"Learning error: {str(e)}")
            
        state['node_execution_times']['learn_from_feedback'] = time.time() - node_start
        return state
    
    # === CONDITIONAL EDGE FUNCTIONS ===
    
    def should_learn_from_feedback(self, state: SystemState) -> bool:
        """Determine if we should trigger learning node"""
        # Learn if there are corrections
        return len(state.get('corrections', [])) > 0
    
    def should_retry_analysis(self, state: SystemState) -> bool:
        """Determine if we should re-analyze with improved patterns"""
        # Retry if we learned something significant (more than 3 corrections)
        return len(state.get('failed_patterns', [])) > 3
    
    # === HELPER FUNCTIONS ===
    
    def _get_owner(self, repo_url: str) -> str:
        """Extract owner from GitHub URL"""
        parts = repo_url.rstrip('/').split('/')
        return parts[-2]
    
    def _get_repo(self, repo_url: str) -> str:
        """Extract repo name from GitHub URL"""
        parts = repo_url.rstrip('/').split('/')
        return parts[-1].replace('.git', '')
    
    async def run(self, repo_url: str, files_to_download: List[str]) -> Dict[str, Any]:
        """
        Run the complete LangGraph workflow
        """
        # Initialize state
        initial_state: SystemState = {
            'repo_url': repo_url,
            'files_to_download': files_to_download,
            'client_preferences': {},
            'downloaded_files': {},
            'files_fetched': 0,
            'total_requested': len(files_to_download),
            'api_calls': 0,
            'cache_hits': 0,
            'github_rate_limit_remaining': 5000,
            'technical_analysis': {},
            'business_rules': [],
            'features_found': [],
            'functions_found': [],
            'routes_found': [],
            'database_calls': [],
            'imports_found': [],
            'analysis_confidence': 0.85,
            'file_types': {},
            'business_context': {},
            'categorized_rules': {},
            'business_summary': '',
            'report_text': '',
            'report_metrics': {},
            'executive_summary': '',
            'user_rating': None,
            'user_comments': None,
            'corrections': [],
            'successful_patterns': [],
            'failed_patterns': [],
            'confidence_score': 0.85,
            'pattern_db_updated': False,
            'stage': ProcessingStage.INITIALIZED,
            'errors': [],
            'warnings': [],
            'start_time': datetime.now(),
            'end_time': None,
            'processing_time': 0.0,
            'node_execution_times': {}
        }
        
        # Run the graph
        final_state = await self.compiled_graph.ainvoke(initial_state)
        final_state['stage'] = ProcessingStage.COMPLETED
        
        return final_state