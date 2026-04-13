from council_graph import council_graph, CouncilState
import streamlit as st
import asyncio
from langchain_core.messages import HumanMessage
import os
import time

st.set_page_config(page_title="CouncilAI", page_icon="🧠", layout="wide")

st.title("🧠 CouncilAI - Your AI Council")
st.markdown("Multiple frontier models **debate** → Critic reviews → Chairman delivers the best answer")

# ====================== MODEL AVATARS ======================
MODEL_AVATARS = {
    "grok": "🔍",
    "claude": "⚖️",
    "gpt": "🚀",
}

# ====================== AVAILABLE MODELS ======================
ALL_AVAILABLE_MODELS = [
    "openrouter/x-ai/grok-4.1-fast",
    "openrouter/anthropic/claude-sonnet-4-6",
    "openrouter/openai/gpt-4.1",
]

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

    # Council Members (Debaters)
    selected_models = st.multiselect(
        "Council Members (Debaters)", 
        ALL_AVAILABLE_MODELS, 
        default=[ALL_AVAILABLE_MODELS[0], ALL_AVAILABLE_MODELS[1]],
        help="These models will debate with each other"
    )

    # Chairman Selection
    chairman_model = st.selectbox(
        "Chairman Model (Final Synthesis)", 
        ALL_AVAILABLE_MODELS,
        index=1,   # Default to Claude Sonnet 4.6
        help="This model will synthesize the final answer. Recommended: Claude Sonnet 4.6"
    )

    st.caption("💡 **Recommended Chairman:** Claude Sonnet 4.6 for best synthesis")

    # Personas for debaters
    personas = {}
    for model in selected_models:
        short_name = model.split("/")[-1].replace("-", " ").title()
        avatar_key = next((k for k in MODEL_AVATARS if k in model.lower()), "gpt")
        avatar = MODEL_AVATARS[avatar_key]
        default_persona = "Truth-seeking contrarian" if "grok" in model else \
                          "Rigorous analytical thinker" if "claude" in model else \
                          "Creative optimist" if "gpt" in model else "Fast pragmatic engineer"
        
        personas[model] = st.text_input(f"{avatar} Persona for {short_name}", value=default_persona)

    num_rounds = st.slider("Number of Debate Rounds", 1, 3, 1)

    st.caption("💰 Tip: 2-3 debaters + Grok Critic + Claude Chairman = Great results")

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
        "criticisms": [],
        "current_round": 1,
        "num_rounds": num_rounds,
        "selected_models": selected_models,
        "personas": personas,
        "chairman_model": chairman_model,
        "final_answer": ""
    }

    with st.spinner("Council is debating... (Debate → Critic → Synthesis)"):
        try:
            result = asyncio.run(council_graph.ainvoke(initial_state))
            
            end_time = time.time()
            time_taken = round(end_time - start_time, 2)

            # ====================== DISPLAY DISCUSSION ======================
            st.subheader("📜 Council Discussion")

            tab1, tab2 = st.tabs(["💬 Live Chat View (WhatsApp Style)", "📋 Round-wise View"])

            # ------------------- Live Chat View (WhatsApp Style) -------------------
            with tab1:
                st.caption("Models debating like friends in a group chat 👥")

                # User Question
                with st.chat_message("user", avatar="👤"):
                    st.markdown(f"**Question:** {query}")

                # Debate Responses + Critic Feedback
                for round_list in result.get("round_responses", []):
                    for resp in round_list:
                        model_name = resp["model"].split("/")[-1]
                        avatar = MODEL_AVATARS.get(
                            next((k for k in MODEL_AVATARS if k in model_name.lower()), "gpt"), "🤖"
                        )
                        with st.chat_message(name=model_name, avatar=avatar):
                            st.caption(f"**{model_name}** • Round {resp.get('round', 1)}")
                            st.markdown(resp["content"])

                # Show Critic Feedback
                for crit in result.get("criticisms", []):
                    with st.chat_message(name="Critic", avatar="🧐"):
                        st.caption(f"**Critic (Grok)** • After Round {crit.get('round', '')}")
                        st.warning(crit["content"])

                # Final Chairman Synthesis
                if result.get("final_answer"):
                    with st.chat_message(name="Chairman", avatar="🏛️"):
                        st.caption(f"**Chairman ({chairman_model.split('/')[-1]})** • Final Synthesis")
                        st.success(result["final_answer"])

            # ------------------- Round-wise Structured View -------------------
            with tab2:
                round_dict = {}
                for round_list in result.get("round_responses", []):
                    for resp in round_list:
                        r = resp.get("round", 1)
                        if r not in round_dict:
                            round_dict[r] = []
                        round_dict[r].append(resp)

                for r in sorted(round_dict.keys()):
                    with st.expander(f"Round {r}", expanded=False):
                        for resp in round_dict[r]:
                            model_name = resp["model"].split("/")[-1]
                            avatar = MODEL_AVATARS.get(
                                next((k for k in MODEL_AVATARS if k in model_name.lower()), "gpt"), "🤖"
                            )
                            st.markdown(f"{avatar} **{model_name}**")
                            st.caption(personas.get(resp["model"], ""))
                            st.write(resp["content"])
                            st.divider()

                # Show Critic in Round-wise view too
                if result.get("criticisms"):
                    st.subheader("🧐 Critic Feedback")
                    for crit in result["criticisms"]:
                        st.warning(f"**After Round {crit.get('round')}**\n\n{crit['content']}")

            # ====================== USAGE ANALYTICS ======================
            st.subheader("📊 Usage Analytics")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("⏱️ Time Taken", f"{time_taken} seconds")
            with col2:
                estimated_cost = round(0.03 + (len(selected_models) * num_rounds * 0.025), 4)
                st.metric("💰 Estimated Cost", f"${estimated_cost:.4f}")

            st.progress(min(estimated_cost / 0.30, 1.0))
            st.caption("Cost bar (0.30 USD = high usage for one full run with critic)")

        except Exception as e:
            st.error(f"Error running council: {str(e)}")