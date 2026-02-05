# ==================== MAIN INTEGRATED SYSTEM ====================
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
from reporting_agent import ReportingWorkflow   
from summarizing_agent import SummarizingWorkflow   


class Orchestrator:
    def __init__(self):
        # Initialize workflows
        self.reporting_workflow = ReportingWorkflow()
        self.summarizing_workflow = SummarizingWorkflow()
        
        # Build graphs
        self.reporting_graph = self.reporting_workflow.build_graph()
        self.summarizing_graph = self.summarizing_workflow.build_graph()
    
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_menu(self):
        """Print main menu"""
        self.clear_screen()
        print("\n" + "="*60)
        print("🤖 Astrafenix AI - Powered by LangGraph")
        print("="*60)
        print("\nPlease choose an option:\n")
        print("1.  Submit Daily Report (Individual Developer)")
        print("2.  Generate Team Summary (Team Lead/Manager)")
        print("0.  Exit System")
        print("\n" + "-"*60)
    
    async def run_reporting_agent(self):
        """Run the reporting agent workflow"""
        print("\n" + "="*60)
        print(" Starting Daily Report Submission...")
        print("="*60)
        
        # Initial state
        initial_state = {
            "developer_id": "",
            "developer_name": "",
            "answers": {},
            "current_question_index": 0,
            "structured_report": {},
            "generated_summary": "",
            "final_report": "",
            "report_id": None,
            "should_continue": True,
            "messages": []
        }
        
        try:
            # Execute the workflow
            result = await self.reporting_graph.ainvoke(initial_state)
            
            print("\n" + "="*60)
            print("✅ Daily report workflow completed!")
            print("="*60)
            
        except Exception as e:
            print(f"❌ Error in reporting workflow: {e}")
    
    async def run_summarizing_agent(self):
        """Run the summarizing agent workflow"""
        print("\n" + "="*70)
        print(" Starting Team Summary Generation...")
        print("="*70)
        
        # Initial state
        initial_state = {
            "team_id": "",
            "summary_date": date.today(),
            "developer_reports": [],
            "team_summary": {},
            "final_team_report": "",
            "summary_id": None,
            "should_continue": True,
            "messages": []
        }
        
        try:
            # Execute the workflow
            result = await self.summarizing_graph.ainvoke(initial_state)
            
            print("\n" + "="*70)
            print("✅ Team summary workflow completed!")
            print("="*70)
            
        except Exception as e:
            print(f"❌ Error in summarizing workflow: {e}")
    
    async def run(self):
        """Main execution loop"""
        print("\n" + "="*60)
        print("🤖 Welcome to Astrafenix AI Reporting System")
        print("="*60)
        print(" Powered by LangGraph\n")
        
        running = True
        
        while running:
            try:
                self.print_menu()
                choice = input("\nEnter your choice (0-2): ").strip()
                
                if choice == "0":
                    print("\n👋 Thank you for using Astrafenix AI!")
                    running = False
                
                elif choice == "1":
                    await self.run_reporting_agent()
                    input("\nPress Enter to return to main menu...")
                
                elif choice == "2":
                    await self.run_summarizing_agent()
                    input("\nPress Enter to return to main menu...")
                
                else:
                    print(f"\n❌ Invalid choice: '{choice}'. Please enter 0, 1, or 2.")
                    input("Press Enter to continue...")
            
            except KeyboardInterrupt:
                print("\n\n⏹️  Process interrupted.")
                running = False
            
            except Exception as e:
                print(f"\n❌ Unexpected error: {e}")