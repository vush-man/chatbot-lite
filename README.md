# chatbot-lite

**chatbot-lite** is a minimal, beginner-friendly chatbot built from scratch using **LangGraph** and a local LLM via **Ollama**.  
It is designed as a lightweight foundation that can later evolve into more advanced, workflow-based or multi-agent systems.

---

> Current version: **v0.4 – Tools, RAG, & MCP Support**

---

## ✨ Features

- Conversational chatbot built using LangGraph
- Local LLM support via Ollama
- **RAG (Retrieval-Augmented Generation)**: Upload and chat with PDFs, powered by FAISS
- **Tool Calling & Automation**: Built-in tools for DuckDuckGo Web Search, Math calculations, etc.
- **MCP (Model Context Protocol)**: Seamless integration with remote MCP servers (e.g., Stock Prices, Expense Tracker)
- Clean separation between backend logic and frontend UI
- Streamlit-based chat interface
- Persistent chat memory using SQLite (conversations survive restarts)
- Rename, delete, and resume previous conversations by thread
- Real-time streaming responses for a natural chat experience
- Beginner-friendly and heavily extensible

---

## 🧱 Tech Stack

- **Python**
- **LangGraph**
- **LangChain**
- **Ollama (local LLMs)**
- **Streamlit**
- **FAISS & PyPDF (for RAG)**
- **Model Context Protocol (MCP)**

---

## 📂 Project Structure

```bash
chatbot-lite/
│
├── chatbot_backend.py      # LangGraph-based chatbot logic, RAG, and MCP clients
├── streamlit_frontend.py   # Streamlit chat UI, file upload, and rendering
├── mcp_tools.py            # Local MCP server implementation (Stocks, Math)
├── README.md               # Documentation
├── .env.example            # Environment variables template
└── requirements.txt        # Python dependencies
```

---

## 🚀 Getting Started

### 1️⃣ Prerequisites

- Python 3.9+
- Ollama installed and running
- A local model pulled (example: `qwen2.5:3b`)

```bash
ollama pull qwen2.5:3b
```

---

### 2️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 3️⃣ Run the Chatbot

```bash
streamlit run streamlit_frontend.py
```

Your chatbot will be available in the browser 🚀

---

## 🧠 How It Works (High-Level)

1. User enters a message or uploads a PDF via the Streamlit UI  
2. The message is passed into a **LangGraph state graph**
3. The chatbot node invokes the local LLM, providing it access to **RAG context**, **Local Tools**, and **Remote MCP Tools**
4. If the LLM decides to use a tool, the **ToolNode** executes the action and returns the output to the LLM
5. Conversations and uploaded document metadata are persisted using SQLite-backed checkpointers
6. The final generated reply is streamed back to the UI in real-time

This architecture is modular, scalable, and easy to extend with new tools or completely new agents.

---

## 🔮 Roadmap

- Add intent detection (Sentinel-style routing)
- Conditional graph flows
- Multi-agent workflows

---

## 📌 Version

**v0.2 – Streaming Chat**  
Introduced real-time streaming responses for a more natural chat experience.

**v0.3 – Persistent Chat**  
Added SQLite-backed persistent memory, conversation management, and resume chat functionality.

**v0.4 – Tools, RAG, & MCP Support**  
Introduced Retrieval-Augmented Generation for PDFs, native Langchain tool calling (Web Search), and integration with Model Context Protocol (MCP) servers for extended capabilities (Stocks, Math, Expenses). UI enhancements for thread management (Rename/Delete).

---

## 📜 License

This project is open-source and free to use for learning and experimentation.
