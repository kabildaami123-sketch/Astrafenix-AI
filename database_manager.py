# ==================== DATABASE MANAGER ====================

import json
import os
import sys
import asyncio
from datetime import datetime, date
from typing import Dict, Any, TypedDict, Annotated, Optional, List
import psycopg2
import ollama
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from dotenv import load_dotenv

load_dotenv()
class DatabaseManager:
    """Manages database connections and operations"""
    
    def __init__(self):
        self.config = {
            "host": os.getenv("DB_HOST"),
            "database": os.getenv("DB_NAME"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD")
        }
    
    def get_connection(self):
        """Get database connection"""
        try:
            conn = psycopg2.connect(**self.config)
            conn.autocommit = True
            return conn
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return None
    
    def verify_developer(self, developer_id: str) -> tuple[bool, Optional[str]]:
        """Verify if developer exists in team_members table"""
        conn = self.get_connection()
        if not conn:
            return False, None
        
        try:
            cursor = conn.cursor()
            query = """
            SELECT developer_name, team_id FROM team_members 
            WHERE developer_id = %s
            """
            cursor.execute(query, (developer_id,))
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if result:
                name = result[0]
                team = result[1]
                if team:
                    return True, f"{name} (Team: {team})"
                return True, name
            return False, None
            
        except Exception as e:
            print(f"❌ Verification error: {e}")
            return False, None