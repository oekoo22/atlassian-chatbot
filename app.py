# pip3 install requests python-dotenv

from dotenv import load_dotenv
import os
import requests

load_dotenv()

# Atlassian Key
atlassian_key = os.getenv("ATLASSIAN_API")
jira_user = os.getenv("JIRA_USER_EMAIL")
jira_url = os.getenv("JIRA_URL")

# Check if env file loaded correctly
print("API Key loaded:", atlassian_key is not None)
print("Jira User loaded:", jira_user is not None)
print("Jira Domain loaded:", jira_url is not None)

# Ticket ID
ticket_id = "SCRUM-2"

# URL for API-Request
url = f"{jira_url}/rest/api/3/issue/{ticket_id}"

# Header for API-Request
headers = {
    "Accept": "application/json"
}

auth = (jira_user, atlassian_key)

# API-Request
response = requests.get(url, headers=headers, auth=auth)

# Check if request was successful
if response.status_code == 200:
    print("Request was successful")
    print(response.json())
else:
    print("Request failed")
    print(response.text)