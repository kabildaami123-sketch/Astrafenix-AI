# ==================== REPORTING AGENT NODES ====================
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
from database_manager import DatabaseManager
# ==================== STATE DEFINITION ====================
class ReportingState(TypedDict):
    """State for the reporting agent"""
    developer_id: str
    developer_name: str
    answers: Dict[str, str]
    current_question_index: int
    structured_report: Dict[str, Any]
    generated_summary: str
    final_report: str
    report_id: Optional[int]
    should_continue: bool
    messages: Annotated[List[Dict[str, str]], add_messages]



# ==================== REPORTING AGENT NODES ====================
class ReportingWorkflow:
    """Complete reporting workflow using LangGraph"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.questions = [
            {
                "id": "tasks",
                "question": "1. What specific tasks did you complete today?",
                "field": "completed_tasks",
                "required": True
            },
            {
                "id": "progress",
                "question": "2. What's your progress percentage on your main task? (0-100)",
                "field": "progress_percentage",
                "required": True
            },
            {
                "id": "blockers",
                "question": "3. Are you facing any blockers or challenges?",
                "field": "blockers",
                "required": False
            },
            {
                "id": "tomorrow",
                "question": "4. What will you focus on tomorrow?",
                "field": "tomorrow_plan",
                "required": True
            },
            {
                "id": "notes",
                "question": "5. Any additional notes for the team?",
                "field": "additional_notes",
                "required": False
            }
        ]
    
    def build_graph(self):
        """Build the LangGraph for reporting workflow"""
        
        # Create workflow
        workflow = StateGraph(ReportingState)
        
        # Add nodes
        workflow.add_node("verify_developer", self.verify_developer_node)
        workflow.add_node("ask_questions", self.ask_questions_node)
        workflow.add_node("save_to_db", self.save_to_db_node)
        workflow.add_node("generate_report", self.generate_report_node)
        workflow.add_node("display_report", self.display_report_node)
        
        # Add edges with conditional routing
        workflow.set_entry_point("verify_developer")
        
        # Conditional: If verification succeeds, ask questions, else end
        workflow.add_conditional_edges(
            "verify_developer",
            self.decide_next_after_verification,
            {
                "continue": "ask_questions",
                "end": END
            }
        )
        
        # Conditional: After questions, decide next step
        workflow.add_conditional_edges(
            "ask_questions",
            self.decide_next_after_questions,
            {
                "continue": "save_to_db",
                "end": END
            }
        )
        
        # Linear flow for the rest
        workflow.add_edge("save_to_db", "generate_report")
        workflow.add_edge("generate_report", "display_report")
        workflow.add_edge("display_report", END)
        
        return workflow.compile()
    
    def decide_next_after_verification(self, state: ReportingState) -> str:
        """Decide next step after verification"""
        return "continue" if state.get("should_continue", False) else "end"
    
    def decide_next_after_questions(self, state: ReportingState) -> str:
        """Decide next step after questions"""
        return "continue" if state.get("should_continue", False) else "end"
    
    async def verify_developer_node(self, state: ReportingState) -> ReportingState:
        """Verify developer ID"""
        print("\n" + "="*60)
        print("🤖 Astrafenix AI - Daily Reporting System")
        print("="*60)
        
        # Get developer ID
        developer_id = input("\nEnter your Developer ID: ").strip()
        while not developer_id:
            print("❌ Developer ID is required!")
            developer_id = input("Enter your Developer ID: ").strip()
        
        # Verify developer exists
        verified, developer_name = self.db_manager.verify_developer(developer_id)
        
        if not verified:
            print(f"❌ Developer ID '{developer_id}' not found in team members.")
            print("   Please check your ID or contact your team lead.")
            state["should_continue"] = False
            return state
        
        state["developer_id"] = developer_id
        state["developer_name"] = developer_name
        state["should_continue"] = True
        
        print(f"\n✅ Welcome, {developer_name}!")
        print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d')}")
        
        confirm = input("\nProceed with daily report? (Y/n): ").strip().lower()
        state["should_continue"] = confirm not in ['n', 'no']
        
        return state
    
    async def ask_questions_node(self, state: ReportingState) -> ReportingState:
        """Ask all 5 questions"""
        if not state.get("should_continue", True):
            return state
        
        print("\n" + "="*60)
        print(f"📝 Daily Report - {state['developer_name']}")
        print("="*60)
        print("\nPlease answer these 5 questions:\n")
        
        state["answers"] = {}
        
        for i, q in enumerate(self.questions):
            print("-" * 50)
            print(f"\n{q['question']}")
            if q['required']:
                print("(Required)")
            
            while True:
                answer = input("\nYour answer: ").strip()
                
                if not answer and q['required']:
                    print("❌ This field is required.")
                    continue
                
                # Validate progress percentage
                if q['id'] == 'progress':
                    try:
                        clean = ''.join(c for c in answer if c.isdigit())
                        if not clean:
                            print("❌ Please enter a number (0-100)")
                            continue
                        progress = int(clean)
                        if progress < 0 or progress > 100:
                            print("❌ Progress must be 0-100")
                            continue
                        answer = f"{progress}%"
                    except ValueError:
                        print("❌ Please enter a valid number")
                        continue
                
                state["answers"][q['field']] = answer
                break
        
        # Show summary
        print("\n" + "="*60)
        print(" Your Answers Summary:")
        print("-" * 40)
        for field, answer in state["answers"].items():
            display = field.replace('_', ' ').title()
            print(f"• {display}: {answer}")
        
        confirm = input("\nProceed? (Y/n): ").strip().lower()
        state["should_continue"] = confirm not in ['n', 'no']
        
        return state
    
    async def save_to_db_node(self, state: ReportingState) -> ReportingState:
        """Save answers to database"""
        if not state.get("should_continue", True):
            return state
        
        print("\n" + "="*60)
        print(" Saving to Database...")
        
        conn = self.db_manager.get_connection()
        if not conn:
            state["should_continue"] = False
            return state
        
        try:
            cursor = conn.cursor()
            
            # Ensure developer exists
            upsert_dev = """
            INSERT INTO team_members (developer_id, developer_name)
            VALUES (%s, %s)
            ON CONFLICT (developer_id) DO UPDATE 
            SET developer_name = EXCLUDED.developer_name
            """
            cursor.execute(upsert_dev, (state["developer_id"], state["developer_name"]))
            
            # Calculate progress
            progress_str = state["answers"].get('progress_percentage', '0%')
            try:
                clean = ''.join(c for c in progress_str if c.isdigit())
                progress = int(clean) if clean else 0
            except (ValueError, TypeError):
                progress = 0
            progress = max(0, min(100, progress))
            
            # Create summary
            summary = f"Progress: {progress}%"
            tasks = state["answers"].get('completed_tasks', '')
            if tasks:
                first_task = tasks.split('.')[0][:30]
                summary = f"{first_task} | {summary}"
            
            # Insert report
            insert_query = """
            INSERT INTO developer_reports 
            (developer_id, developer_name, date, raw_responses, summary, progress_percentage, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (developer_id, date) DO UPDATE SET
                raw_responses = EXCLUDED.raw_responses,
                summary = EXCLUDED.summary,
                progress_percentage = EXCLUDED.progress_percentage,
                status = EXCLUDED.status,
                updated_at = NOW()
            RETURNING report_id
            """
            
            cursor.execute(insert_query, (
                state["developer_id"],
                state["developer_name"],
                datetime.now().date(),
                json.dumps(state["answers"]),
                summary,
                progress,
                'submitted'
            ))
            
            result = cursor.fetchone()
            if result:
                state["report_id"] = result[0]
                print(f"✅ Report saved (ID: {state['report_id']})")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"❌ Database error: {e}")
            state["should_continue"] = False
        
        return state
    
    async def generate_report_node(self, state: ReportingState) -> ReportingState:
        """Generate AI report"""
        if not state.get("should_continue", True):
            return state
        
        print("\n" + "="*60)
        print(" Generating AI Report...")
        
        # Prepare data
        tasks = state["answers"].get('completed_tasks', '')
        progress = state["answers"].get('progress_percentage', '0%').replace('%', '')
        
        # Format blockers
        blockers = state["answers"].get('blockers', '')
        if not blockers or blockers.lower() in ['no', 'none', 'n/a', '']:
            blockers_text = "No blockers reported"
        else:
            blockers_text = blockers
        
        tomorrow = state["answers"].get('tomorrow_plan', '')
        notes = state["answers"].get('additional_notes', '')
        
        prompt = f"""Create a professional daily report:

DEVELOPER: {state['developer_name']}
DATE: {datetime.now().strftime('%Y-%m-%d')}

TASKS: {tasks}
PROGRESS: {progress}%
BLOCKERS: {blockers_text}
TOMORROW: {tomorrow}
NOTES: {notes}

Format as a professional daily report.
"""
        
        try:
            response = ollama.chat(
                model="llama3.1:8b",
                messages=[
                    {
                        "role": "system",
                        "content": "You create professional daily reports."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                options={
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "num_predict": 500
                }
            )
            
            state["final_report"] = response['message']['content']
            print("✅ Report generated successfully!")
            
        except Exception as e:
            print(f"⚠️  AI generation failed: {e}")
            state["final_report"] = self._generate_template_report(state)
        
        return state
    
    def _generate_template_report(self, state: ReportingState) -> str:
        """Generate template-based report"""
        tasks = state["answers"].get('completed_tasks', 'No tasks completed')
        progress = state["answers"].get('progress_percentage', '0%')
        
        # Format blockers
        blockers = state["answers"].get('blockers', '')
        if not blockers or blockers.lower() in ['no', 'none', 'n/a', '']:
            blockers_text = "No blockers reported"
        else:
            blockers_text = blockers
        
        tomorrow = state["answers"].get('tomorrow_plan', 'No plan specified')
        notes = state["answers"].get('additional_notes', 'No additional notes')
        
        report = f"""
## Daily Report - {datetime.now().strftime('%Y-%m-%d')}
**Developer:** {state['developer_name']}

### Executive Summary
{state['developer_name']} reported on today's work with {progress} progress.

### Tasks Completed
{tasks}

### Progress Status
Progress: {progress}

### Blockers & Challenges
{blockers_text}

### Tomorrow's Plan
{tomorrow}

### Additional Notes
{notes}
"""
        return report
    
    async def display_report_node(self, state: ReportingState) -> ReportingState:
        """Display final report"""
        if not state.get("should_continue", True):
            return state
        
        print("\n" + "="*60)
        print(" FINAL DAILY REPORT")
        print("="*60 + "\n")
        
        if state.get("final_report"):
            print(state["final_report"])
        else:
            print("❌ No report generated.")
        
        print("\n" + "="*60)
        print(f"✅ Report for: {state['developer_name']}")
        if state.get("report_id"):
            print(f"📊 Database ID: {state['report_id']}")
        print("="*60)
        
        return state
