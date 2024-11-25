# pip3 install requests python-dotenv
from dotenv import load_dotenv
import os
import requests
import openai
import json

load_dotenv()

class JiraChatbot:
    def __init__(self):
        # Konfiguration
        self.atlassian_key = os.getenv("ATLASSIAN_API")
        self.jira_user = os.getenv("JIRA_USER_EMAIL")
        self.jira_url = os.getenv("JIRA_URL")
        self.openai_key = os.getenv("OPENAI_API")
        openai.api_key = self.openai_key
        
        # Konversationsgedächtnis
        self.conversation_messages = [
            {
                "role": "system",
                "content": """Du bist ein hilfreicher Assistent, der Jira Tickets durchsucht und analysiert. 
                Wenn der Benutzer nach einem spezifischen Ticket-ID fragt (z.B. SCRUM-3), nutze get_ticket_description.
                Wenn der Benutzer nach Informationen sucht (z.B. 'Wo wird XYZ erwähnt?'), nutze search_tickets_by_keyword.
                Fasse die gefundenen Informationen zusammen und antworte in verständlicher Form."""
            }
        ]
        
        # Tools Definition
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_ticket_description",
                    "description": "Get the description of a specific Jira ticket using its ID",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticket_id": {
                                "type": "string",
                                "description": "The Jira ticket ID (e.g., SCRUM-3)",
                            }
                        },
                        "required": ["ticket_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_tickets_by_keyword",
                    "description": "Search for Jira tickets containing specific keywords",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "keyword": {
                                "type": "string",
                                "description": "The keyword to search for in tickets",
                            }
                        },
                        "required": ["keyword"]
                    }
                }
            }
        ]

    def get_ticket_description(self, ticket_id):
        headers = {
            "Accept": "application/json"
        }

        auth = (self.jira_user, self.atlassian_key)
        url = f"{self.jira_url}/rest/api/3/issue/{ticket_id}"
        
        response = requests.get(url, headers=headers, auth=auth)
        
        if response.status_code == 200:
            ticket_data = response.json()
            description = ticket_data['fields'].get('description', None)
                
            if description:
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

    def search_tickets_by_keyword(self, keyword):
        headers = {
            "Accept": "application/json"
        }
        auth = (self.jira_user, self.atlassian_key)

        jql = f'text ~ "{keyword}" ORDER BY created DESC'
        url = f"{self.jira_url}/rest/api/3/search?jql={jql}"
        
        response = requests.get(url, headers=headers, auth=auth)

        if response.status_code == 200:
            search_results = response.json()
            issues = search_results.get('issues', [])
            if issues:
                return [
                    {
                        "ticket_id": issue['key'],
                        "summary": issue['fields'].get('summary', 'No Title available'),
                        "description": self.get_ticket_description(issue['key'])
                    }
                    for issue in issues[:5]  # Limit to top 5 results for better handling
                ]
            else:
                return []
        else:
            raise Exception(f"Error: {response.status_code} {response.text}")

    def process_conversation(self, user_input):
        # Add User Input to the conversation
        self.conversation_messages.append({"role": "user", "content": user_input})
        
        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=self.conversation_messages,
                tools=self.tools
            )
            
            assistant_message = response.choices[0].message
            
            if response.choices[0].finish_reason == "tool_calls":
                for tool_call in assistant_message.tool_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    
                    if function_name == "search_tickets_by_keyword":
                        results = self.search_tickets_by_keyword(arguments["keyword"])
                        
                        # Add the function results to the messages
                        self.conversation_messages.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [tool_call]
                        })
                        self.conversation_messages.append({
                            "role": "tool",
                            "content": json.dumps(results),
                            "tool_call_id": tool_call.id
                        })
                        
                    elif function_name == "get_ticket_description":
                        description = self.get_ticket_description(arguments["ticket_id"])
                        
                        self.conversation_messages.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [tool_call]
                        })
                        self.conversation_messages.append({
                            "role": "tool",
                            "content": description,
                            "tool_call_id": tool_call.id
                        })
                
                # Get the final response after function calls
                return self.process_conversation(user_input)
            
            # Füge die Antwort zum Konversationsverlauf hinzu
            self.conversation_messages.append({
                "role": "assistant",
                "content": assistant_message.content
            })
            
            return assistant_message.content
            
        except Exception as e:
            return f"Ein Fehler ist aufgetreten: {str(e)}"

def main():
    print("Jira Chatbot gestartet. Geben Sie 'exit' ein, um das Programm zu beenden.")
    chatbot = JiraChatbot()
    
    while True:
        user_input = input("\nIhre Anfrage: ")
        
        if user_input.lower() == 'exit':
            print("Auf Wiedersehen!")
            break
            
        response = chatbot.process_conversation(user_input)
        print("\nAssistent:", response)

if __name__ == "__main__":
    main()