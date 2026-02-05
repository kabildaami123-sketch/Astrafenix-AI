# with_langgraph.py
#!/usr/bin/env python3
"""
Astrafenix AI - LangGraph Integrated System 
"""
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
from orchestrator import Orchestrator
# ==================== MAIN ====================
async def main():
    """Main entry point"""
    system = Orchestrator()
    await system.run()


if __name__ == "__main__":
    # Run async main
    asyncio.run(main())