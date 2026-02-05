from jira_data_fetcher import JiraDataFetcher
from smart_chunker import JiraSmartChunker
from chroma_store import ChromaRAGStore
from typing import List, Dict
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Get Gemini API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# rag_pipeline.py
class JiraRAGPipeline:
    def __init__(self, domain: str, email: str, api_token: str):
        self.fetcher = JiraDataFetcher(domain, email, api_token)
        self.chunker = JiraSmartChunker()
        self.vector_store = ChromaRAGStore()
        
    def ingest_project(self, project_key: str, max_issues: int = 50):
        """Complete ingestion pipeline for a project"""
        
        print(f"🚀 Starting RAG ingestion for project: {project_key}")
        
        # Step 1: Fetch project data
        print("📥 Fetching project details...")
        project_data = self.fetcher.fetch_project_details(project_key)
        
        # Step 2: Chunk project data
        print("✂️ Chunking project data...")
        project_chunks = self.chunker.chunk_project_data(project_data)
        
        # Step 3: Store project chunks
        print("💾 Storing project chunks in vector DB...")
        self.vector_store.store_project_chunks(project_chunks, project_key)
        
        # Step 4: Fetch issues
        print("📥 Fetching project issues...")
        issues = self.fetcher.fetch_project_issues(project_key, max_issues)
        
        print(f"📊 Found {len(issues)} issues")
        if issues:
            print(f"📌 First issue sample: {issues[0].get('key')} - {issues[0].get('summary')[:50]}")
        else:
            print("⚠️  No issues found in project")
        
        # Step 5: Process each issue
        all_issue_chunks = []
        for i, issue in enumerate(issues):
            print(f"  Processing issue {i+1}/{len(issues)}: {issue['key']}")
            
            # Chunk issue data
            try:
                issue_chunks = self.chunker.chunk_issue_data(issue)
                all_issue_chunks.extend(issue_chunks)
                print(f"    ✓ Created {len(issue_chunks)} chunks")
            except Exception as e:
                print(f"    ✗ Error chunking issue: {e}")
            
            # Progress indicator
            if (i + 1) % 10 == 0:
                print(f"    {i+1} issues processed, {len(all_issue_chunks)} chunks created")
        
        # Step 6: Store issue chunks
        print(f"💾 Storing {len(all_issue_chunks)} issue chunks...")
        if all_issue_chunks:
            self.vector_store.store_issue_chunks(all_issue_chunks, project_key)
        
        print(f"🎉 RAG ingestion complete for {project_key}!")
        print(f"   • Project chunks: {len(project_chunks)}")
        print(f"   • Issue chunks: {len(all_issue_chunks)}")
        print(f"   • Total chunks: {len(project_chunks) + len(all_issue_chunks)}")
        
        return {
            "project_key": project_key,
            "project_chunks": len(project_chunks),
            "issue_chunks": len(all_issue_chunks),
            "total_chunks": len(project_chunks) + len(all_issue_chunks)
        }
    
    def query_project(self, query: str, project_key: str, 
                     query_type: str = "general", k: int = 10) -> Dict:
        """Query the RAG system"""
        
        # Route query based on type
        if "bug" in query.lower() or "error" in query.lower():
            # Special handling for bug queries
            results = self.vector_store.get_recent_bugs(project_key, k=k)
            source = "semantic_bug_search"
        elif "team" in query.lower() or "member" in query.lower():
            # Query project/team data
            results = self.vector_store.semantic_search(
                query=query,
                collection_name="project",
                filters={"project_key": project_key, "type": {"$in": ["team_members", "component"]}},
                k=k
            )
            source = "project_team_search"
        else:
            # General search across both collections
            # Try issues first (more detailed)
            issue_results = self.vector_store.semantic_search(
                query=query,
                collection_name="issues",
                filters={"project_key": project_key},
                k=k//2
            )
            
            # Then project data
            project_results = self.vector_store.semantic_search(
                query=query,
                collection_name="project",
                filters={"project_key": project_key},
                k=k//2
            )
            
            results = issue_results + project_results
            results.sort(key=lambda x: x["relevance_score"], reverse=True)
            results = results[:k]
            source = "hybrid_search"
        
        # Extract context for LLM
        context = "\n\n".join([
            f"[Source {i+1} - {r['metadata'].get('type', 'unknown')}]: {r['document'][:500]}..."
            for i, r in enumerate(results[:5])  # Limit context tokens
        ])
        
        return {
            "query": query,
            "project": project_key,
            "results_count": len(results),
            "top_results": [
                {
                    "content": r["document"][:200] + "..." if len(r["document"]) > 200 else r["document"],
                    "type": r["metadata"].get("type", "unknown"),
                    "relevance": r["relevance_score"],
                    "metadata": {k: v for k, v in r["metadata"].items() 
                                if k in ["key", "author", "created", "tags"]}
                }
                for r in results[:3]  # Return top 3 for display
            ],
            "context": context,
            "search_source": source
        }
    
    def query(self, user_query: str, project_key: str = "PRJ") -> str:
        """Query the RAG system and generate response using Gemini"""
        
        # Get search results
        search_results = self.query_project(user_query, project_key)
        context = search_results["context"]
        
        # If no Gemini API key, return raw search results
        if not GEMINI_API_KEY:
            return self._format_search_results(search_results)
        
        # Use Gemini to generate response
        try:
            import google.genai as genai
            
            client = genai.Client(api_key=GEMINI_API_KEY)
            
            prompt = f"""You are a helpful developer assistant with expertise in Jira project management.

Based on the following context from the Jira project, answer the developer's question accurately and concisely.

CONTEXT:
{context}

DEVELOPER QUESTION: {user_query}

INSTRUCTIONS:
- Answer based on the provided context from the Jira project
- If the context doesn't contain relevant information, say so clearly
- Be concise but comprehensive
- Format your answer with clear structure using bullet points if needed
- Focus on practical, actionable information
"""
            
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            return response.text
            
        except Exception as e:
            print(f"Warning: Gemini API error: {e}")
            return self._format_search_results(search_results)
    
    def _format_search_results(self, search_results: Dict) -> str:
        """Format search results as fallback when Gemini is unavailable"""
        
        output = f"📊 Search Results ({search_results['results_count']} found):\n\n"
        
        if not search_results["top_results"]:
            return output + "❌ No relevant results found for your query."
        
        for i, result in enumerate(search_results["top_results"], 1):
            output += f"{i}. [{result['type'].upper()}] (Relevance: {result['relevance']:.2%})\n"
            output += f"   {result['content']}\n"
            if result["metadata"]:
                output += f"   Metadata: {result['metadata']}\n"
            output += "\n"
        
        return output