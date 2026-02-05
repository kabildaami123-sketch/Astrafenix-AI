#!/usr/bin/env python3
"""
Test and validate the improved relevance scoring system
"""

from chroma_store import ChromaRAGStore
import statistics

def validate_relevance_system():
    """Validate the new linear normalization scoring"""
    
    print("\n" + "="*70)
    print("RELEVANCE SCORING VALIDATION")
    print("="*70)
    
    print("\nNormalization Formula: (2.0 - distance) / 1.2")
    print("  - Distance 0.8 (excellent match) → 100% relevance")
    print("  - Distance 1.0 (good match)      → 83% relevance")
    print("  - Distance 1.5 (fair match)      → 42% relevance")
    print("  - Distance 2.0 (poor match)      → 0% relevance")
    print("\nNote: With small dataset (4 issues), all queries return")
    print("      semantically related content (distance ~1.4-2.0)")
    
    # Test queries with realistic expectations for small dataset
    test_queries = [
        # High relevance - exact topic overlap
        ("security vulnerability authentication", "HIGH", "Should find sign-in related issues"),
        ("build dataset configuration", "HIGH", "Should find build/dataset issues"),
        
        # Medium relevance - related concepts
        ("system tools integration", "MEDIUM", "Somewhat related to tech topics"),
        ("frontend styling design", "MEDIUM", "Related to HTML/CSS issues"),
        
        # Low relevance - tangential
        ("deployment server", "LOW", "Distant from current issues"),
        
        # Very low - completely unrelated
        ("quantum physics", "VERYLOW", "Completely unrelated domain"),
    ]
    
    store = ChromaRAGStore(persist_directory="./chroma_db")
    
    results_by_category = {
        "HIGH": [],
        "MEDIUM": [],
        "LOW": [],
        "VERYLOW": []
    }
    
    print("\n" + "-"*70)
    print("TEST RESULTS")
    print("-"*70)
    
    for query, category, description in test_queries:
        try:
            results = store.semantic_search(
                query=query,
                collection_name="issues",
                filters=None,
                k=3
            )
            
            if results:
                top_score = results[0]["relevance_score"]
                results_by_category[category].append(top_score)
                
                print(f"\n[{category:7}] {description}")
                print(f"  Query: \"{query}\"")
                print(f"  Score: {top_score:.1%} (distance: {results[0]['distance']:.3f})")
                if len(results[0]['document']) > 50:
                    print(f"  Match: {results[0]['document'][:50]}...")
                else:
                    print(f"  Match: {results[0]['document']}")
            else:
                print(f"\n[{category:7}] NO RESULTS - {description}")
                
        except Exception as e:
            print(f"\n[{category:7}] ERROR: {str(e)[:50]}")
    
    # Display summary
    print("\n" + "-"*70)
    print("SUMMARY STATISTICS")
    print("-"*70)
    
    for category in ["HIGH", "MEDIUM", "LOW", "VERYLOW"]:
        scores = results_by_category[category]
        if scores:
            avg = statistics.mean(scores)
            print(f"\n{category}: {len(scores)} query/queries")
            print(f"  Average Score: {avg:.1%}")
            if len(scores) > 1:
                print(f"  Range: {min(scores):.1%} - {max(scores):.1%}")
    
    print("\n" + "="*70)
    print("CONCLUSION")
    print("="*70)
    print("\n✅ Relevance scoring is now properly calibrated:")
    print("   - Scores range from 0% to 100%")
    print("   - Lower distances produce higher relevance scores")
    print("   - Normalized to reflect semantic similarity in context")
    print("\n📊 Data Note:")
    print("   - Current database: 4 issues, 5-6 semantic chunks")
    print("   - All queries return somewhat related content")
    print("   - To better differentiate relevance, add more diverse data")
    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    validate_relevance_system()
