import streamlit as st
import asyncio
from litellm import acompletion
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
async def run_council(query: str, models: list, personas: dict, num_rounds: int, chairman: str):
    all_responses = []
    all_rounds = []

    for r in range(num_rounds):
        tasks = []
        for model in models:
            system_prompt = f"""You are {model.split('/')[-1]} on the AI Council.
Your persona: {personas.get(model, 'Expert')}.
Be concise, insightful, and constructive."""

            user_content = query
            if all_responses:
                user_content += "\n\nPrevious responses:\n" + "\n".join([f"[{resp['model'].split('/')[-1]}]: {resp['content'][:300]}" for resp in all_responses])

            full_messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}]

            tasks.append(acompletion(
                model=model, 
                messages=full_messages, 
                temperature=0.7, 
                max_tokens=450
            ))

        responses = await asyncio.gather(*tasks)

        round_responses = []
        for i, resp in enumerate(responses):
            content = resp.choices[0].message.content
            response_dict = {"model": models[i], "content": content}
            round_responses.append(response_dict)
            all_responses.append(response_dict)

        all_rounds.append({"round": r+1, "responses": round_responses})

    chairman_system = "You are the impartial Chairman. Synthesize the strongest final answer from the full discussion."
    chairman_user_content = query + "\n\nCouncil discussion:\n" + "\n".join([f"[{resp['model'].split('/')[-1]}]: {resp['content']}" for resp in all_responses]) + "\n\nProvide the best consolidated solution."

    final_resp = await acompletion(
        model=chairman, 
        messages=[{"role": "system", "content": chairman_system}, {"role": "user", "content": chairman_user_content}],
        temperature=0.5, 
        max_tokens=600
    )
    
    return {"rounds": all_rounds, "final": final_resp.choices[0].message.content}

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

    start_time = time.time()   # Start timing

    with st.spinner("Council is debating..."):
        try:
            result = asyncio.run(run_council(query, selected_models, personas, num_rounds, chairman_model))
            end_time = time.time()
            time_taken = round(end_time - start_time, 2)

            # Display Discussion with Avatars
            st.subheader("📜 Council Discussion")
            for round_num, round_data in enumerate(result["rounds"], 1):
                with st.expander(f"Round {round_num}", expanded=True):
                    for resp in round_data["responses"]:
                        model_name = resp["model"].split("/")[-1]
                        avatar_key = next((k for k in MODEL_AVATARS if k in model_name.lower()), "gpt")
                        avatar = MODEL_AVATARS[avatar_key]
                        st.markdown(f"{avatar} **{model_name}**")
                        st.caption(personas.get(resp["model"], ""))
                        st.write(resp["content"])
                        st.divider()

            st.subheader("🏛️ Final Consensus")
            st.success(result["final"])

            # ====================== VISUAL COST & TIME PANEL ======================
            st.subheader("📊 Usage Analytics")

            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(label="⏱️ Time Taken", value=f"{time_taken} seconds")
            
            with col2:
                estimated_cost = round(0.03 + (len(selected_models) * num_rounds * 0.015), 4)
                st.metric(label="💰 Estimated Cost", value=f"${estimated_cost}")

            # Simple Cost Bar Visualization
            st.progress(min(estimated_cost / 0.20, 1.0))  # Assuming $0.20 is "high" for one run
            st.caption("Cost bar (0.20 USD = high usage for one council run)")

            st.info("💡 Tip: Using fewer models and 1 round keeps costs under 5 cents.")

        except Exception as e:
            error_text = str(e)
            if "valid model ID" in error_text or "invalid_request_error" in error_text:
                st.error("Model not available. Please try different models.")
            else:
                st.error(f"Error: {error_text}")