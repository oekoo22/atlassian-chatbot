import os
from dotenv import load_dotenv

load_dotenv()

# Bind credentials
atlassian_key = os.getenv("ATLASSIAN_API")
jira_user = os.getenv("JIRA_USER_EMAIL")
jira_url = os.getenv("JIRA_URL")
openai_key = os.getenv("OPENAI_API")