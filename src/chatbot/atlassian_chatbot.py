import openai
import json
from config.settings import openai_key
from apis.jira_api import JiraAPI
from apis.confluence_api import ConfluenceAPI

# Create class for chatbot
class AtlassianChatbot:
    def __init__(self):
        self.jira_api = JiraAPI()
        self.confluence_api = ConfluenceAPI()
        self.openai = openai_key
        openai.api_key = self.openai
        
        # Conversation Messages
        self.conversation_messages = [
            {
                # This is the instruction for the chatbot. Change this for more nuanced responses.
                "role": "system",
                "content": """You are a helpful assistant who searches and analyzes Jira tickets and Confluence pages.
                If the user asks for a specific ticket ID (e.g., SCRUM-3), use get_ticket_description.
                If the user searches for information about Confluence (e.g., "Find pages about XYZ"), use search_confluence_pages.
                If the user searches for ticket information (e.g., "Where is XYZ mentioned?"), use search_tickets_by_keyword.
                Summarize the found information and respond in a clear and understandable manner.
                Please, always use the tools first before providing general information. When you found any information leading to an answer to the prompt, always just use the tools. You can also ask the user, if you can provide any additional information.
                Use your general knowledge JUST and ONLY JUST if the tools do not provide any information.
                If you are asked for information which you would clarify as some kind of organization intern information, e.g. vacation policies, internal structures, who is responsible for specific things etc., please NEVER answer with your general knowledge instead just use the tools to answer."""
            }
        ]
        
        # Define the tools which the chatbot can later use. Tools are functions that can be called by the chatbot to perform specific tasks.
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

    # Import API functions from Jira and Confluence
    def search_tickets_by_keyword(self, keyword):
        return self.jira_api.search_tickets_by_keyword(keyword)

    def get_ticket_description(self, ticket_id):
        return self.jira_api.get_ticket_description(ticket_id)

    def search_confluence_pages(self, keyword):
        return self.confluence_api.search_confluence_pages(keyword)
    
    # Where the magic happens. The chatbot gets the user input and processes the conversation.
    def process_conversation(self, user_input):
        # Add User Input to the conversation
        self.conversation_messages.append({"role": "user", "content": user_input})
        
        try:
            # Call the OpenAI API to get the chatbot response
            response = openai.chat.completions.create(
                model="gpt-4o", # Change the model as needed. 
                messages=self.conversation_messages,
                tools=self.tools # Give the chatbot access to all defined tools
            )
            # Get the chatbot response
            assistant_message = response.choices[0].message
            
            # Check if the chatbot response is a tool call
            if response.choices[0].finish_reason == "tool_calls":
                # We have to extract the tool calls from the assistant message to actually get the answer for the user
                for tool_call in assistant_message.tool_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    
                    # Get results from each tool call and fill the chatbot message with the actual answer
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
            
            # Return the chatbot response
            return assistant_message.content
            
        except Exception as e:
            return f"Error: {str(e)}"