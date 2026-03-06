from __future__ import annotations
import os
import asyncio
import threading
import aiosqlite
import tempfile
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from typing import Annotated, Any, Dict, Optional, TypedDict
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.vectorstores import FAISS
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langgraph.graph import START, StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_mcp_adapters.client import MultiServerMCPClient


load_dotenv()

_ASYNC_LOOP = asyncio.new_event_loop()
_ASYNC_THREAD = threading.Thread(target=_ASYNC_LOOP.run_forever, daemon=True)
_ASYNC_THREAD.start()

def _submit_async(coro):
    return asyncio.run_coroutine_threadsafe(coro, _ASYNC_LOOP)


def run_async(coro):
    return _submit_async(coro).result()


def submit_async_task(coro):
    """Schedule a coroutine on the backend event loop."""
    return _submit_async(coro)

llm = ChatOllama(
    model = 'qwen2.5:3b'
)
embeddings = OllamaEmbeddings(
    model='qwen3-embedding:4b'
)

_THREAD_RETRIEVERS: Dict[str, Any] = {}
_THREAD_METADATA: Dict[str, dict] = {}

def _get_retriever(thread_id: Optional[str]):
    """Fetch the retriever for a thread if available."""
    if thread_id and thread_id in _THREAD_RETRIEVERS:
        return _THREAD_RETRIEVERS[thread_id]
    return None


def ingest_pdf(file_bytes: bytes, thread_id: str, filename: Optional[str] = None) -> dict:
    """
    Build a FAISS retriever for the uploaded PDF and store it for the thread.
    Returns a summary dict that can be surfaced in the UI.
    """
    if not file_bytes:
        raise ValueError("No bytes received for ingestion.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(file_bytes)
        temp_path = temp_file.name

    try:
        loader = PyPDFLoader(temp_path)
        docs = loader.load()

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200, separators=["\n\n", "\n", " ", ""]
        )
        chunks = splitter.split_documents(docs)

        vector_store = FAISS.from_documents(chunks, embeddings)
        retriever = vector_store.as_retriever(
            search_type="similarity", search_kwargs={"k": 4}
        )

        _THREAD_RETRIEVERS[str(thread_id)] = retriever
        _THREAD_METADATA[str(thread_id)] = {
            "filename": filename or os.path.basename(temp_path),
            "documents": len(docs),
            "chunks": len(chunks),
        }

        return {
            "filename": filename or os.path.basename(temp_path),
            "documents": len(docs),
            "chunks": len(chunks),
        }
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass

search_tool = DuckDuckGoSearchRun()

@tool
def rag_tool(query: str, thread_id: Optional[str] = None) -> dict:
    """
    Retrieve relevant information from the uploaded PDF for this chat thread.
    Always include the thread_id when calling this tool.
    """
    retriever = _get_retriever(thread_id)
    if retriever is None:
        return {
            "error": "No document indexed for this chat. Upload a PDF first.",
            "query": query,
        }

    result = retriever.invoke(query)
    context = [doc.page_content for doc in result]
    metadata = [doc.metadata for doc in result]

    return {
        "query": query,
        "context": context,
        "metadata": metadata,
        "source_file": _THREAD_METADATA.get(str(thread_id), {}).get("filename"),
    }

client = MultiServerMCPClient(
    {
        "arith_and_stocks": {
            "transport": "stdio",
            "command": "python",
            "args": [os.getenv("MCP_TOOLS_PATH")],
        },
        "expense": {
            "transport": "streamable_http",
            "url": os.getenv("EXPENSE_MCP_URL")
        }
    }
)

_mcp_future = _submit_async(client.get_tools())

async def _init_checkpointer():
    conn = await aiosqlite.connect(database="chatbot.db", check_same_thread=False)
    return AsyncSqliteSaver(conn)

checkpointer = run_async(_init_checkpointer())

_chatbot = None
_llm_with_tools = None

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

