import os
import base64
import requests
from dotenv import load_dotenv
import json

load_dotenv()

domain = os.getenv('JIRA_DOMAIN', 'kabildaami123')
email = os.getenv('JIRA_EMAIL', 'kabildaami123@gmail.com')
api_token = os.getenv('JIRA_API_TOKEN')

base_url = f'https://{domain}.atlassian.net'

auth_string = f'{email}:{api_token}'
encoded_auth = base64.b64encode(auth_string.encode()).decode()
headers = {
    'Authorization': f'Basic {encoded_auth}',
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}

# Get the KAN board issues
board_id = 2
issues_url = f'{base_url}/rest/agile/latest/board/{board_id}/issue'
params = {
    'maxResults': 100,
    'jql': 'project = PRJ'
}

response = requests.get(issues_url, headers=headers, params=params)
if response.status_code == 200:
    data = response.json()
    issues = data.get('issues', [])
    print(f'Found {len(issues)} issues')
    
    for i, issue in enumerate(issues):
        print(f'\n--- Issue {i+1} ---')
        print(f'Key: {issue.get("key")}')
        print(f'Type: {type(issue)}')
        print(f'Has fields: {"fields" in issue}')
        print(f'Fields keys: {list(issue.get("fields", {}).keys())[:5]}...')
        
        # Check the structure
        fields = issue.get('fields', {})
        print(f'Status: {fields.get("status")}')
        print(f'Assignee: {fields.get("assignee")}')
        print(f'Priority: {fields.get("priority")}')
