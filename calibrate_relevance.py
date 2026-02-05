"""
Relevance Score Calibration for RAG Pipeline
Tests and calibrates the semantic search relevance scoring
"""
import os
from dotenv import load_dotenv
from jira_data_fetcher import JiraDataFetcher
from smart_chunker import JiraSmartChunker
from chroma_store import ChromaRAGStore
import json

load_dotenv()

# Synthetic test cases: (query, expected_relevant_keywords, relevance_category)
SYNTHETIC_TEST_DATA = [
    # High relevance tests - exact/direct matches
    ("build dataset for clients", ["dataset", "clients", "build"], "HIGH"),
    ("sign in button implementation", ["sign in", "button"], "HIGH"),
    ("html and css styling", ["html", "css"], "HIGH"),
    
    # Medium relevance tests - semantic matches
    ("data preparation for project", ["dataset", "build"], "MEDIUM"),
    ("authentication functionality", ["sign in", "button"], "MEDIUM"),
    ("frontend styling issues", ["html", "css"], "MEDIUM"),
    
    # Low relevance tests - tangential matches
    ("database optimization", ["dataset"], "LOW"),
    ("security considerations", ["sign in"], "LOW"),
    ("web standards compliance", ["html"], "LOW"),
    
    # Very low relevance
    ("server maintenance", ["bug"], "VERYLOW"),
    ("deployment pipeline", ["fix"], "VERYLOW"),
]

def calibrate_relevance_scores():
    """Test current relevance scoring against synthetic data"""
    
    domain = os.getenv("JIRA_DOMAIN", "kabildaami123")
    email = os.getenv("JIRA_EMAIL", "kabildaami123@gmail.com")
    api_token = os.getenv("JIRA_API_TOKEN")
    
    # Initialize
    vector_store = ChromaRAGStore()
    
    print("=" * 70)
    print("RELEVANCE SCORE CALIBRATION TEST")
    print("=" * 70)
    
    results_summary = {
        "HIGH": {"queries": 0, "avg_score": 0, "scores": []},
        "MEDIUM": {"queries": 0, "avg_score": 0, "scores": []},
        "LOW": {"queries": 0, "avg_score": 0, "scores": []},
        "VERYLOW": {"queries": 0, "avg_score": 0, "scores": []},
    }
    
    for query, keywords, expected_category in SYNTHETIC_TEST_DATA:
        try:
            # Perform semantic search without filters first
            results = vector_store.semantic_search(
                query=query,
                collection_name="issues",
                filters=None,
                k=5
            )
            
            if results:
                top_score = results[0]["relevance_score"]
                results_summary[expected_category]["queries"] += 1
                results_summary[expected_category]["scores"].append(top_score)
                
                print(f"\nQuery: '{query}'")
                print(f"Expected: {expected_category}")
                print(f"Top Result Score: {top_score:.2f}")
                if results[0]["document"]:
                    print(f"Match: {results[0]['document'][:60]}...")
            else:
                print(f"\nQuery: '{query}' - No results found")
                
        except Exception as e:
            print(f"\nQuery: '{query}' - Error: {str(e)[:50]}")
    
    # Calculate statistics
    print("\n" + "=" * 70)
    print("CALIBRATION STATISTICS")
    print("=" * 70)
    
    for category, data in results_summary.items():
        if data["queries"] > 0:
            avg = sum(data["scores"]) / len(data["scores"])
            min_score = min(data["scores"])
            max_score = max(data["scores"])
            results_summary[category]["avg_score"] = avg
            
            print(f"\n{category} Relevance (n={data['queries']})")
            print(f"  Average Score: {avg:.4f}")
            print(f"  Min Score: {min_score:.4f}")
            print(f"  Max Score: {max_score:.4f}")
    
    print("\n" + "=" * 70)
    print("RECOMMENDATIONS FOR SCORE NORMALIZATION")
    print("=" * 70)
    
    # Analyze score distribution
    all_scores = []
    for data in results_summary.values():
        all_scores.extend(data["scores"])
    
    if all_scores:
        min_actual = min(all_scores)
        max_actual = max(all_scores)
        
        print(f"\nDistance Range Found: [{min_actual:.4f}, {max_actual:.4f}]")
        print(f"\nCurrent Formula: relevance_score = 1 - distance")
        print(f"  -> Gives range: [{1 - max_actual:.4f}, {1 - min_actual:.4f}]")
        print(f"  -> Problem: Negative values and inverted scale!\n")
        
        # Propose better formula
        print("IMPROVED FORMULA OPTIONS:")
        print(f"\n1. Max-Min Normalization (Recommended):")
        print(f"   relevance_score = (max_dist - distance) / (max_dist - min_dist)")
        print(f"   Result range: [0, 1] or [0%, 100%]")
        
        print(f"\n2. Exponential Decay:")
        print(f"   relevance_score = exp(-distance)")
        print(f"   Emphasizes very close matches")
        
        print(f"\n3. Sigmoid Normalization:")
        print(f"   relevance_score = 1 / (1 + exp(distance))")
        print(f"   Smooth s-curve mapping")

if __name__ == "__main__":
    calibrate_relevance_scores()