async def chat_node(state: ChatState, config=None):
    """LLM node that may answer or request a tool call."""
    thread_id = None
    if config and isinstance(config, dict):
        thread_id = config.get("configurable", {}).get("thread_id")

    system_message = SystemMessage(
        content=(
            "You are a helpful assistant. "
            "IMPORTANT: Never fabricate, guess, or hallucinate data. "
            "When you call a tool, present ONLY the data returned by that tool — "
            "do not add entries, numbers, or details from memory or previous turns. "
            "If a tool returns an empty result, say so honestly.\n\n"
            "For questions about the uploaded PDF, call the `rag_tool` and include "
            f"the thread_id `{thread_id}`. "
            "You can also use the web search, stock price, expense tracking tools "
            "and calculator tools when helpful. "
            "If no document is available, ask the user to upload a PDF."
        )
    )

    messages = [system_message, *state["messages"]]
    response = await _llm_with_tools.ainvoke(messages, config=config)
    return {"messages": [response]}


def get_chatbot():
    """Lazily compile the chatbot graph on first use.
    MCP tools load in the background at import; by the time the user
    sends their first message they are usually ready."""
    global _chatbot, _llm_with_tools
    if _chatbot is not None:
        return _chatbot

    try:
        mcp_tools = _mcp_future.result(timeout=30)
    except Exception:
        mcp_tools = []

    tools = [search_tool, rag_tool, *mcp_tools]
    _llm_with_tools = llm.bind_tools(tools) if tools else llm

    tool_node = ToolNode(tools) if tools else None

    graph = StateGraph(ChatState)
    graph.add_node("chat_node", chat_node)
    graph.add_edge(START, "chat_node")

    if tool_node:
        graph.add_node("tools", tool_node)
        graph.add_conditional_edges("chat_node", tools_condition)
        graph.add_edge("tools", "chat_node")
    else:
        graph.add_edge("chat_node", END)

    _chatbot = graph.compile(checkpointer=checkpointer)
    return _chatbot

# --- Thread names (persisted to JSON) ---
_NAMES_FILE = os.path.join(os.path.dirname(__file__), "thread_names.json")

def _load_thread_names() -> dict:
    try:
        with open(_NAMES_FILE, "r", encoding="utf-8") as f:
            import json
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return {}

def _save_thread_names(names: dict):
    import json
    with open(_NAMES_FILE, "w", encoding="utf-8") as f:
        json.dump(names, f, indent=2)

def rename_thread(thread_id: str, name: str):
    """Set a custom display name for a thread."""
    names = _load_thread_names()
    names[str(thread_id)] = name
    _save_thread_names(names)

def get_thread_name(thread_id: str) -> str:
    """Return custom name if set, otherwise the thread ID itself."""
    names = _load_thread_names()
    return names.get(str(thread_id), str(thread_id))

def get_all_thread_names() -> dict:
    """Return the full {thread_id: name} mapping."""
    return _load_thread_names()

# --- Thread listing ---
async def _alist_threads():
    all_threads = []
    seen = set()
    async for checkpoint in checkpointer.alist(None):
        tid = checkpoint.config["configurable"]["thread_id"]
        if tid not in seen:
            seen.add(tid)
            all_threads.append(tid)
    return list(reversed(all_threads))

def retrieve_all_threads():
    return run_async(_alist_threads())


def thread_has_document(thread_id: str) -> bool:
    return str(thread_id) in _THREAD_RETRIEVERS


def thread_document_metadata(thread_id: str) -> dict:
    return _THREAD_METADATA.get(str(thread_id), {})


def delete_thread(thread_id: str):
    """Delete a thread's checkpoints, name, and any in-memory data."""
    tid = str(thread_id)
    # Remove checkpoints from SQLite
    import sqlite3
    try:
        conn = sqlite3.connect("chatbot.db")
        conn.execute("DELETE FROM checkpoints WHERE thread_id = ?", (tid,))
        conn.execute("DELETE FROM writes WHERE thread_id = ?", (tid,))
        conn.commit()
        conn.close()
    except Exception:
        pass
    # Remove custom name
    names = _load_thread_names()
    names.pop(tid, None)
    _save_thread_names(names)
    # Remove in-memory retriever/metadata
    _THREAD_RETRIEVERS.pop(tid, None)
    _THREAD_METADATA.pop(tid, None)