import streamlit as st
from langchain_core.messages import HumanMessage
# Importing chatbot object from langgraph_backend.py
from langgraph_backend import chatbot

# Due to checkpointer, invoke krte time thread_id bhi bhejna pdega 
CONFIG = {'configurable' : {'thread_id' : 'thread-1'}}

user_input = st.chat_input('Type here')

# st.session_state -> dict -> 

if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []


# Loading the conversation history
for message in st.session_state['message_history'] :
    with st.chat_message(message['role']):
        st.text(message['content'])

# {'role' : 'user', 'content' : 'Hii'}
# {'role' : 'assistant', 'content' : 'Hello'}

if user_input:

    # First add the message to message_history
    st.session_state['message_history'].append({'role': 'user', 'content' : user_input})
    with st.chat_message('user'):
        st.text(user_input)


    response = chatbot.invoke({'messages' : [HumanMessage(content = user_input)]}, config = CONFIG)
    ai_message = response['messages'][-1].content
    # First add the message to message_history
    st.session_state['message_history'].append({'role': 'assistant', 'content' : ai_message})
    with st.chat_message('assistant'):
        st.text(ai_message)
    


    