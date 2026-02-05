from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List, Dict, Any
import json

class JiraSmartChunker:
    def __init__(self):
        # Different chunk sizes for different content types
        self.chunkers = {
            "project": RecursiveCharacterTextSplitter(
                chunk_size=1500,
                chunk_overlap=300,
                separators=["\n\n", "\n", ". ", " ", ""]
            ),
            "issue": RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                separators=["\n\n", "\n", ". ", " ", ""]
            ),
            "comment": RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=100,
                separators=["\n", ". ", " ", ""]
            )
        }
    
    def chunk_project_data(self, project_data: Dict) -> List[Dict]:
        """Chunk project information for RAG"""
        
        chunks = []
        
        # Chunk 1: Project overview
        overview_text = f"""
        Project: {project_data['name']} ({project_data['key']})
        Description: {project_data.get('description', 'No description')}
        Lead: {project_data['lead']['name']} ({project_data['lead']['email']})
        Components: {', '.join([c['name'] for c in project_data['components']])}
        Versions: {', '.join([v['name'] for v in project_data['versions']])}
        """
        
        overview_chunks = self.chunkers["project"].split_text(overview_text)
        
        for i, chunk in enumerate(overview_chunks):
            chunks.append({
                "content": chunk,
                "metadata": {
                    "type": "project_overview",
                    "project_key": project_data["key"],
                    "chunk_id": f"project_{project_data['key']}_overview_{i}",
                    "tags": "project,overview,metadata"
                }
            })
        
        # Chunk 2: Team members
        team_members = project_data.get("custom_fields", {}).get("team_members", [])
        if team_members:
            team_text = "Project Team Members:\n"
            for member in team_members:
                team_text += f"- {member['name']}: {member['role']}"
                if member.get('email'):
                    team_text += f" ({member['email']})"
                team_text += "\n"
            
            team_chunks = self.chunkers["project"].split_text(team_text)
            
            for i, chunk in enumerate(team_chunks):
                chunks.append({
                    "content": chunk,
                    "metadata": {
                        "type": "team_members",
                        "project_key": project_data["key"],
                        "chunk_id": f"project_{project_data['key']}_team_{i}",
                        "tags": "team,members,staff,collaboration"
                    }
                })
        
        # Chunk 3: Components (teams/groups)
        for component in project_data.get("components", []):
            component_text = f"""
            Component: {component['name']}
            Description: {component.get('description', 'No description')}
            Lead: {component.get('lead', 'No lead assigned')}
            """
            
            component_chunks = self.chunkers["project"].split_text(component_text)
            
            for i, chunk in enumerate(component_chunks):
                chunks.append({
                    "content": chunk,
                    "metadata": {
                        "type": "component",
                        "project_key": project_data["key"],
                        "component_id": component["id"],
                        "component_name": component["name"],
                        "chunk_id": f"component_{component['id']}_{i}",
                        "tags": "component,team,subteam,group"
                    }
                })
        
        return chunks
    
    def chunk_issue_data(self, issue_data: Dict) -> List[Dict]:
        """Chunk issue information for RAG with semantic relationships"""
        
        chunks = []
        
        # Chunk 1: Issue core information
        core_text = f"""
        Issue: {issue_data['key']} - {issue_data['summary']}
        Type: {issue_data['issuetype']['name']}
        Status: {issue_data['status']['name']}
        Priority: {issue_data['priority']['name']}
        Assignee: {issue_data['assignee']['name']}
        
        Description:
        {issue_data.get('description', 'No description provided')}
        
        Created: {issue_data['created']}
        Updated: {issue_data['updated']}
        Due Date: {issue_data.get('duedate', 'No due date')}
        
        Labels: {', '.join(issue_data['labels'])}
        Components: {', '.join([c['name'] for c in issue_data['components']])}
        
        Time Estimate: {issue_data['timeoriginalestimate']} seconds
        Time Spent: {issue_data['timespent']} seconds
        """
        
        core_chunks = self.chunkers["issue"].split_text(core_text)
        
        for i, chunk in enumerate(core_chunks):
            chunks.append({
                "content": chunk,
                "metadata": {
                    "type": "issue_core",
                    "chunk_id": f"issue_{issue_data['key']}_core_{i}",
                    "primary_key": issue_data['key'],
                    "issue_key": issue_data['key'],
                    "status": issue_data['status']['name'],
                    "priority": issue_data['priority']['name'],
                    "assignee": issue_data['assignee']['name'],
                    "issuetype": issue_data['issuetype']['name'],
                    "created": issue_data['created'],
                    "updated": issue_data['updated'],
                    "tags": ",".join(["issue", "core", "metadata"])
                }
            })
        
        # Chunk 2: Comments (developer updates)
        for comment in issue_data.get('comments', []):
            comment_text = f"""
            Comment by {comment['author']} on {comment['created']}:
            {comment['body']}
            """
            
            comment_chunks = self.chunkers["comment"].split_text(comment_text)
            
            for i, chunk in enumerate(comment_chunks):
                chunks.append({
                    "content": chunk,
                    "metadata": {
                        "type": "comment",
                        "issue_key": issue_data['key'],
                        "author": comment['author'],
                        "timestamp": comment['created'],
                        "comment_id": comment['id'],
                        "chunk_id": f"comment_{comment['id']}_{i}",
                        "tags": ",".join(["comment", "developer_update", "communication", "progress"] + 
                                self._detect_comment_type(comment['body']))
                    }
                })
        
        # Chunk 3: Worklogs (time tracking)
        if issue_data.get('worklogs'):
            worklog_text = "Time Tracking:\n"
            for worklog in issue_data['worklogs']:
                worklog_text += f"- {worklog['author']}: {worklog['timeSpent']} on {worklog['started']}"
                if worklog.get('comment'):
                    worklog_text += f" - {worklog['comment']}"
                worklog_text += "\n"
            
            worklog_chunks = self.chunkers["comment"].split_text(worklog_text)
            
            for i, chunk in enumerate(worklog_chunks):
                chunks.append({
                    "content": chunk,
                    "metadata": {
                        "type": "worklog",
                        "issue_key": issue_data['key'],
                        "chunk_id": f"worklog_{issue_data['key']}_{i}",
                        "tags": "worklog,time_tracking,billing,hours"
                    }
                })
        
        return chunks
    
    def _detect_comment_type(self, comment_text: str) -> List[str]:
        """Detect the type of comment for semantic tagging"""
        text_lower = comment_text.lower()
        types = []
        
        if any(word in text_lower for word in ['fixed', 'resolved', 'completed', 'done']):
            types.append("resolution")
        if any(word in text_lower for word in ['error', 'bug', 'issue', 'problem', 'broken']):
            types.append("problem_report")
        if any(word in text_lower for word in ['question', '?', 'what about', 'should i']):
            types.append("question")
        if any(word in text_lower for word in ['@', 'ping', 'mention', 'review']):
            types.append("collaboration")
        if any(word in text_lower for word in ['blocked', 'stuck', 'cannot', 'unable']):
            types.append("blocker")
        if any(word in text_lower for word in ['test', 'testing', 'qa', 'verified']):
            types.append("testing")
        
        return types