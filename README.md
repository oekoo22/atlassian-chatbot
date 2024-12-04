# JIRA & Confluence Chat Assistant
This is a Streamlit-based chatbot application that integrates with JIRA and Confluence to help users efficiently query and analyze tickets and pages. Powered by OpenAI's GPT API, the bot can retrieve, summarize, and interact with organizational data stored in JIRA and Confluence.

## Features
**JIRA Integration:**
* Fetch ticket descriptions using ticket IDs.
* Search for tickets by keywords.
**Confluence Integration:**
* Search for Confluence pages by keywords.
**Conversational AI:**
* Summarizes search results and assists with insights using OpenAI GPT.
**Interactive UI:**
* Streamlit provides a user-friendly interface for seamless communication.

## Prerequisites
Before running the application, ensure you have the following:

**1. API Keys:**

* ATLASSIAN_API: API token for Atlassian access.
* JIRA_USER_EMAIL: Email associated with your JIRA account.
* JIRA_URL: Base URL for your JIRA instance.
* OPENAI_API: API key for OpenAI's GPT API.

**2.Environment Setup:**

* Python 3.8 or higher.
* Required libraries installed (see below).
* Environment Variables: Store your credentials securely in a .env file:

```plaintext
ATLASSIAN_API=<your-atlassian-api-key>
JIRA_USER_EMAIL=<your-jira-user-email>
JIRA_URL=<your-jira-url>
OPENAI_API=<your-openai-api-key>
```
## Installation
1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-folder>
```

2. Create and activate a virtual environment:
```bash
python -m venv env
source env/bin/activate # On Windows: env\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Add your .env file in the project root directory.

## Running the Application
1. Start the Streamlit app:

```bash
Copy code
streamlit run app.py
```

2. Open your browser to the URL displayed (e.g., http://localhost:8501).

3. Interact with the chatbot to ask questions about JIRA tickets or search for Confluence pages.

## Code Overview
* `JiraChatbot` Class:
    * Manages API interactions with JIRA and Confluence.
    * Integrates with OpenAI GPT for advanced conversational capabilities.
* Streamlit Integration:
    * Interactive chat UI using st.chat_input and st.chat_message.
* Tools:
    * Implements get_ticket_description, search_tickets_by_keyword, and search_confluence_pages as core functionalities.