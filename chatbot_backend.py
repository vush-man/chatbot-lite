from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage
from langchain_ollama import ChatOllama
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages
import sqlite3

llm = ChatOllama(
    model= 'llama3.2:3b'
)

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def chat_node(state: ChatState):
    messages = state['messages']
    response = llm.invoke(messages)

    return {'messages': [response]}

conn = sqlite3.connect(database='chatbot.db', check_same_thread=False)

checkpointer = SqliteSaver(conn=conn)

graph = StateGraph(ChatState)

graph.add_node('chat_node', chat_node)

graph.add_edge(START, 'chat_node')
graph.add_edge('chat_node', END)

chatbot = graph.compile(checkpointer=checkpointer)

def init_metadata_table():
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_metadata (
            thread_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

init_metadata_table()

def set_conversation_name(thread_id, name):
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO conversation_metadata (thread_id, name)
        VALUES (?, ?)
    ''', (str(thread_id), name))
    conn.commit()

def get_conversation_name(thread_id):
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM conversation_metadata WHERE thread_id = ?', (str(thread_id),))
    result = cursor.fetchone()
    return result[0] if result else str(thread_id)

def retrieve_all_threads():
    all_threads = {}
    for checkpoint in checkpointer.list(None):
        thread_id = checkpoint.config['configurable']['thread_id']
        name = get_conversation_name(thread_id)
        all_threads[str(thread_id)] = name

    return all_threads