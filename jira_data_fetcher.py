import requests
import json
from datetime import datetime
from typing import Dict, List, Any
import base64

class JiraDataFetcher:
    def __init__(self, domain: str, email: str, api_token: str):
        # Handle both full URL and domain-only formats
        if domain.startswith("http"):
            self.base_url = domain
        else:
            self.base_url = f"https://{domain}.atlassian.net"
        
        print(f"[*] Using Jira instance: {self.base_url}")
        self.auth_header = self._create_auth_header(email, api_token)
        self.session = requests.Session()
        self.session.headers.update(self.auth_header)
    
    def _create_auth_header(self, email: str, api_token: str) -> Dict:
        auth_string = f"{email}:{api_token}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        return {
            "Authorization": f"Basic {encoded_auth}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    def fetch_project_details(self, project_key: str) -> Dict:
        """Fetch complete project details including custom fields"""
        
        # Get basic project info
        project_url = f"{self.base_url}/rest/api/3/project/{project_key}"
        response = self.session.get(project_url)
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch project: {response.text}")
        
        project_data = response.json()
        
        # Get custom fields (where team data is stored)
        custom_fields = self._extract_custom_fields(project_key)
        
        # Get project components (teams/groups)
        components_url = f"{self.base_url}/rest/api/3/project/{project_key}/components"
        components_response = self.session.get(components_url)
        components = components_response.json() if components_response.status_code == 200 else []
        
        # Get project versions
        versions_url = f"{self.base_url}/rest/api/3/project/{project_key}/versions"
        versions_response = self.session.get(versions_url)
        versions = versions_response.json() if versions_response.status_code == 200 else []
        
        # Structure the project data
        structured_project = {
            "id": project_data.get("id"),
            "key": project_data.get("key"),
            "name": project_data.get("name"),
            "description": project_data.get("description", ""),
            "lead": {
                "name": project_data.get("lead", {}).get("displayName", ""),
                "email": project_data.get("lead", {}).get("emailAddress", "")
            },
            "components": [
                {
                    "id": comp.get("id"),
                    "name": comp.get("name"),
                    "description": comp.get("description", ""),
                    "lead": comp.get("lead", {}).get("displayName", "") if comp.get("lead") else ""
                }
                for comp in components
            ],
            "versions": [
                {
                    "id": ver.get("id"),
                    "name": ver.get("name"),
                    "description": ver.get("description", ""),
                    "releaseDate": ver.get("releaseDate", "")
                }
                for ver in versions
            ],
            "custom_fields": custom_fields,
            "fetched_at": datetime.now().isoformat()
        }
        
        return structured_project
    
    def _extract_custom_fields(self, project_key: str) -> Dict:
        """Extract custom fields that contain team/staff information"""
        
        # Search for issues with custom field patterns
        jql = f'project = {project_key} AND "Team[Member]" IS NOT EMPTY'
        
        search_url = f"{self.base_url}/rest/api/3/search"
        params = {
            "jql": jql,
            "maxResults": 50,
            "fields": "summary,customfield_10010,customfield_10020,customfield_10030"  # Example custom field IDs
        }
        
        response = self.session.get(search_url, params=params)
        
        if response.status_code != 200:
            return {}
        
        issues = response.json().get("issues", [])
        
        # Extract team information from custom fields
        team_members = []
        
        for issue in issues:
            fields = issue.get("fields", {})
            
            # Look for custom fields (you need to discover your Jira's field IDs)
            for field_key, field_value in fields.items():
                if field_key.startswith("customfield_") and field_value:
                    # Try to parse team information
                    if isinstance(field_value, list):
                        for item in field_value:
                            if isinstance(item, dict) and "value" in item:
                                team_info = self._parse_team_field(item["value"])
                                if team_info:
                                    team_members.append(team_info)
                    elif isinstance(field_value, dict):
                        team_info = self._parse_team_field(field_value.get("value", ""))
                        if team_info:
                            team_members.append(team_info)
        
        # If no custom fields found, get project members
        if not team_members:
            team_members = self._get_project_members(project_key)
        
        return {
            "team_members": team_members,
            "total_members": len(team_members)
        }
    
    def _parse_team_field(self, field_value: str) -> Dict:
        """Parse team member information from custom field"""
        # Common patterns in team fields:
        # "John Doe (UI Designer) - john@example.com"
        # "Jane Smith|Backend Developer|jane@company.com"
        
        if not field_value:
            return None
        
        # Try different parsing strategies
        patterns = [
            # Pattern: Name (Role) - email
            r'(.+?)\s*\((.+?)\)\s*-\s*([\w\.-]+@[\w\.-]+\.\w+)',
            # Pattern: Name|Role|Email
            r'(.+?)\|(.+?)\|([\w\.-]+@[\w\.-]+\.\w+)',
            # Pattern: Name - Role
            r'(.+?)\s*-\s*(.+)'
        ]
        
        import re
        
        for pattern in patterns:
            match = re.match(pattern, field_value)
            if match:
                groups = match.groups()
                if len(groups) >= 2:
                    return {
                        "name": groups[0].strip(),
                        "role": groups[1].strip() if len(groups) > 1 else "Team Member",
                        "email": groups[2].strip() if len(groups) > 2 else ""
                    }
        
        # Fallback: just name
        return {"name": field_value.strip(), "role": "Team Member", "email": ""}
    
    def _get_project_members(self, project_key: str) -> List[Dict]:
        """Get project members via project role API"""
        
        # Get project roles
        roles_url = f"{self.base_url}/rest/api/3/project/{project_key}/role"
        roles_response = self.session.get(roles_url)
        
        if roles_response.status_code != 200:
            return []
        
        roles = roles_response.json()
        members = []
        
        # Get users for each role (simplified - in reality you'd need to iterate)
        for role_name, role_url in roles.items():
            try:
                role_response = self.session.get(role_url)
                if role_response.status_code == 200:
                    role_data = role_response.json()
                    for actor in role_data.get("actors", []):
                        if actor.get("type") == "atlassian-user-role-actor":
                            member = {
                                "name": actor.get("displayName", ""),
                                "role": role_name.replace("atlassian-", "").title(),
                                "email": actor.get("emailAddress", "")
                            }
                            members.append(member)
            except:
                continue
        
        return members
    
    def fetch_project_issues(self, project_key: str, max_results: int = 100) -> List[Dict]:
        """Fetch all issues with complete details using Agile API"""
        
        issues = []
        
        try:
            # First, try to get boards (Jira Agile/Software uses boards instead of search)
            boards_url = f"{self.base_url}/rest/agile/latest/board"
            response = self.session.get(boards_url)
            
            if response.status_code == 200:
                print(f"[*] Using Agile Board API to fetch issues...")
                boards = response.json().get("values", [])
                
                # Get issues from each board
                for board in boards:
                    board_id = board.get("id")
                    board_name = board.get("name")
                    
                    # Get issues from this board
                    issues_url = f"{self.base_url}/rest/agile/latest/board/{board_id}/issue"
                    params = {
                        "maxResults": 100,
                        "jql": f"project = {project_key}"
                    }
                    
                    board_response = self.session.get(issues_url, params=params)
                    if board_response.status_code == 200:
                        board_issues = board_response.json().get("issues", [])
                        print(f"  [*] Board '{board_name}': {len(board_issues)} issues for {project_key}")
                        
                        for issue in board_issues:
                            try:
                                structured_issue = self._structure_issue(issue)
                                issues.append(structured_issue)
                                if len(issues) >= max_results:
                                    break
                            except Exception as e:
                                print(f"    [!] Error structuring issue {issue.get('key')}: {e}")
                                continue
                    
                    if len(issues) >= max_results:
                        break
                
                if issues:
                    print(f"[+] Successfully fetched {len(issues)} issues from {project_key} using Agile API")
                    return issues
            
        except Exception as e:
            print(f"[!] Agile API error: {e}")
        
        # Fallback to search API (may not work on all instances)
        print(f"[*] Trying standard Search API...")
        
        jql = f'project = {project_key} ORDER BY created DESC'
        
        start_at = 0
        
        while len(issues) < max_results:
            search_url = f"{self.base_url}/rest/api/3/search"
            params = {
                "jql": jql,
                "startAt": start_at,
                "maxResults": min(50, max_results - len(issues)),
                "fields": "summary,description,status,assignee,reporter,created,updated,resolutiondate,duedate,priority,labels,issuetype,components,comment,worklog,timeoriginalestimate,timespent,parent,subtasks,issuelinks",
            }
            
            response = self.session.get(search_url, params=params)
            
            if response.status_code != 200:
                print(f"[!] Error fetching issues (Status {response.status_code}): {response.text[:100]}")
                break
            
            data = response.json()
            batch_issues = data.get("issues", [])
            
            if not batch_issues:
                print(f"[*] No more issues found (fetched {len(issues)} total)")
                break
            
            print(f"[*] Fetched batch: {len(batch_issues)} issues (total so far: {len(issues) + len(batch_issues)})")
            
            # Structure each issue
            for issue in batch_issues:
                try:
                    structured_issue = self._structure_issue(issue)
                    issues.append(structured_issue)
                except Exception as e:
                    print(f"    [!] Error structuring issue {issue.get('key')}: {e}")
                    continue
            
            start_at += len(batch_issues)
            
            # Check if we've fetched all issues
            if len(batch_issues) < 50 or len(issues) >= max_results:
                break
        
        print(f"[+] Successfully fetched {len(issues)} issues from {project_key}")
        return issues
    
    def _structure_issue(self, issue: Dict) -> Dict:
        """Structure issue data for RAG"""
        
        fields = issue.get("fields", {})
        
        # Get comments (developer updates)
        comments = []
        comment_field = fields.get("comment", {})
        if comment_field and isinstance(comment_field, dict) and "comments" in comment_field:
            for comment in comment_field.get("comments", []):
                if comment:
                    comments.append({
                        "id": comment.get("id"),
                        "author": comment.get("author", {}).get("displayName", "Unknown") if comment.get("author") else "Unknown",
                        "body": comment.get("body", ""),
                        "created": comment.get("created", ""),
                        "updated": comment.get("updated", "")
                    })
        
        # Get worklogs (time tracking)
        worklogs = []
        worklog_field = fields.get("worklog", {})
        if worklog_field and isinstance(worklog_field, dict) and "worklogs" in worklog_field:
            for worklog in worklog_field.get("worklogs", []):
                if worklog:
                    worklogs.append({
                        "id": worklog.get("id"),
                        "author": worklog.get("author", {}).get("displayName", "Unknown") if worklog.get("author") else "Unknown",
                        "timeSpent": worklog.get("timeSpent", ""),
                        "started": worklog.get("started", ""),
                        "comment": worklog.get("comment", "")
                    })
        
        # Safely get status
        status_field = fields.get("status")
        status_data = {
            "name": status_field.get("name", "") if status_field and isinstance(status_field, dict) else "Unknown",
            "statusCategory": status_field.get("statusCategory", {}).get("name", "") if status_field and isinstance(status_field, dict) else ""
        }
        
        # Safely get issuetype
        issuetype_field = fields.get("issuetype")
        issuetype_data = {
            "name": issuetype_field.get("name", "") if issuetype_field and isinstance(issuetype_field, dict) else "Unknown",
            "description": issuetype_field.get("description", "") if issuetype_field and isinstance(issuetype_field, dict) else ""
        }
        
        # Structure the issue
        structured = {
            "id": issue.get("id"),
            "key": issue.get("key"),
            "self": issue.get("self"),
            
            # Core fields
            "summary": fields.get("summary", ""),
            "description": fields.get("description", ""),
            
            # Status & progress
            "status": status_data,
            "progress": fields.get("progress", {}).get("percent", 0) if fields.get("progress") else 0,
            
            # People
            "assignee": {
                "name": fields.get("assignee", {}).get("displayName", "") if fields.get("assignee") else "Unassigned",
                "email": fields.get("assignee", {}).get("emailAddress", "") if fields.get("assignee") else ""
            },
            "reporter": {
                "name": fields.get("reporter", {}).get("displayName", "") if fields.get("reporter") else "",
                "email": fields.get("reporter", {}).get("emailAddress", "") if fields.get("reporter") else ""
            },
            
            # Time tracking
            "created": fields.get("created", ""),
            "updated": fields.get("updated", ""),
            "resolutiondate": fields.get("resolutiondate", ""),
            "duedate": fields.get("duedate", ""),
            
            # Estimates & actuals
            "timeoriginalestimate": fields.get("timeoriginalestimate", 0),  # seconds
            "timespent": fields.get("timespent", 0),  # seconds
            
            # Categorization
            "issuetype": issuetype_data,
            "priority": {
                "name": fields.get("priority", {}).get("name", "") if fields.get("priority") else "Unset",
                "iconUrl": fields.get("priority", {}).get("iconUrl", "") if fields.get("priority") else ""
            },
            "labels": fields.get("labels", []) if fields.get("labels") else [],
            "components": [
                {
                    "id": comp.get("id"),
                    "name": comp.get("name")
                }
                for comp in (fields.get("components", []) if fields.get("components") else [])
            ],
            
            # Relationships
            "parent": {
                "key": fields.get("parent", {}).get("key") if fields.get("parent") else None
            },
            "subtasks": [
                {
                    "key": subtask.get("key"),
                    "summary": subtask.get("fields", {}).get("summary", "")
                }
                for subtask in (fields.get("subtasks", []) if fields.get("subtasks") else [])
            ],
            
            # Content
            "comments": comments,
            "worklogs": worklogs,
            "comment_count": len(comments),
            "worklog_hours": sum(
                self._parse_time_to_hours(w.get("timeSpent", "")) 
                for w in worklogs
            ),
            
            # For semantic search
            "semantic_tags": self._generate_semantic_tags(fields),
            "chunk_type": "issue"
        }
        
        return structured
    
    def _parse_time_to_hours(self, time_str: str) -> float:
        """Convert Jira time string to hours"""
        if not time_str:
            return 0
        
        # Format: "3h 30m", "2d", "1w", etc.
        import re
        
        hours = 0
        # Days
        day_match = re.search(r'(\d+)\s*d', time_str)
        if day_match:
            hours += int(day_match.group(1)) * 8  # 8-hour workday
        
        # Hours
        hour_match = re.search(r'(\d+)\s*h', time_str)
        if hour_match:
            hours += int(hour_match.group(1))
        
        # Minutes
        min_match = re.search(r'(\d+)\s*m', time_str)
        if min_match:
            hours += int(min_match.group(1)) / 60
        
        # Weeks
        week_match = re.search(r'(\d+)\s*w', time_str)
        if week_match:
            hours += int(week_match.group(1)) * 40  # 40-hour workweek
        
        return hours
    
    def _generate_semantic_tags(self, fields: Dict) -> List[str]:
        """Generate semantic tags for better retrieval"""
        tags = []
        
        # Issue type
        issuetype_field = fields.get("issuetype")
        if issuetype_field and isinstance(issuetype_field, dict):
            issue_type = issuetype_field.get("name", "").lower()
            tags.append(f"type:{issue_type}")
        
        # Priority
        priority_field = fields.get("priority")
        if priority_field and isinstance(priority_field, dict):
            priority = priority_field.get("name", "").lower()
            tags.append(f"priority:{priority}")
        
        # Status
        status_field = fields.get("status")
        if status_field and isinstance(status_field, dict):
            status = status_field.get("name", "").lower()
            tags.append(f"status:{status}")
        
        # Labels
        for label in (fields.get("labels", []) if fields.get("labels") else []):
            if label:
                tags.append(f"label:{str(label).lower()}")
        
        # Components
        for component in (fields.get("components", []) if fields.get("components") else []):
            if component and isinstance(component, dict):
                comp_name = component.get("name", "").lower()
                tags.append(f"component:{comp_name}")
        
        # Time-based tags
        created = fields.get("created", "")
        if created:
            # Extract year-month for temporal filtering
            try:
                year_month = created[:7]  # "2024-03"
                tags.append(f"created:{year_month}")
            except:
                pass
        
        return tags