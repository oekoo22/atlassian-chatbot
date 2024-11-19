# pip3 install requests python-dotenv
from dotenv import load_dotenv
import os
import requests
import openai
import json

load_dotenv()

# Atlassian Key
atlassian_key = os.getenv("ATLASSIAN_API")
jira_user = os.getenv("JIRA_USER_EMAIL")
jira_url = os.getenv("JIRA_URL")

# OpenAI Key
openai_key = os.getenv("OPENAI_API")

# Set OpenAI API Key
openai.api_key = openai_key
    
# Test Ticket ID
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

# Function to get ticket description
def get_ticket_description(ticket_id):
    # URL for API-Request
    url = f"{jira_url}/rest/api/3/issue/{ticket_id}"
    
    # API-Request
    response = requests.get(url, headers=headers, auth=auth)
    
    # Check if request was successful
    if response.status_code == 200:
        ticket_data = response.json()
        description = ticket_data['fields'].get('description', None)
            
        if description:
            # Extract text from structured output
            text_content = ""
            for paragraph in description.get('content', []):
                for element in paragraph.get('content', []):
                    if element['type'] == 'text':
                        text_content += element['text'] + " "
            return text_content.strip()
        else:
            return "Keine Beschreibung verfügbar"
    else:
        return f"Fehler: {response.status_code} {response.text}"

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_ticket_description",
            "description": "Use this function whenever the prompt asks you to give the user acces to a ticket with a ticket id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticket_id": {
                        "type": "string",
                        "description": "The user's ticket ID.",
                    },
                },
                "required": ["ticket_id"],
                "additionalProperties": False
            }
        }
    }
]

# OpenAI Test Request
response = openai.chat.completions.create(
    model="gpt-4o",
    messages=[
        {
            "role": "system", 
            "content": "You are a helpful assistant. Use the supplied tools to assist the user."},
        {
            "role": "user",
            "content": "Please provide me the description of the ticket with the id SCRUM-2."
        }
    ],
    tools=tools,
)

#print(response.choices[0])

tool_call = response.choices[0].message.tool_calls[0]
arguments = json.loads(tool_call.function.arguments)

ticket_id = arguments['ticket_id']
#print(get_ticket_description(ticket_id))

# Function Call Result Message
response = {
    "choices": [
        {
            "message": {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "call_fOjuDCYeZVdO8vXGYAH69Sxi",
                        "type": "function",
                        "function": {
                            "arguments": "{'ticket_id': 'SCRUM-2'}",
                            "name": "get_ticket_description"
                        }
                    }
                ]
            }
        }
    ]
}

function_call_result_message = {
    "role": "tool",
    "content": json.dumps({
        "ticket_id": ticket_id,
        "ticket_description": get_ticket_description(ticket_id)
    }),
    "tool_call_id": response['choices'][0]['message']['tool_calls'][0]['id']
}

completion_payload = {
    "model": "gpt-4o",
    "messages": [
        {"role": "system", "content": "You are a helpful assistant. Use the supplied tools to assist the user."},
        {"role": "user", "content": "Hi, can you tell me the ticket description for the ticket SCRUM-2?"},
        response['choices'][0]['message'],
        function_call_result_message
    ]
}

response = openai.chat.completions.create(
    model=completion_payload["model"],
    messages=completion_payload["messages"]
)

print(response)