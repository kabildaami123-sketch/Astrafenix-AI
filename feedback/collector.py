from typing import Dict, Any, List
import random

class FeedbackCollector:
    """
    Simplified feedback collector for hackathon
    """
    
    def generate_simulated_feedback(self, state: Dict) -> Dict[str, Any]:
        """
        Generate simulated feedback based on confidence
        For hackathon demo - in real app, this would come from user
        """
        confidence = state.get('confidence_score', 0.5)
        
        # Simulate feedback
        if confidence < 0.7:
            # Low confidence - simulate some corrections
            corrections = self._simulate_corrections(state)
            rating = random.randint(3, 4)
            comments = "Good start, but some business rules need clarification."
        else:
            corrections = []
            rating = random.randint(4, 5)
            comments = "Great analysis! Very accurate."
        
        return {
            'rating': rating,
            'comments': comments,
            'corrections': corrections,
            'engagement_time': random.randint(30, 300),
            'downloaded': random.choice([True, False])
        }

    def ingest_user_feedback(self, message: str, structured: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Ingest a user-supplied feedback message. If `structured` is provided,
        prefer it (it should include 'corrections' list). Returns a normalized
        feedback dict ready to be passed to `CodeAnalyzer.process_feedback`.
        """
        feedback = {
            'message': message,
            'corrections': []
        }

        if structured:
            # Basic validation - ensure corrections is a list
            corr = structured.get('corrections') or []
            if isinstance(corr, list):
                feedback['corrections'] = corr
        return feedback
    
    def _simulate_corrections(self, state: Dict) -> List[Dict]:
        """Simulate corrections for low confidence cases"""
        corrections = []
        
        business_rules = state.get('business_context', {}).get('business_rules', [])
        
        # Add corrections for first few rules
        for i, rule in enumerate(business_rules[:2]):
            corrections.append({
                'original': rule.get('code', ''),
                'corrected': f"Corrected version of rule {i+1}",
                'type': rule.get('type', 'unknown')
            })
        
        return corrections