# chatbot-lite

**chatbot-lite** is a minimal, beginner-friendly chatbot built from scratch using **LangGraph** and a local LLM via **Ollama**.  
It is designed as a lightweight foundation that can later evolve into more advanced, workflow-based or multi-agent systems.

---

> Current version: **v0.2 – Streaming Chat**

---

## ✨ Features

- Simple conversational chatbot using LangGraph
- Local LLM support via Ollama
- Clean separation between backend logic and frontend UI
- Streamlit-based chat interface
- Thread-aware memory using LangGraph checkpointers
- Beginner-friendly and easy to extend
- Real-time streaming responses for a more natural chat experience

---

## 🧱 Tech Stack

- **Python**
- **LangGraph**
- **LangChain**
- **Ollama (local LLMs)**
- **Streamlit**

---

## 📂 Project Structure

```bash
chatbot-lite/
│
├── chatbot_backend.py      # LangGraph-based chatbot logic
├── streamlit_frontend.py   # Streamlit chat UI
├── README.md
└── requirements.txt        
```

---

## 🚀 Getting Started

### 1️⃣ Prerequisites

- Python 3.9+
- Ollama installed and running
- A local model pulled (example: `llama3.2:3b`)

```bash
ollama pull llama3.2:3b
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

1. User enters a message via the Streamlit UI  
2. Message is sent to a LangGraph state graph  
3. The chatbot node invokes the local LLM  
4. Responses are stored using a thread-based checkpointer  
5. The reply is rendered back in the UI  

This architecture is intentionally minimal and designed to scale.

---

## 🔮 Roadmap

- Add intent detection (Sentinel-style routing)
- Conditional graph flows
- Tool and function calling
- Persistent memory (DB / vector store)
- Multi-agent workflows

---

## 📌 Version

**v0.1 – Chatbot Lite**  
Single-node conversational agent built as a foundation project.

**v0.2 – Streaming Chat**  
Includes real-time streaming responses for a more natural chat experience.

---

## 📜 License

This project is open-source and free to use for learning and experimentation.
