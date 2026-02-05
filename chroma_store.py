import chromadb
from chromadb.config import Settings
from typing import List, Dict
import hashlib
import math

class ChromaRAGStore:
    def __init__(self, persist_directory: str = "./chroma_db"):
        self.client = chromadb.PersistentClient(path=persist_directory)

        
        # Create or get collections
        self.project_collection = self.client.get_or_create_collection(
            name="project_data",
            metadata={"description": "Project metadata and team information"}
        )
        
        self.issues_collection = self.client.get_or_create_collection(
            name="issues_data", 
            metadata={"description": "Jira issues with comments and worklogs"}
        )
    
    def store_project_chunks(self, chunks: List[Dict], project_key: str):
        """Store project chunks in ChromaDB"""
        
        documents = []
        metadatas = []
        ids = []
        
        for chunk in chunks:
            content = chunk["content"]
            metadata = chunk["metadata"]
            
            # Generate unique ID
            chunk_id = metadata.get("chunk_id", self._generate_chunk_id(content))
            
            documents.append(content)
            metadatas.append(metadata)
            ids.append(chunk_id)
        
        # Add to collection
        self.project_collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"✅ Stored {len(chunks)} project chunks for {project_key}")
    
    def store_issue_chunks(self, chunks: List[Dict], project_key: str):
        """Store issue chunks in ChromaDB"""
        
        documents = []
        metadatas = []
        ids = []
        
        for chunk in chunks:
            content = chunk["content"]
            metadata = chunk["metadata"]
            
            # Generate unique ID
            chunk_id = metadata.get("chunk_id", self._generate_chunk_id(content))
            
            documents.append(content)
            metadatas.append(metadata)
            ids.append(chunk_id)
        
        # Add to collection
        self.issues_collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"✅ Stored {len(chunks)} issue chunks for {project_key}")
    
    def semantic_search(self, query: str, collection_name: str, 
                       filters: Dict = None, k: int = 10) -> List[Dict]:
        """Perform semantic search with filtering"""
        
        collection = getattr(self, f"{collection_name}_collection")
        
        # Build where filter for metadata
        where_filter = None
        if filters:
            filter_conditions = []
            for key, value in filters.items():
                if isinstance(value, dict) and "$in" in value:
                    # Already has an operator
                    filter_conditions.append({key: value})
                elif isinstance(value, list):
                    filter_conditions.append({key: {"$in": value}})
                else:
                    filter_conditions.append({key: value})
            
            # Combine multiple conditions with $and
            if len(filter_conditions) == 1:
                where_filter = filter_conditions[0]
            elif len(filter_conditions) > 1:
                where_filter = {"$and": filter_conditions}
        
        # Perform search
        results = collection.query(
            query_texts=[query],
            n_results=k,
            where=where_filter if where_filter else None,
            include=["documents", "metadatas", "distances"]
        )
        
        # Format results with improved relevance scoring
        formatted_results = []
        for i in range(len(results["documents"][0])):
            distance = results["distances"][0][i]
            # Use improved sigmoid normalization for better relevance scoring
            relevance_score = self._normalize_relevance_score(distance)
            
            formatted_results.append({
                "document": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": distance,
                "relevance_score": relevance_score  # Now properly normalized to [0, 1]
            })
        
        return formatted_results
    
    def get_recent_bugs(self, project_key: str, k: int = 10) -> List[Dict]:
        """Get recent bugs and issues"""
        
        # Try to find bug type issues first
        try:
            results = self.semantic_search(
                query="bug fix error issue problem",
                collection_name="issues",
                filters={
                    "project_key": project_key,
                    "type": "issue_core"
                },
                k=k
            )
        except:
            # Fallback to general search if filters fail
            results = self.semantic_search(
                query="bug fix error issue problem",
                collection_name="issues",
                filters={"project_key": project_key},
                k=k
            )
        
        # If no results, do a general search
        if not results:
            results = self.semantic_search(
                query="bug fix error issue problem",
                collection_name="issues",
                filters=None,
                k=k
            )
        
        # Sort by created date (most recent first)
        results.sort(key=lambda x: x["metadata"].get("created", ""), reverse=True)
        
        return results[:k]
    
    def _normalize_relevance_score(self, distance: float) -> float:
        """
        Normalize ChromaDB cosine distance to relevance score (0-1 range).
        
        ChromaDB cosine distance is typically 0-2, where:
        - 0: Perfect match
        - 1: Orthogonal  
        - 2: Opposite
        
        Most real results fall in range ~[0.8, 2.0] (semantically related text)
        We normalize this observed range to [0, 1] scale for better differentiation.
        """
        try:
            # Normalize based on observed range in semantic search results
            # Min distance (best match): ~0.8, Max distance (worst match): ~2.0
            # Linear normalization: (max - distance) / (max - min)
            min_dist = 0.8  # Typical best match
            max_dist = 2.0  # Typical worst match
            
            # Linear interpolation: lower distance = higher score
            normalized = (max_dist - distance) / (max_dist - min_dist)
            
            # Clamp to [0, 1] range
            return max(0.0, min(1.0, normalized))
        except:
            # Fallback
            return 0.5
    
    def _normalize_relevance_score_exponential(self, distance: float) -> float:
        """Exponential normalization with auto-calibration"""
        try:
            # More moderate exponential: -2.5 * distance
            score = math.exp(-2.5 * distance)
            return max(0.0, min(1.0, score))
        except:
            return 0.5
    
    def _generate_chunk_id(self, content: str) -> str:
        """Generate unique ID for chunk"""
        return hashlib.md5(content.encode()).hexdigest()[:16]