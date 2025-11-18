from agents.atlassian_agent import AtlassianAgent


class AtlassianChatbot:
    def __init__(self):
        self.agent = AtlassianAgent()

    def search_tickets_by_keyword(self, keyword):
        return self.agent.search_tickets_by_keyword(keyword)

    def get_ticket_description(self, ticket_id):
        return self.agent.get_ticket_description(ticket_id)

    def search_confluence_pages(self, keyword):
        return self.agent.search_confluence_pages(keyword)

    def process_conversation(self, user_input):
        try:
            return self.agent.respond(user_input)
        except Exception as e:
            return f"Error: {str(e)}"
