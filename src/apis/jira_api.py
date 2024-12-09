import requests
from config.settings import jira_url, jira_user, atlassian_key

class JiraAPI:
    def __init__(self):
        self.jira_url = jira_url
        self.jira_user = jira_user
        self.atlassian_key = atlassian_key

    # When a user wants the description of a specific ticket, the chatbot uses the get_ticket_description tool.
    def get_ticket_description(self, ticket_id):
        headers = {
            "Accept": "application/json"
        }

        auth = (self.jira_user, self.atlassian_key)
        url = f"{self.jira_url}/rest/api/3/issue/{ticket_id}" # Use the Ticket ID extracted from the user prompt
        
        response = requests.get(url, headers=headers, auth=auth)
        
        # Make sure the response is successful
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

    # Use the search API endpoint to search for a ticket from the keyword a user prompts.
    def search_tickets_by_keyword(self, keyword):
        headers = {
            "Accept": "application/json"
        }
        auth = (self.jira_user, self.atlassian_key)

        jql = f'text ~ "{keyword}" ORDER BY created DESC'
        url = f"{self.jira_url}/rest/api/3/search?jql={jql}"
        
        response = requests.get(url, headers=headers, auth=auth)

        # Make sure the response is successful
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
                    for issue in issues[:5]  # Limit to top 5 results for better handling. Raise if needed.
                ]
            else:
                return []
        else:
            raise Exception(f"Error: {response.status_code} {response.text}")
        
    def get_ticket_url(self, ticket_id):
        """Generate the full URL for a Jira ticket."""
        return f"{self.jira_url}/browse/{ticket_id}"