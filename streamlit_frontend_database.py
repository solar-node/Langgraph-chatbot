import streamlit as st
from langchain_core.messages import HumanMessage
# Importing chatbot object from langgraph_backend.py
from langgraph_backend_database import chatbot, retrieve_all_threads

# Can generate new thread id each time it is called
import uuid


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

if st.sidebar.button('Start Conversation'):
    reset_chat()

st.sidebar.header('Recent')

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
            

# ***************** MAIN UI ***********************************

# Loading the conversation history
for message in st.session_state['message_history'] :
    with st.chat_message(message['role']):
        st.text(message['content'])

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
        ai_message = st.write_stream(
            message_chunk.content for message_chunk, metadata in chatbot.stream(
                {'messages' : [HumanMessage(content=user_input)]},
                config = CONFIG,
                stream_mode= 'messages'
                )
            )
        

    # Store in session
    st.session_state['message_history'].append({'role': 'assistant', 'content' : ai_message})