# 🧠 CouncilAI - Multi-LLM Debate System

**An AI Council where multiple frontier models discuss, debate, and deliver the best possible answer.**

🔗 Live App
[Launch CouncilAI on Streamlit Cloud](https://councilai-io.streamlit.app/)

## ✨ What is CouncilAI?

Instead of asking a single LLM, CouncilAI lets **multiple AI models** (Grok, Claude, Gemini, etc.) act as a council:
- They respond in parallel with different personas
- They see each other's answers and debate across rounds
- A **Chairman model** synthesizes the strongest final consensus

This approach significantly reduces hallucinations and produces more balanced, high-quality outputs.

## 🎥 Demo Video
[Watch the demo](https://www.loom.com/share/3fa9529d01f34033ac04616ce06cf10c)  


## 🚀 Features

- Multi-round debate with customizable personas
- Parallel model calls for speed
- Chairman synthesis for final best answer
- Cost-optimized (uses cheap & fast models via OpenRouter)
- Clean, interactive Streamlit UI with expandable discussion rounds
- Supports Grok, Claude, Gemini and more

## 🛠️ Tech Stack

- **Frontend**: Streamlit
- **LLM Orchestration**: LiteLLM (one key for 100+ models)
- **Backend**: Async Python
- **Deployment**: Streamlit Community Cloud

## 📸 Screenshots / GIFs

*(Add 2-3 screenshots or GIFs here showing:)*
- Sidebar with model selection
- Debate in progress
- Final consensus

## 🏗️ Architecture

```mermaid
flowchart TD
    A[User Query] --> B[Parallel Council Members]
    B --> C1[Grok - Truth-seeking Contrarian]
    B --> C2[Claude - Rigorous Analyst]
    B --> C3[Gemini - Creative Optimist]
    
    C1 --> D[Round 1 Responses]
    C2 --> D
    C3 --> D
    
    D --> E[Multi-Round Debate\nModels see previous responses]
    E --> F[Chairman Model]
    F --> G[Final Consensus + Best Answer]
    
    style A fill:#0A2540,stroke:#fff,color:#fff
    style G fill:#00C853,stroke:#fff,color:#fff
