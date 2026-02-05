# ==================== SUMMARIZING AGENT WORKFLOW ====================
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
from reporting_agent import ReportingWorkflow


# ==================== STATE DEFINITION ====================
class SummarizingState(TypedDict):
    """State for the summarizing agent"""
    team_id: str
    summary_date: date
    developer_reports: List[Dict[str, Any]]
    team_summary: Dict[str, Any]
    final_team_report: str
    summary_id: Optional[int]
    should_continue: bool
    messages: Annotated[List[Dict[str, str]], add_messages]


# ==================== summarizing AGENT NODES ====================
class SummarizingWorkflow:    
    def __init__(self):
        self.db_manager = DatabaseManager()
    
    def build_graph(self):
        """Build the LangGraph for summarizing workflow"""
        
        # Create workflow
        workflow = StateGraph(SummarizingState)
        
        # Add nodes
        workflow.add_node("get_team_info", self.get_team_info_node)
        workflow.add_node("fetch_reports", self.fetch_reports_node)
        workflow.add_node("generate_summary", self.generate_summary_node)
        workflow.add_node("save_summary", self.save_summary_node)
        workflow.add_node("display_summary", self.display_summary_node)
        
        # Add edges with conditional routing
        workflow.set_entry_point("get_team_info")
        
        # Conditional routing
        workflow.add_conditional_edges(
            "get_team_info",
            self.decide_next_after_team_info,
            {
                "continue": "fetch_reports",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "fetch_reports",
            self.decide_next_after_fetch,
            {
                "continue": "generate_summary",
                "end": END
            }
        )
        
        # Linear flow for the rest
        workflow.add_edge("generate_summary", "save_summary")
        workflow.add_edge("save_summary", "display_summary")
        workflow.add_edge("display_summary", END)
        
        return workflow.compile()
    
    def decide_next_after_team_info(self, state: SummarizingState) -> str:
        """Decide next step after getting team info"""
        return "continue" if state.get("should_continue", False) else "end"
    
    def decide_next_after_fetch(self, state: SummarizingState) -> str:
        """Decide next step after fetching reports"""
        return "continue" if state.get("should_continue", False) else "end"
    
    async def get_team_info_node(self, state: SummarizingState) -> SummarizingState:
        """Get team information"""
        print("\n" + "="*70)
        print("🤖 Astrafenix AI - Team Summarizing Agent")
        print("="*70)
        
        # Get team ID
        team_id = input("\nEnter Team ID: ").strip()
        while not team_id:
            print("❌ Team ID is required!")
            team_id = input("Enter Team ID: ").strip()
        
        # Get date
        date_input = input(f"Enter date (YYYY-MM-DD, default: {date.today()}): ").strip()
        if date_input:
            try:
                summary_date = datetime.strptime(date_input, '%Y-%m-%d').date()
            except ValueError:
                print("❌ Invalid date format. Using today.")
                summary_date = date.today()
        else:
            summary_date = date.today()
        
        state["team_id"] = team_id
        state["summary_date"] = summary_date
        state["should_continue"] = True
        
        print(f"\n🏢 Team: {team_id}")
        print(f"📅 Date: {summary_date}")
        
        confirm = input("\nProceed? (Y/n): ").strip().lower()
        state["should_continue"] = confirm not in ['n', 'no']
        
        return state
    
    async def fetch_reports_node(self, state: SummarizingState) -> SummarizingState:
        """Fetch developer reports"""
        if not state.get("should_continue", True):
            return state
        
        print("\n" + "="*70)
        print("📋 Fetching Developer Reports...")
        
        conn = self.db_manager.get_connection()
        if not conn:
            state["should_continue"] = False
            return state
        
        try:
            cursor = conn.cursor()
            
            query = """
            SELECT 
                dr.report_id,
                dr.developer_id,
                dr.developer_name,
                dr.date,
                dr.raw_responses,
                dr.summary,
                dr.progress_percentage,
                dr.status,
                tm.team_id
            FROM developer_reports dr
            LEFT JOIN team_members tm ON dr.developer_id = tm.developer_id
            WHERE dr.date = %s 
                AND (tm.team_id = %s OR %s = 'all')
            ORDER BY dr.developer_name
            """
            
            cursor.execute(query, (state["summary_date"], state["team_id"], state["team_id"]))
            results = cursor.fetchall()
            
            if not results:
                print(f"❌ No reports found for team '{state['team_id']}' on {state['summary_date']}")
                state["should_continue"] = False
                cursor.close()
                conn.close()
                return state
            
            # Process results
            state["developer_reports"] = []
            for row in results:
                report = {
                    'report_id': row[0],
                    'developer_id': row[1],
                    'developer_name': row[2],
                    'date': row[3],
                    'raw_responses': row[4],
                    'summary': row[5],
                    'progress_percentage': row[6],
                    'status': row[7],
                    'team_id': row[8]
                }
                state["developer_reports"].append(report)
            
            print(f"✅ Found {len(state['developer_reports'])} report(s)")
            
            # Display summary
            print("\n📊 Reports Summary:")
            print("-" * 50)
            
            total_progress = 0
            for report in state["developer_reports"]:
                dev_name = report['developer_name']
                progress = report['progress_percentage']
                summary = report['summary'][:60] + '...' if len(report['summary']) > 60 else report['summary']
                
                print(f"👤 {dev_name:<20} | 🎯 {progress:>3}% | 📝 {summary}")
                total_progress += progress
            
            avg_progress = total_progress / len(state["developer_reports"]) if state["developer_reports"] else 0
            print("-" * 50)
            print(f"📈 Average Progress: {avg_progress:.1f}%")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"❌ Error fetching reports: {e}")
            state["should_continue"] = False
        
        return state
    
    async def generate_summary_node(self, state: SummarizingState) -> SummarizingState:
        """Generate team summary"""
        if not state.get("should_continue", True):
            return state
        
        print("\n" + "="*70)
        print("🤖 Generating Team Summary...")
        
        # Organize data
        organized_data = self._organize_report_data(state)
        
        # Generate summary using AI
        try:
            summary_text = await self._generate_ai_summary(organized_data)
            
            state["team_summary"] = {
                'team_id': state["team_id"],
                'date': state["summary_date"].isoformat(),
                'total_developers': len(state["developer_reports"]),
                'reports_submitted': len(state["developer_reports"]),
                'overall_progress': organized_data['average_progress'],
                'blockers_count': organized_data['blockers_count'],
                'summary_text': summary_text,
                'action_items': self._extract_action_items(summary_text),
                'risk_level': self._assess_risk_level(organized_data)
            }
            
            print("✅ Team summary generated!")
            
        except Exception as e:
            print(f"⚠️  AI summary failed: {e}")
            state["team_summary"] = self._generate_basic_summary(state, organized_data)
        
        return state
    
    def _organize_report_data(self, state: SummarizingState) -> Dict[str, Any]:
        """Organize report data"""
        organized = {
            'team_id': state["team_id"],
            'date': state["summary_date"].isoformat(),
            'developers': [],
            'average_progress': 0,
            'blockers_count': 0
        }
        
        total_progress = 0
        blockers_count = 0
        
        for report in state["developer_reports"]:
            raw_responses = report['raw_responses']
            if isinstance(raw_responses, str):
                try:
                    responses = json.loads(raw_responses)
                except:
                    responses = {}
            else:
                responses = raw_responses or {}
            
            developer_data = {
                'name': report['developer_name'],
                'progress': report['progress_percentage'],
                'tasks': responses.get('completed_tasks', 'Not specified'),
                'blockers': responses.get('blockers', 'None'),
                'tomorrow_plan': responses.get('tomorrow_plan', 'Not specified'),
                'notes': responses.get('additional_notes', 'None')
            }
            
            organized['developers'].append(developer_data)
            total_progress += developer_data['progress']
            
            if developer_data['blockers'] and developer_data['blockers'].lower() not in ['no', 'none', 'n/a']:
                blockers_count += 1
        
        organized['average_progress'] = round(total_progress / len(state["developer_reports"]), 2) if state["developer_reports"] else 0
        organized['blockers_count'] = blockers_count
        
        return organized
    
    async def _generate_ai_summary(self, organized_data: Dict[str, Any]) -> str:
        """Generate AI summary"""
        developers_text = ""
        for dev in organized_data['developers']:
            developers_text += f"{dev['name']}: {dev['progress']}% progress"
            if dev['blockers'].lower() not in ['no', 'none']:
                developers_text += f" | Blocker: {dev['blockers']}"
            developers_text += "\n"
        
        prompt = f"""Create a team daily summary:

TEAM: {organized_data['team_id']}
DATE: {organized_data['date']}
DEVELOPERS: {len(organized_data['developers'])}
AVG PROGRESS: {organized_data['average_progress']}%
BLOCKERS: {organized_data['blockers_count']}

INDIVIDUAL REPORTS:
{developers_text}

Create a professional team summary report.
"""
        
        response = ollama.chat(
            model="llama3.1:8b",
            messages=[
                {
                    "role": "system",
                    "content": "You are a project manager creating team summaries."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            options={
                "temperature": 0.3,
                "top_p": 0.9,
                "num_predict": 800
            }
        )
        
        return response['message']['content']
    
    def _extract_action_items(self, summary_text: str) -> List[str]:
        """Extract action items"""
        action_items = []
        lines = summary_text.split('\n')
        
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in ['action:', 'todo:', 'need to', 'should', 'must']):
                clean_line = line.strip('•-* ').strip()
                if clean_line and len(clean_line) > 10:
                    action_items.append(clean_line)
        
        return action_items[:3] or ["Review progress", "Address blockers"]
    
    def _assess_risk_level(self, organized_data: Dict[str, Any]) -> str:
        """Assess risk level"""
        if organized_data['blockers_count'] > len(organized_data['developers']) * 0.5:
            return "high"
        elif organized_data['average_progress'] < 50:
            return "medium"
        elif organized_data['blockers_count'] > 0:
            return "low"
        else:
            return "none"
    
    def _generate_basic_summary(self, state: SummarizingState, organized_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate basic summary"""
        summary_text = f"""
TEAM SUMMARY - {state['team_id']}
Date: {state['summary_date']}

Overview:
- Developers: {len(state['developer_reports'])}
- Avg Progress: {organized_data['average_progress']}%
- Blockers: {organized_data['blockers_count']}

Individual Progress:
"""
        
        for dev in organized_data['developers']:
            summary_text += f"- {dev['name']}: {dev['progress']}%\n"
        
        return {
            'team_id': state["team_id"],
            'date': state["summary_date"].isoformat(),
            'total_developers': len(state["developer_reports"]),
            'reports_submitted': len(state["developer_reports"]),
            'overall_progress': organized_data['average_progress'],
            'blockers_count': organized_data['blockers_count'],
            'summary_text': summary_text,
            'action_items': ["Review progress", "Address blockers"],
            'risk_level': 'low'
        }
    
    async def save_summary_node(self, state: SummarizingState) -> SummarizingState:
        """Save team summary to database"""
        if not state.get("should_continue", True) or "team_summary" not in state:
            return state
        
        print("\n" + "="*70)
        print(" Saving Team Summary...")
        
        conn = self.db_manager.get_connection()
        if not conn:
            return state
        
        try:
            cursor = conn.cursor()
            
            query = """
            INSERT INTO team_daily_summary 
            (team_id, date, total_developers, reports_submitted, overall_progress, 
             blockers_count, summary_report, action_items, risk_level)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (team_id, date) DO UPDATE SET
                total_developers = EXCLUDED.total_developers,
                reports_submitted = EXCLUDED.reports_submitted,
                overall_progress = EXCLUDED.overall_progress,
                blockers_count = EXCLUDED.blockers_count,
                summary_report = EXCLUDED.summary_report,
                action_items = EXCLUDED.action_items,
                risk_level = EXCLUDED.risk_level
            RETURNING id
            """
            
            cursor.execute(query, (
                state["team_summary"]['team_id'],
                state["summary_date"],
                state["team_summary"]['total_developers'],
                state["team_summary"]['reports_submitted'],
                float(state["team_summary"]['overall_progress']),
                state["team_summary"]['blockers_count'],
                state["team_summary"]['summary_text'],
                json.dumps(state["team_summary"]['action_items']),
                state["team_summary"]['risk_level']
            ))
            
            result = cursor.fetchone()
            if result:
                state["summary_id"] = result[0]
                print(f"✅ Team summary saved (ID: {state['summary_id']})")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"❌ Error saving summary: {e}")
        
        return state
    
    async def display_summary_node(self, state: SummarizingState) -> SummarizingState:
        """Display team summary"""
        if not state.get("should_continue", True) or "team_summary" not in state:
            return state
        
        print("\n" + "="*70)
        print(" TEAM DAILY REPORT")
        print("="*70 + "\n")
        
        if state["team_summary"].get('summary_text'):
            print(state["team_summary"]['summary_text'])
        else:
            print("❌ No summary generated.")
        
        print("\n" + "="*70)
        print(f"🏢 Team: {state['team_id']}")
        print(f"📅 Date: {state['summary_date']}")
        print(f"👥 Reports: {len(state['developer_reports'])}")
        print(f"📈 Avg Progress: {state['team_summary'].get('overall_progress', 0):.1f}%")
        if state.get("summary_id"):
            print(f"💾 Database ID: {state['summary_id']}")
        print("="*70)
        
        return state
