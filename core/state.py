from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

class ProcessingStage(str, Enum):
    FETCHING = "fetching"
    ANALYZING = "analyzing"
    REPORTING = "reporting"
    COMPLETED = "completed"
    FAILED = "failed"

class SystemState(TypedDict):
    # Job info
    job_id: str
    repo_url: str
    
    # Fetching
    files: Dict[str, Any]          # All fetched files
    files_fetched: int              # Count for scalability demo
    total_files_in_repo: int        # Show we're sampling
    
    # Analysis
    business_context: Optional[Dict[str, Any]]
    confidence_score: float
    
    # Reporting
    report: Optional[Dict[str, Any]]
    
    # Feedback
    feedback: Optional[Dict[str, Any]]
    corrections: List[Dict[str, Any]]
    
    # Performance metrics
    processing_time: float
    files_processed: int
    api_calls: int
    cache_hits: int
    
    # Status
    stage: ProcessingStage
    errors: List[str]
    started_at: datetime
    completed_at: Optional[datetime]