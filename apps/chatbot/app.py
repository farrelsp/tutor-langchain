import os
import uuid
import sqlite3
import streamlit as st
from dotenv import load_dotenv

from langchain_ollama import ChatOllama
from langchain_core.prompts import (
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    ChatPromptTemplate,
    MessagesPlaceholder,
)
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import SQLChatMessageHistory

# Environment
load_dotenv(".env")  

DB_PATH = "sqlite:///chat_history.db"
RAW_DB_PATH = "chat_history.db"        

def ensure_chat_history_table():
    conn = sqlite3.connect(RAW_DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            message_type TEXT,   -- 'human' or 'ai'
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()

def list_sessions():
    """Return all distinct session_ids, newest last (based on last message)."""
    conn = sqlite3.connect(RAW_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT session_id
        FROM chat_history
        GROUP BY session_id
        ORDER BY MAX(id) DESC
    """)
    sessions = [row[0] for row in cursor.fetchall()]
    conn.close()
    return sessions

ensure_chat_history_table()

# LLM & LangChain setup
base_url  = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/")
model_name = os.getenv("OLLAMA_MODEL", "llama3.2:1b")

llm = ChatOllama(
    base_url=base_url,
    model=model_name,
)

prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate.from_template("You are a helpful assistant."),
        MessagesPlaceholder(variable_name="history"),
        HumanMessagePromptTemplate.from_template("{input}"),
    ]
)

chain = prompt | llm | StrOutputParser()

def get_sql_history(sid: str):
    return SQLChatMessageHistory(
        session_id=sid,
        connection=DB_PATH,
        table_name="chat_history",
    )

def chain_with_history():
    return RunnableWithMessageHistory(
        chain,
        get_session_history=get_sql_history,
        input_messages_key="input",
        history_messages_key="history",
    )

# Streamlit UI
st.set_page_config(page_title="CetJPT", page_icon="🤖")
st.title("CetJPT")
st.caption("Chat with me – the friendly cousin of ChatGPT, running LLaMA!")

# Sidebar: Session selection 
st.sidebar.header("🗂️ Chat Sessions")

existing_sessions = list_sessions()
SESSION_NEW = "Start new chat"

chosen = st.sidebar.selectbox(
    "Select or create a session", existing_sessions + [SESSION_NEW]
)

if "session_id" not in st.session_state or chosen == SESSION_NEW:
    # Generate a new unique session_id
    st.session_state.session_id = f"chat-{uuid.uuid4().hex[:8]}"
    st.session_state.history = []          
else:
    st.session_state.session_id = chosen

session_id = st.session_state.session_id

# Load history for the active session 
if ("history" not in st.session_state or st.session_state.get("last_loaded_session") != session_id):
    db_history = get_sql_history(session_id)
    st.session_state.history = [
        {"role": m.type, "content": m.content} for m in db_history.messages
    ]
    st.session_state.last_loaded_session = session_id

# Show past dialogue 
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input 
user_input = st.chat_input("Ask anything…")

def chat_generator(user_text):
    config = {"configurable": {"session_id": session_id}}
    yield from chain_with_history().stream({"input": user_text}, config=config)

if user_input:
    # Show user msg
    with st.chat_message("human"):
        st.markdown(user_input)
    st.session_state.history.append({"role": "human", "content": user_input})

    # Show assistant msg
    with st.chat_message("ai"):
        acc = []
        def streamer():
            for chunk in chat_generator(user_input):
                acc.append(chunk)
                yield chunk
        st.write_stream(streamer())
        ai_response = "".join(acc)

    st.session_state.history.append({"role": "ai", "content": ai_response})
