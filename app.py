import streamlit as st
from dotenv import load_dotenv
import os
import requests
import openai
import json
from datetime import datetime

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
                Fasse die gefundenen Informationen zusammen und antworte in verständlicher Form.
                Füge für jedes erwähnte Ticket einen Link zum Ticket hinzu."""
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

    def get_ticket_url(self, ticket_id):
        """Generate the full URL for a Jira ticket."""
        return f"{self.jira_url}/browse/{ticket_id}"

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
            ticket_url = self.get_ticket_url(ticket_id)
                
            if description:
                text_content = ""
                for paragraph in description.get('content', []):
                    for element in paragraph.get('content', []):
                        if element['type'] == 'text':
                            text_content += element['text'] + " "
                return f"{text_content.strip()}\n\nTicket URL: {ticket_url}"
            else:
                return f"Keine Beschreibung verfügbar\n\nTicket URL: {ticket_url}"
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
                        "description": self.get_ticket_description(issue['key']),
                        "url": self.get_ticket_url(issue['key'])
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
                model="gpt-4o",
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

def init_session_state():
    """Initialize session state variables."""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'chatbot' not in st.session_state:
        st.session_state.chatbot = JiraChatbot()
    if 'user_input' not in st.session_state:
        st.session_state.user_input = ""

def display_message(role, content):
    """Display a chat message with appropriate styling."""
    if role == "user":
        st.write(f'👤 **Sie** ({datetime.now().strftime("%H:%M")})')
        st.write(content)
    else:
        st.write(f'🤖 **JIRA Assistant** ({datetime.now().strftime("%H:%M")})')
        st.write(content)
    st.write("---")

def main():
    st.set_page_config(
        page_title="JIRA Chat Assistant",
        page_icon="🤖",
        layout="wide"
    )

    st.title("🤖 JIRA Chat Assistant")
    st.write("Stellen Sie Fragen zu Ihren JIRA-Tickets oder suchen Sie nach bestimmten Informationen.")

    # Initialize session state
    init_session_state()

    # Chat container
    chat_container = st.container()

    # Input container at the bottom
    with st.container():
        user_input = st.text_input(
            "Ihre Nachricht:",
            key="user_input_field",
            placeholder="Fragen Sie z.B. nach einem bestimmten Ticket oder suchen Sie nach Stichworten...",
            value=st.session_state.user_input
        )
        
        col1, col2 = st.columns([6, 1])
        with col2:
            clear_button = st.button("Chat löschen")

    if clear_button:
        st.session_state.messages = []
        st.session_state.chatbot = JiraChatbot()
        st.session_state.user_input = ""
        st.rerun()

    if user_input and user_input != st.session_state.user_input:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Get chatbot response
        response = st.session_state.chatbot.process_conversation(user_input)
        
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        # Update user_input in session state
        st.session_state.user_input = user_input
        
        # Rerun to update the display
        st.rerun()

    # Display chat history
    with chat_container:
        for message in st.session_state.messages:
            display_message(message["role"], message["content"])

if __name__ == "__main__":
    main()