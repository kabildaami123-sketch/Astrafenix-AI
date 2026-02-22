# main.py
"""
Main entry point - Run the business report generator with integrated feedback loop
"""

import asyncio
import argparse
from dotenv import load_dotenv

from core.orchestrator import BusinessReportOrchestrator
from core.config import config
from utils.logger import logger

# Load environment variables
load_dotenv()

async def main():
    parser = argparse.ArgumentParser(description='Generate business-friendly code reports')
    parser.add_argument('repo_url', help='GitHub repository URL')
    parser.add_argument('--files', nargs='+', 
                       default=['README.md', 'app/__init__.py', 'app/models.py', 
                               'app/templates/base.html', 'app/templates/index.html'],
                       help='Files to analyze')
    
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("BUSINESS REPORT GENERATOR - Translating Code to Business Value")
    print("="*80)
    print(f"\nRepository: {args.repo_url}")
    print(f"Files to analyze: {len(args.files)}")
    
    # Validate config
    try:
        config.validate()
    except ValueError as e:
        print(f"\nConfiguration error: {e}")
        print("Please check your .env file")
        return
    
    # Run the orchestrator
    orchestrator = BusinessReportOrchestrator()
    html_report = await orchestrator.generate_report(args.repo_url, args.files)
    
    # Feedback loop: Ask user if they want to provide feedback
    print("\n" + "="*80)
    print("💬 FEEDBACK LOOP - Help Improve the Analysis")
    print("="*80)
    print("\nWould you like to provide feedback to improve the analysis?")
    print("Examples:")
    print("  • 'function authenticate should validate email format'")
    print("  • 'The checkout flow should include shipping address'")
    print("\nType your feedback (or press Ctrl+D / Ctrl+C to skip):")
    print("-"*80)
    
    feedback_lines = []
    try:
        while True:
            line = input()
            if line == "" and feedback_lines:
                if feedback_lines[-1] == "":
                    feedback_lines.pop()
                    break
                feedback_lines.append("")
            elif line != "":
                feedback_lines.append(line)
            elif line == "" and not feedback_lines:
                # If first input is empty, treat as skip
                break
    except EOFError:
        pass
    except KeyboardInterrupt:
        pass
    
    feedback_msg = "\n".join(feedback_lines).strip()
    
    if feedback_msg:
        print("\n📝 Processing your feedback...")
        result = orchestrator.ingest_feedback(feedback_msg)
        
        print(f"\n✅ {result.get('summary', 'Feedback processed')}")
        if result.get('applied'):
            print(f"\n📋 Applied corrections:")
            for item in result['applied'][:5]:
                file_name = item.get('file', '').split('/')[-1]
                print(f"   • [{file_name}] {item.get('target', 'unknown')}: {item.get('correction', '')[:50]}...")
        
        if result.get('skipped'):
            print(f"\n⚠️ Unhandled items (may need manual review):")
            for item in result['skipped'][:3]:
                print(f"   • Original: {item.get('original', 'N/A')[:40]}")
        
        print("\n✅ Feedback saved! The system will apply these improvements to future analyses.")
    else:
        print("\nℹ️  No feedback submitted. Exiting.")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    asyncio.run(main())