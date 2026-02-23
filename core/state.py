# core/state.py
from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

class ProcessingStage(str, Enum):
    INITIALIZED = "initialized"
    FETCHING = "fetching"
    ANALYZING = "analyzing"
    TRANSLATING = "translating"
    REPORTING = "reporting"
    FEEDBACK = "feedback"
    LEARNING = "learning"
    COMPLETED = "completed"
    FAILED = "failed"

class SystemState(TypedDict):
    # Input
    repo_url: str
    files_to_download: List[str]
    client_preferences: Dict[str, Any]
    
    # GitHub fetching results
    downloaded_files: Dict[str, Any]
    files_fetched: int
    total_requested: int
    api_calls: int
    cache_hits: int
    github_rate_limit_remaining: int
    
    # Agent 1: CodeUnderstandingAgent results
    technical_analysis: Dict[str, Any]  # Raw analysis per file
    business_rules: List[Dict[str, Any]]
    features_found: List[Dict[str, Any]]
    functions_found: List[Dict[str, Any]]
    routes_found: List[Dict[str, Any]]
    database_calls: List[Dict[str, Any]]
    imports_found: List[Dict[str, Any]]
    analysis_confidence: float
    
    # CodeAnalyzer results (used by Agent 1)
    file_types: Dict[str, str]  # Map of file path to type
    
    # BusinessTranslator results
    business_context: Dict[str, Any]
    categorized_rules: Dict[str, List[Dict[str, Any]]]
    business_summary: str
    
    # Agent 2: ReportGeneratorAgent results
    report_text: str
    report_metrics: Dict[str, Any]
    executive_summary: str
    
    # Feedback
    user_rating: Optional[int]
    user_comments: Optional[str]
    corrections: List[Dict[str, Any]]
    
    # Learning
    successful_patterns: List[Dict[str, Any]]
    failed_patterns: List[Dict[str, Any]]
    confidence_score: float
    pattern_db_updated: bool
    
    # System
    stage: ProcessingStage
    errors: List[str]
    warnings: List[str]
    start_time: datetime
    end_time: Optional[datetime]
    processing_time: float
    node_execution_times: Dict[str, float]  # Track time per node