import streamlit as st
from chatbot_backend import chatbot, retrieve_all_threads, set_conversation_name
from langchain_core.messages import HumanMessage, AIMessage
import uuid

def generate_thread_id():
    thread_id = uuid.uuid4()
    return thread_id

def reset_chat(conversation_name=None):
    thread_id = generate_thread_id()
    st.session_state['thread_id'] = thread_id
    st.session_state['conversation_name'] = conversation_name
    add_thread(st.session_state['thread_id'], conversation_name)
    st.session_state['message_history'] = []

def add_thread(thread_id, conversation_name=None):
    if str(thread_id) not in st.session_state['chat_threads']:
        display_name = conversation_name if conversation_name else str(thread_id)
        st.session_state['chat_threads'][str(thread_id)] = display_name

def load_conversation(thread_id):
    state = chatbot.get_state(config={'configurable': {'thread_id': thread_id}})
    return state.values.get('messages', [])

if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()

if 'conversation_name' not in st.session_state:
    st.session_state['conversation_name'] = None

if 'chat_threads' not in st.session_state:
    st.session_state['chat_threads'] = retrieve_all_threads()

st.sidebar.title('LangGraph Chatbot')

col1, col2 = st.sidebar.columns([3, 1])
with col1:
    new_chat_name = st.text_input('Chat name (optional)', placeholder='e.g., "Python Help"', key='new_chat_name_input')
with col2:
    if st.button('New Chat'):
        reset_chat(conversation_name=new_chat_name if new_chat_name else None)
        st.rerun()

st.sidebar.header('My Conversations')

for thread_id in list(st.session_state['chat_threads'].keys())[::-1]:
    conversation_name = st.session_state['chat_threads'][thread_id]
    if st.sidebar.button(conversation_name, key=str(thread_id)):
        st.session_state['thread_id'] = thread_id
        st.session_state['conversation_name'] = conversation_name
        messages = load_conversation(thread_id)

        temp_messages = []

        for msg in messages:
            if isinstance(msg, HumanMessage):
                role='user'
            else:
                role='assistant'
            temp_messages.append({'role': role, 'content': msg.content})

        st.session_state['message_history'] = temp_messages
        st.rerun()


if st.session_state['conversation_name']:
    st.title(st.session_state['conversation_name'])

for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.text(message['content'])

user_input = st.chat_input('Type here')

if user_input:
    if not st.session_state['conversation_name']:
        auto_name = user_input[:50] + ('...' if len(user_input) > 50 else '')
        st.session_state['conversation_name'] = auto_name
        set_conversation_name(st.session_state['thread_id'], auto_name)
        st.session_state['chat_threads'][str(st.session_state['thread_id'])] = auto_name

    st.session_state['message_history'].append({'role': 'user', 'content': user_input})
    with st.chat_message('user'):
        st.text(user_input)

    CONFIG = {'configurable': {'thread_id': st.session_state['thread_id']}}

    with st.chat_message("assistant"):
        def ai_only_stream():
            for message_chunk, metadata in chatbot.stream(
                {"messages": [HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode="messages"
            ):
                if isinstance(message_chunk, AIMessage):
                    yield message_chunk.content

        ai_message = st.write_stream(ai_only_stream())

    st.session_state['message_history'].append({'role': 'assistant', 'content': ai_message})