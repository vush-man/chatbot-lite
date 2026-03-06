import queue
import uuid
import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from chatbot_backend import get_chatbot, ingest_pdf, retrieve_all_threads, thread_document_metadata, submit_async_task, rename_thread, get_thread_name, get_all_thread_names, delete_thread

def generate_thread_id():
    return uuid.uuid4()

def reset_chat():
    thread_id = generate_thread_id()
    st.session_state["thread_id"] = thread_id
    st.session_state["message_history"] = []

def add_thread(thread_id):
    if thread_id not in st.session_state["chat_threads"]:
        st.session_state["chat_threads"].append(thread_id)

def load_conversation(thread_id):
    state = get_chatbot().get_state(config={"configurable": {"thread_id": thread_id}})
    return state.values.get("messages", [])

if "message_history" not in st.session_state:
    st.session_state["message_history"] = []

if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = generate_thread_id()

if "chat_threads" not in st.session_state:
    st.session_state["chat_threads"] = retrieve_all_threads()

if "ingested_docs" not in st.session_state:
    st.session_state["ingested_docs"] = {}

thread_key = str(st.session_state["thread_id"])
thread_docs = st.session_state["ingested_docs"].setdefault(thread_key, {})
threads = st.session_state["chat_threads"]
thread_names = get_all_thread_names()
selected_thread = None

st.sidebar.title("LangGraph PDF Chatbot")

col_id, col_rename = st.sidebar.columns([3, 1])
current_display_name = thread_names.get(thread_key, thread_key[:8] + "…")
col_id.markdown(f"**Chat:** `{current_display_name}`")
with col_rename.popover("✏️"):
    new_name = st.text_input("Rename this chat", value=thread_names.get(thread_key, ""), key="rename_input")
    if st.button("Save", key="rename_save") and new_name.strip():
        rename_thread(thread_key, new_name.strip())
        st.rerun()

if st.sidebar.button("New Chat", use_container_width=True):
    reset_chat()
    st.rerun()

if thread_docs:
    latest_doc = list(thread_docs.values())[-1]
    st.sidebar.success(
        f"Using `{latest_doc.get('filename')}` "
        f"({latest_doc.get('chunks')} chunks from {latest_doc.get('documents')} pages)"
    )
else:
    st.sidebar.info("No PDF indexed yet.")

uploaded_pdf = st.sidebar.file_uploader("Upload a PDF for this chat", type=["pdf"])
if uploaded_pdf:
    if uploaded_pdf.name in thread_docs:
        st.sidebar.info(f"`{uploaded_pdf.name}` already processed for this chat.")
    else:
        with st.sidebar.status("Indexing PDF…", expanded=True) as status_box:
            summary = ingest_pdf(
                uploaded_pdf.getvalue(),
                thread_id=thread_key,
                filename=uploaded_pdf.name,
            )
            thread_docs[uploaded_pdf.name] = summary
            status_box.update(label="✅ PDF indexed", state="complete", expanded=False)

st.sidebar.subheader("Past conversations")
if not threads:
    st.sidebar.write("No past conversations yet.")
else:
    for thread_id in threads:
        tid = str(thread_id)
        display = thread_names.get(tid, tid[:8] + "…")
        col_btn, col_del = st.sidebar.columns([5, 1])
        if col_btn.button(display, key=f"side-thread-{tid}", help=tid, use_container_width=True):
            selected_thread = thread_id
        if col_del.button("🗑️", key=f"del-thread-{tid}", help="Delete this chat"):
            delete_thread(tid)
            if tid in st.session_state["chat_threads"]:
                st.session_state["chat_threads"].remove(tid)
            if thread_key == tid:
                reset_chat()
            st.rerun()

st.title("Multi Utility Chatbot")

# Chat area
for message in st.session_state["message_history"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_input = st.chat_input("Ask about your document or use tools")

if user_input:
    st.session_state["message_history"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    CONFIG = {
        "configurable": {"thread_id": thread_key},
        "metadata": {"thread_id": thread_key},
        "run_name": "chat_turn",
    }

    with st.chat_message("assistant"):
        tool_names_used: list[str] = []
        status_placeholder = st.empty()

        def ai_only_stream():
            event_queue: queue.Queue = queue.Queue()

            async def run_stream():
                try:
                    async for message_chunk, metadata in get_chatbot().astream(
                        {"messages": [HumanMessage(content=user_input)]},
                        config=CONFIG,
                        stream_mode="messages",
                    ):
                        event_queue.put((message_chunk, metadata))
                except Exception as exc:
                    event_queue.put(("error", exc))
                finally:
                    event_queue.put(None)

            submit_async_task(run_stream())

            while True:
                item = event_queue.get()
                if item is None:
                    break
                message_chunk, metadata = item
                if message_chunk == "error":
                    raise metadata

                if isinstance(message_chunk, ToolMessage):
                    tool_name = getattr(message_chunk, "name", "tool")
                    tool_names_used.append(tool_name)
                    status_placeholder.info(f"🔧 Using `{tool_name}` …")

                # Stream ONLY non-empty assistant tokens
                if isinstance(message_chunk, AIMessage) and message_chunk.content:
                    yield message_chunk.content

        ai_message = st.write_stream(ai_only_stream())

        if tool_names_used:
            status_placeholder.success(f"✅ Used: {', '.join(tool_names_used)}")
        else:
            status_placeholder.empty()

    st.session_state["message_history"].append(
        {"role": "assistant", "content": ai_message or ""}
    )
    add_thread(st.session_state["thread_id"])

    doc_meta = thread_document_metadata(thread_key)
    if doc_meta:
        st.caption(
            f"Document indexed: {doc_meta.get('filename')} "
            f"(chunks: {doc_meta.get('chunks')}, pages: {doc_meta.get('documents')})"
        )

st.divider()

if selected_thread:
    st.session_state["thread_id"] = selected_thread
    messages = load_conversation(selected_thread)

    temp_messages = []
    for msg in messages:
        if isinstance(msg, ToolMessage):
            continue
        role = "user" if isinstance(msg, HumanMessage) else "assistant"
        temp_messages.append({"role": role, "content": msg.content})
    st.session_state["message_history"] = temp_messages
    st.session_state["ingested_docs"].setdefault(str(selected_thread), {})
    st.rerun()