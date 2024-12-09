import requests
from config.settings import jira_url, jira_user, atlassian_key

class ConfluenceAPI:
    def __init__(self):
        self.jira_url = jira_url
        self.jira_user = jira_user
        self.atlassian_key = atlassian_key

    # Search for Confluence pages containing specific keywords from the user prompt.
    def search_confluence_pages(self, keyword):
        headers = {
            "Accept": "application/json"
        }
        auth = (self.jira_user, self.atlassian_key)

        # Use Confluence search API
        url = f"{self.jira_url}/wiki/rest/api/search"
        params = {
            "cql": f"type=page and text ~ \"{keyword}\"",
            "limit": 5  # Limit to top 5 results. Raise if needed.
        }
        
        response = requests.get(url, headers=headers, auth=auth, params=params)

        # Make sure the response is successful
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
        
    
    def get_confluence_page_url(self, page_id):
        """Generate the full URL for a Confluence page."""
        return f"{self.jira_url}/wiki/pages/viewpage.action?pageId={page_id}"