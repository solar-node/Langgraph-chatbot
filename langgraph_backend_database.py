from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
import sqlite3

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model = 'gemini-2.0-flash-lite'
)

class ChatState(TypedDict):
    messages : Annotated[list[BaseMessage], add_messages]

def chat_node(state: ChatState):
    messages = state['messages']
    response = llm.invoke(messages)
    return {'messages' : [response]}

conn = sqlite3.connect(database='chatbot.db', check_same_thread=False)

# Checkpointer
checkpointer = SqliteSaver(conn = conn)

graph = StateGraph(ChatState)
graph.add_node('chat_node',chat_node)
graph.add_edge(START, 'chat_node')
graph.add_edge('chat_node', END)

chatbot = graph.compile(checkpointer=checkpointer)

# In langgraph_backend_database.py

def retrieve_all_threads():
    checkpoints = list(checkpointer.list(None))
    threads_map = {}

    # Iterate backwards (from newest checkpoint to oldest)
    # This ensures we get the most recent state for each thread first.
    for checkpoint in reversed(checkpoints):
        thread_id = checkpoint.config['configurable']['thread_id']
        
        # If we already found a title for this thread, skip it
        if thread_id in threads_map:
            continue
            
        # --- Start: Clearer Title Extraction ---

        # 1. Get the saved state dictionary from the checkpoint
        state = checkpoint.checkpoint
        if not isinstance(state, dict):
            state = {} # Ensure we have a dictionary to work with

        # 2. Safely get the 'channel_values' dictionary
        # This contains the actual data from your graph nodes
        channel_values = state.get("channel_values", {})

        # 3. Safely get the '__start__' node's data
        # This is where LangGraph stores the initial input
        start_node_data = channel_values.get("__start__", {})

        # 4. Safely get the list of messages from that node
        messages = start_node_data.get("messages", [])

        # --- End: Clearer Title Extraction ---

        # 5. Find the first human message to use as a title
        title = "New Chat" # Default title
        for msg in messages: 
            if isinstance(msg, HumanMessage):
                content = msg.content.strip()
                if content: # Make sure content is not empty
                    title = content[:30] + ("..." if len(content) > 30 else "")
                    break # We found our title, stop looping
        
        # 6. Store the thread info
        threads_map[thread_id] = {"id": thread_id, "title": title}

    # We iterated newest-to-oldest, so threads_map is in that order.
    # Convert to a list and reverse it to get oldest-to-newest,
    # which is the order your frontend expects.
    all_threads = list(threads_map.values())
    all_threads.reverse()

    return all_threads

# Test
# CONFIG = {'configurable' : {'thread_id' : 'thread-1'}}

# response = chatbot.invoke(
#     {'messages' : [HumanMessage(content='What is my name?')]},
#     config = CONFIG
# )
# print(response)

# for checkpoint in checkpointer.list(None):
#     print(checkpoint.config['configurable'])