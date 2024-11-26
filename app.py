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
        # Configurations
        self.atlassian_key = os.getenv("ATLASSIAN_API")
        self.jira_user = os.getenv("JIRA_USER_EMAIL")
        self.jira_url = os.getenv("JIRA_URL")
        self.openai_key = os.getenv("OPENAI_API")
        openai.api_key = self.openai_key
        
        # Conversation Messages
        self.conversation_messages = [
            {
                "role": "system",
                "content": """You are a helpful assistant who searches and analyzes Jira tickets and Confluence pages.
                If the user asks for a specific ticket ID (e.g., SCRUM-3), use get_ticket_description.
                If the user searches for information about Confluence (e.g., "Find pages about XYZ"), use search_confluence_pages.
                If the user searches for ticket information (e.g., "Where is XYZ mentioned?"), use search_tickets_by_keyword.
                Summarize the found information and respond in a clear and understandable manner."""
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
            },
            {
                "type": "function",
                "function": {
                    "name": "search_confluence_pages",
                    "description": "Search for Confluence pages containing specific keywords",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "keyword": {
                                "type": "string",
                                "description": "The keyword to search for in Confluence pages",
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

    def get_confluence_page_url(self, page_id):
        """Generate the full URL for a Confluence page."""
        return f"{self.jira_url}/wiki/pages/viewpage.action?pageId={page_id}"

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
                return f"No Description available\n\nTicket URL: {ticket_url}"
        else:
            return f"Error: {response.status_code} {response.text}"

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

    def search_confluence_pages(self, keyword):
        headers = {
            "Accept": "application/json"
        }
        auth = (self.jira_user, self.atlassian_key)

        # Use Confluence search API
        url = f"{self.jira_url}/wiki/rest/api/search"
        params = {
            "cql": f"type=page and text ~ \"{keyword}\"",
            "limit": 5  # Limit to top 5 results
        }
        
        response = requests.get(url, headers=headers, auth=auth, params=params)

        if response.status_code == 200:
            search_results = response.json()
            results = search_results.get('results', [])
            if results:
                return [
                    {
                        "page_id": result['content']['id'],
                        "title": result['title'],
                        "excerpt": result.get('excerpt', 'No excerpt available'),
                        "url": self.get_confluence_page_url(result['content']['id'])
                    }
                    for result in results
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
                        
                    elif function_name == "search_confluence_pages":
                        results = self.search_confluence_pages(arguments["keyword"])
                        
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
            
            # Add the response to the conversation history
            self.conversation_messages.append({
                "role": "assistant",
                "content": assistant_message.content
            })
            
            return assistant_message.content
            
        except Exception as e:
            return f"Error: {str(e)}"

def init_session_state():
    """Initialize session state variables."""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'chatbot' not in st.session_state:
        st.session_state.chatbot = JiraChatbot()

def display_message(role, content):
    """Display a chat message with bubble-like styling."""
    if role == "user":
        st.chat_message("user").write(content)
    else:
        st.chat_message("assistant").write(content)

def main():
    st.set_page_config(
        page_title="JIRA & Confluence Chat Assistant",
        page_icon="🤖",
        layout="wide"
    )

    st.title("🤖 JIRA & Confluence Chat Assistant")
    st.write("Ask questions about your JIRA tickets or search for Confluence pages.")

    # Initialize session state
    init_session_state()

    # Display chat history
    for message in st.session_state.messages:
        display_message(message["role"], message["content"])

    # Chat input
    if prompt := st.chat_input("Ask questions about your JIRA tickets or search for Confluence pages...."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Get chatbot response
        response = st.session_state.chatbot.process_conversation(prompt)
        
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        # Rerun to update the display
        st.rerun()

if __name__ == "__main__":
    main()