import streamlit as st
from langchain_core.messages import HumanMessage
# Importing chatbot object from langgraph_backend.py
from langgraph_backend_database import chatbot, retrieve_all_threads
import sqlite3
# Can generate new thread id each time it is called
import uuid


st.set_page_config(
    page_title="Langgraph Chatbot",
    page_icon="🤖",  
    layout="wide"    
)

# ********************* Utility functions ************************

def generate_thread_id():

    thread_id = uuid.uuid4()
    return thread_id

def reset_chat():
    thread_id = generate_thread_id()
    st.session_state['thread_id'] = thread_id
    add_thread(st.session_state['thread_id'], title="New Chat")
    st.session_state['message_history'] = []
 
def add_thread(thread_id, title="New Chat"):
    if 'chat_threads' not in st.session_state:
        st.session_state['chat_threads'] = []
    if not any(t['id'] == thread_id for t in st.session_state['chat_threads']):
        st.session_state['chat_threads'].append({'id': thread_id, 'title': title})

# Takes thread_id and returns the list of the messages 
def load_conversation(thread_id):
    state = chatbot.get_state(config={'configurable': {'thread_id': thread_id}}).values
    return state['messages'] if 'messages' in state else []


import os

def clear_database():
    db_path = "chatbot.db"
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Check if tables exist before deleting
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [t[0] for t in cursor.fetchall()]

            if "checkpoints" in tables:
                cursor.execute("DELETE FROM checkpoints;")
            if "checkpoint_blobs" in tables:
                cursor.execute("DELETE FROM checkpoint_blobs;")

            conn.commit()
            conn.close()

            # Reset session state
            st.session_state['chat_threads'] = []
            st.session_state['message_history'] = []
            st.session_state['thread_id'] = generate_thread_id()

            st.success("✅ Database cleared successfully! All chats removed.")
        except Exception as e:
            st.error(f"⚠️ Error clearing database: {e}")
    else:
        st.warning("No database file found to clear.")


# ******************* Session Setup ********************************

if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

if 'thread_id' not in st.session_state: # Iska matlab hmara thread_id set nhi hua h
    st.session_state['thread_id'] = generate_thread_id()


# Create a list and store all thread id's -> To in the sidebar
if 'chat_threads' not in st.session_state:
    st.session_state['chat_threads'] = retrieve_all_threads()

add_thread(st.session_state['thread_id'], title="New Chat")
# ****************** SIDEBAR UI *****************************

st.sidebar.title('Langgraph Chatbot')

# Use an icon and set use_container_width=True
if st.sidebar.button('➕ New Chat', use_container_width=True):
    reset_chat()

st.sidebar.header("Recent", divider="rainbow")

for chat in st.session_state['chat_threads'][::-1]:
    if st.sidebar.button(chat['title'], key=chat['id']):
        st.session_state['thread_id'] = chat['id']
        messages = load_conversation(chat['id'])
     
        temp_messages = []

        for msg in messages:
            if isinstance(msg, HumanMessage):  # If current message ka instance is HumanMessage
                role = 'user'
            else:
                role = 'assistant'
            temp_messages.append({'role' : role, 'content' : msg.content})

        st.session_state['message_history'] = temp_messages

# Sidebar footer for Clear Database
st.sidebar.markdown("---")
st.sidebar.caption("Maintenance")
if st.sidebar.button("🗑️ Clear Database", use_container_width=True):
    clear_database()


# ***************** MAIN UI ***********************************

# Add a title and welcome message if the chat is empty
if not st.session_state['message_history']:
    st.title("🤖 Langgraph Chatbot")
    st.info("Type a message in the box below to start our conversation!")

# Loading the conversation history
for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.markdown(message['content'])
# {'role' : 'user', 'content' : 'Hii'}
# {'role' : 'assistant', 'content' : 'Hello'}

user_input = st.chat_input('Type here')

if user_input:

    # Update chat title with first user message
    for t in st.session_state['chat_threads']:
        if t['id'] == st.session_state['thread_id'] and t['title'] == "New Chat":
            preview = user_input[:30] + ("..." if len(user_input) > 30 else "")
            t['title'] = preview

    # First add the message to message_history
    st.session_state['message_history'].append({'role': 'user', 'content' : user_input})
    with st.chat_message('user'):
        st.text(user_input)

    CONFIG = {'configurable' : {'thread_id' : st.session_state['thread_id']}}

    # response = chatbot.invoke({'messages' : [HumanMessage(content = user_input)]}, config = CONFIG)
    # ai_message = response['messages'][-1].content
    # First add the message to message_history
    # st.session_state['message_history'].append({'role': 'assistant', 'content' : ai_message})

    # Now we will do stream messages not invoke
    with st.chat_message('assistant'):
        response_container = st.empty()
        full_response = ""

        for message_chunk, metadata in chatbot.stream(
            {'messages': [HumanMessage(content=user_input)]},
            config=CONFIG,
            stream_mode='messages'
        ):
            full_response += message_chunk.content
            response_container.markdown(full_response)

        ai_message = full_response

    # Store in session
    st.session_state['message_history'].append({'role': 'assistant', 'content' : ai_message})