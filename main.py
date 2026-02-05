# main.py
import json
import os
from dotenv import load_dotenv
from rag_pipeline import JiraRAGPipeline

load_dotenv()

def main():
    # Configuration
    DOMAIN = os.getenv("JIRA_DOMAIN", "kabildaami123")
    EMAIL = os.getenv("JIRA_EMAIL", "kabildaami123@gmail.com")
    API_TOKEN = os.getenv("JIRA_API_TOKEN")
    PROJECT_KEY = "PRJ"  # e.g., "PROJ"
    
    if not API_TOKEN:
        print(" Please set JIRA_API_TOKEN in .env file")
        return
    
    # Initialize pipeline
    pipeline = JiraRAGPipeline(DOMAIN, EMAIL, API_TOKEN)
    
    # Option 1: Ingest project data
    print("Choose operation:")
    print("1. Ingest project data into RAG")
    print("2. Query existing RAG data")
    
    try:
        choice = input("Enter choice (1 or 2): ").strip()
    except EOFError:
        print("No input provided, exiting...")
        return
    
    if choice == "1":
        # Ingest project
        print(f" Ingesting project {PROJECT_KEY}...")
        result = pipeline.ingest_project(PROJECT_KEY, max_issues=30)
        print(json.dumps(result, indent=2))
        
        # Test query after ingestion
        try:
            test_query = input("\nTest query (or press Enter to skip): ").strip()
        except EOFError:
            test_query = ""
        
        if test_query:
            print(f"\n Testing query: '{test_query}'")
            answer = pipeline.query(test_query)
            print(f" Answer: {answer}")
    
    elif choice == "2":
        # Query mode
        while True:
            try:
                query = input("\n Enter your question (or 'quit' to exit): ").strip()
            except EOFError:
                break
            
            if query.lower() in ['quit', 'exit', 'q']:
                break
            if query:
                print("Searching...")
                answer = pipeline.query(query)
                print(f" Answer: {answer}")
            else:
                print("Please enter a question.")
    
    else:
        print(" Invalid choice. Please enter 1 or 2.")

if __name__ == "__main__":
    main()
    try:
        print("\n Program finished. Press Enter to close...")
        input()  # Keeps terminal window open
    except EOFError:
        pass  # No input available, exit gracefully