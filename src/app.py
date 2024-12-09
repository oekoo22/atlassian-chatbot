import streamlit as st
from chatbot.atlassian_chatbot import AtlassianChatbot

def init_session_state():
    """Initialize session state variables."""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'chatbot' not in st.session_state:
        st.session_state.chatbot = AtlassianChatbot()

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