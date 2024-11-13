from dotenv import load_dotenv
import os

load_dotenv()

# Atlassian Key
atlassian_key = os.getenv("ATLASSIAN_API")
jira_user = os.getenv("JIRA_USER_EMAIL")
jira_url = os.getenv("JIRA_URL")

# Check if env file loaded correctly
print("API Key loaded:", atlassian_key is not None)
print("Jira User loaded:", jira_user is not None)
print("Jira Domain loaded:", jira_url is not None)