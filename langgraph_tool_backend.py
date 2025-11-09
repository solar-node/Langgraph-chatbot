from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
import sqlite3

from langchain_community.tools import DuckDuckGoSearchRun
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.tools import tool
import requests

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model = 'gemini-2.5-flash'
)

#### Tools
# 1. Search tool
search_tool =DuckDuckGoSearchRun(region="us-en")

# 2. Calculator
@tool
def calculator(first_num: float, second_num: float, operation: str) -> dict:
    """
    Perform a basic arithmetic operation on two numbers.
    Supported operations: add, sub, mul, div
    """
    try:
        if operation == "add":
            result = first_num + second_num
        elif operation == "sub":
            result = first_num - second_num
        elif operation == "mul":
            result = first_num * second_num
        elif operation == "div":
            if second_num == 0:
                return {"error": "Division by zero is not allowed"}
            result = first_num / second_num
        else:
            return {"error": f"Unsupported operation '{operation}'"}
        
        return {"first_num": first_num, "second_num": second_num, "operation": operation, "result": result}
    except Exception as e:
        return {"error": str(e)}



# 3. Stock price
@tool
def get_stock_price(symbol: str) -> dict:
    """
    Fetch latest stock price for a given symbol (e.g. 'AAPL', 'TSLA') 
    using Alpha Vantage with API key in the URL.
    """
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey=C9PE94QUEW9VWGFM"
    r = requests.get(url)
    return r.json()

tools = [search_tool, get_stock_price, calculator]
llm_with_tools = llm.bind_tools(tools)


class ChatState(TypedDict):
    messages : Annotated[list[BaseMessage], add_messages]

def chat_node(state: ChatState):
    messages = state['messages']
    response = llm_with_tools.invoke(messages)
    return {'messages' : [response]}

tool_node = ToolNode(tools)

conn = sqlite3.connect(database='chatbot.db', check_same_thread=False)

# Checkpointer
checkpointer = SqliteSaver(conn = conn)

# Graph
graph = StateGraph(ChatState)
graph.add_node('chat_node',chat_node)
graph.add_node("tools", tool_node)

graph.add_edge(START, "chat_node")

graph.add_conditional_edges("chat_node", tools_condition)
graph.add_edge('tools', 'chat_node')

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