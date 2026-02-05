import os
import base64
import requests
from dotenv import load_dotenv

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

# Try with explicit Content-Type
headers_no_ct = {
    'Authorization': f'Basic {encoded_auth}',
    'Accept': 'application/json',
}

# Try different variations
tests = [
    ('POST with JSON body', 'POST', f'{base_url}/rest/api/3/search', '{"jql":"project=PRJ"}'),
    ('POST without CT header', 'POST', f'{base_url}/rest/api/3/search', None),
    ('GET without fields param', 'GET', f'{base_url}/rest/api/3/search?jql=project%3DPRJ', None),
]

for name, method, url, body in tests:
    print(f'\n{name}')
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers_no_ct, timeout=5)
        else:
            if body:
                response = requests.post(url, headers=headers, data=body, timeout=5)
            else:
                response = requests.post(url, headers=headers_no_ct, timeout=5)
        
        print(f'Status: {response.status_code}')
        if response.status_code == 200:
            data = response.json()
            issues = data.get('issues', [])
            print(f'✅ SUCCESS! Found {len(issues)} issues')
        elif response.status_code in [400, 403, 404]:
            print(f'❌ {response.status_code}: {response.text[:200]}')
        else:
            print(f'Response: {response.text[:150]}')
    except Exception as e:
        print(f'Exception: {str(e)[:100]}')
