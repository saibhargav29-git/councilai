from council_graph import council_graph, CouncilState
import streamlit as st
import asyncio
from langchain_core.messages import HumanMessage
import os
import time

st.set_page_config(page_title="CouncilAI", page_icon="🧠", layout="wide")

st.title("🧠 CouncilAI - Your AI Council")
st.markdown("Multiple frontier models debate and deliver the **best answer**")

# ====================== MODEL AVATARS ======================
MODEL_AVATARS = {
    "grok": "🔍",
    "claude": "⚖️",
    "gpt": "🚀",
}

# ====================== SIDEBAR ======================
with st.sidebar:
    st.header("Council Settings")
    
    openrouter_key = st.text_input(
        "OpenRouter API Key", 
        type="password", 
        value=os.getenv("OPENROUTER_API_KEY", ""),
        help="Paste your key here (starts with sk-or-v1-...)"
    )
    
    if openrouter_key:
        os.environ["OPENROUTER_API_KEY"] = openrouter_key

    available_models = [
        "openrouter/x-ai/grok-4.1-fast",
        "openrouter/anthropic/claude-sonnet-4-6",
        "openrouter/openai/gpt-4.1"
    ]
    
    selected_models = st.multiselect(
        "Select Council Members (2-3 recommended)", 
        available_models, 
        default=[available_models[0], available_models[1]]
    )

    personas = {}
    for model in selected_models:
        short_name = model.split("/")[-1].replace("-", " ")
        avatar_key = next((k for k in MODEL_AVATARS if k in model.lower()), "gpt")
        avatar = MODEL_AVATARS[avatar_key]
        default_persona = "Truth-seeking contrarian" if "grok" in model else \
                          "Rigorous analytical thinker" if "claude" in model else \
                          "Creative optimist" if "gpt" in model else "Fast pragmatic engineer"
        personas[model] = st.text_input(f"{avatar} Persona for {short_name}", value=default_persona)

    num_rounds = st.slider("Number of Debate Rounds", 1, 3, 1)
    chairman_model = st.selectbox("Chairman Model (Final Synthesis)", selected_models)

    st.caption("💰 Using cheap models → ~2–8 cents per run")

# ====================== MAIN INPUT ======================
query = st.text_area(
    "What should the AI Council discuss?", 
    height=130,
    placeholder="What are the best career moves for someone strong in DevSecOps and Python in 2026?"
)

if st.button("🚀 Convene the Council", type="primary", use_container_width=True):
    if not openrouter_key:
        st.error("Please enter your OpenRouter API Key")
        st.stop()
    
    if len(selected_models) < 1:
        st.error("Please select at least one council member")
        st.stop()

    start_time = time.time()

    # Prepare initial state
    initial_state: CouncilState = {
        "query": query,
        "messages": [HumanMessage(content=query)],
        "round_responses": [],
        "current_round": 1,
        "num_rounds": num_rounds,
        "selected_models": selected_models,
        "personas": personas,
        "final_answer": ""
    }

    with st.spinner("Council is debating using LangGraph..."):
        try:
            # Run the graph
            result = asyncio.run(council_graph.ainvoke(initial_state))
            
            end_time = time.time()
            time_taken = round(end_time - start_time, 2)

            # ====================== DISPLAY DISCUSSION ======================
            st.subheader("📜 Council Discussion")
            
            # Group responses by round (LangGraph stores them flattened)
            round_dict = {}
            for resp_list in result.get("round_responses", []):
                if not isinstance(resp_list, list):
                    resp_list = [resp_list]
                for resp in resp_list:
                    r = resp.get("round", 1)
                    if r not in round_dict:
                        round_dict[r] = []
                    round_dict[r].append(resp)

            for r in sorted(round_dict.keys()):
                with st.expander(f"Round {r}", expanded=True):
                    for resp in round_dict[r]:
                        model_name = resp["model"].split("/")[-1]
                        avatar_key = next((k for k in MODEL_AVATARS if k in model_name.lower()), "gpt")
                        avatar = MODEL_AVATARS[avatar_key]
                        
                        st.markdown(f"{avatar} **{model_name}**")
                        st.caption(personas.get(resp["model"], ""))
                        st.write(resp["content"])
                        st.divider()

            # Final Answer
            st.subheader("🏛️ Final Consensus")
            st.success(result.get("final_answer", "No final answer generated."))

            # Analytics
            st.subheader("📊 Usage Analytics")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("⏱️ Time Taken", f"{time_taken} seconds")
            with col2:
                estimated_cost = round(0.03 + (len(selected_models) * num_rounds * 0.015), 4)
                st.metric("💰 Estimated Cost", f"${estimated_cost:.4f}")

            st.progress(min(estimated_cost / 0.20, 1.0))
            st.caption("Cost bar (0.20 USD = high usage)")

        except Exception as e:
            st.error(f"Error running council graph: {str(e)}")