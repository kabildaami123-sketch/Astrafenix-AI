# main.py
"""
Multi-Agent System with LangGraph Orchestration
"""

import asyncio
import argparse
from dotenv import load_dotenv

from core.graph import AgentGraph
from core.config import config
from utils.logger import logger

# Load environment variables
load_dotenv()

async def main():
    parser = argparse.ArgumentParser(description='Multi-Agent Code Analysis System')
    parser.add_argument('repo_url', help='GitHub repository URL')
    parser.add_argument('--files', nargs='+', 
                       default=['README.md', 'app/__init__.py', 'app/models.py', 
                               'app/templates/base.html', 'app/templates/index.html'],
                       help='Files to analyze')
    
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("🚀 LANGRAPH MULTI-AGENT SYSTEM - Code to Business Value")
    print("="*80)
    print(f"\n📦 Repository: {args.repo_url}")
    print(f"📁 Files to analyze: {len(args.files)}")
    
    # Validate config
    try:
        config.validate()
    except ValueError as e:
        print(f"\n❌ Configuration error: {e}")
        print("Please check your .env file")
        return
    
    # Initialize and run LangGraph
    graph = AgentGraph()
    result = await graph.run(args.repo_url, args.files)
    
    # Print the beautiful report
    print("\n" + result['report_text'])
    
    # Print node execution times
    print("\n" + "="*60)
    print("⏱️  NODE EXECUTION TIMES")
    print("="*60)
    for node, exec_time in result.get('node_execution_times', {}).items():
        print(f"  • {node:20s}: {exec_time:.3f}s")
    print(f"\n  • {'TOTAL':20s}: {result['processing_time']:.3f}s")
    
    # Print summary
    print("\n" + "="*60)
    print("📊 LANGRAPH WORKFLOW SUMMARY")
    print("="*60)
    print(f"Nodes executed: fetch → analyze → translate → report → feedback → learn")
    print(f"Files analyzed: {result['files_fetched']}/{result['total_requested']}")
    print(f"Business rules: {len(result.get('business_rules', []))}")
    print(f"Features found: {len(result.get('features_found', []))}")
    print(f"Final confidence: {result.get('confidence_score', 0)*100:.1f}%")
    print(f"Corrections learned: {len(result.get('corrections', []))}")
    print(f"Patterns stored: {len(result.get('successful_patterns', [])) + len(result.get('failed_patterns', []))}")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())