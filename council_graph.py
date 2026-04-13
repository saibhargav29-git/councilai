import asyncio
from typing import TypedDict, Annotated, List, Dict
from operator import add
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from litellm import acompletion

# ====================== STATE ======================
class CouncilState(TypedDict):
    query: str
    messages: Annotated[List[BaseMessage], add_messages]
    round_responses: Annotated[List[List[Dict]], add]
    criticisms: Annotated[List[Dict], add]
    current_round: int
    num_rounds: int
    selected_models: List[str]
    personas: Dict[str, str]
    chairman_model: str
    final_answer: str


# ====================== HELPER ======================
async def call_model(model: str, system_prompt: str, user_content: str, temperature: float = 0.7, max_tokens: int = 600):
    try:
        response = await acompletion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[Error with {model.split('/')[-1]}]: {str(e)}"


# ====================== NODE: DEBATE ROUND ======================
async def debate_round(state: CouncilState) -> Dict:
    current_round = state["current_round"]
    models = state["selected_models"]
    personas = state["personas"]
    query = state["query"]

    # Include previous criticism if available
    criticism_context = ""
    if state.get("criticisms"):
        last_crit = state["criticisms"][-1]
        criticism_context = f"\n\nCritic's feedback from previous round:\n{last_crit['content']}"

    previous_context = ""
    if state.get("round_responses"):
        last_round = state["round_responses"][-1]
        previous_context = "\n\nPrevious round responses:\n" + "\n".join(
            [f"[{resp['model'].split('/')[-1]}]: {resp['content'][:450]}" for resp in last_round]
        )

    tasks = []
    for model in models:
        system_prompt = f"""You are {model.split('/')[-1]} on the AI Council.
Your persona: {personas.get(model, 'Expert')}.
Be concise, insightful, constructive, and direct."""

        user_content = query + previous_context + criticism_context
        tasks.append(call_model(model, system_prompt, user_content, temperature=0.75))

    raw_responses = await asyncio.gather(*tasks, return_exceptions=True)

    this_round = []
    for i, content in enumerate(raw_responses):
        model_name = models[i]
        content_str = str(content) if not isinstance(content, Exception) else f"Error: {content}"

        response_dict = {"model": model_name, "content": content_str, "round": current_round}
        this_round.append(response_dict)

        short_name = model_name.split("/")[-1]
        state["messages"].append(AIMessage(content=content_str, name=short_name))

    return {
        "round_responses": [this_round],
        "current_round": current_round + 1,
    }


# ====================== NODE: CRITIC (Dedicated Grok) ======================
async def critic_node(state: CouncilState) -> Dict:
    """Sharp Critic using Grok by default for strong, honest feedback"""
    if not state.get("round_responses"):
        return {"criticisms": []}

    last_round = state["round_responses"][-1]

    discussion = "\n\n".join([
        f"[{resp['model'].split('/')[-1]}]: {resp['content']}" for resp in last_round
    ])

    system_prompt = """You are a sharp, honest, and ruthless Critic on the AI Council.
Your job is to find flaws and weaknesses in the latest round.
Point out:
- Shallow reasoning or weak arguments
- Contradictions between models
- Important perspectives that were missed
- Overconfidence or hidden biases
- Areas needing deeper analysis

Be direct, constructive, and concise (max 350 words)."""

    user_content = f"""Original Question: {state['query']}

Latest Round Discussion:
{discussion}

Give honest critical feedback to help the council improve in the next round."""

    # Always use Grok as Critic (best for critical thinking)
    critic_model = "openrouter/x-ai/grok-4.1-fast"

    criticism = await call_model(
        model=critic_model,
        system_prompt=system_prompt,
        user_content=user_content,
        temperature=0.65,
        max_tokens=450
    )

    critic_entry = {
        "round": state["current_round"] - 1,
        "model": critic_model,
        "content": criticism
    }

    return {"criticisms": [critic_entry]}


# ====================== NODE: CHAIRMAN ======================
async def chairman_synthesis(state: CouncilState) -> Dict:
    chairman = state["chairman_model"]

    discussion = ""
    for round_list in state.get("round_responses", []):
        for resp in round_list:
            short_name = resp["model"].split("/")[-1]
            discussion += f"[{short_name} Round {resp['round']}]: {resp['content']}\n\n"

    system_prompt = """You are the impartial Chairman of the AI Council.
Synthesize the strongest, most balanced, and actionable final answer.
Combine the best ideas, resolve contradictions, and deliver a clear, high-quality consensus."""

    user_content = f"""Original Question: {state['query']}

Full Council Discussion + Critic Feedback:
{discussion}

Provide the best consolidated solution."""

    final_content = await call_model(
        model=chairman,
        system_prompt=system_prompt,
        user_content=user_content,
        temperature=0.5,
        max_tokens=800
    )

    state["messages"].append(AIMessage(content=final_content, name="Chairman"))

    return {"final_answer": final_content}


# ====================== BUILD GRAPH ======================
def build_council_graph():
    workflow = StateGraph(CouncilState)

    workflow.add_node("debate_round", debate_round)
    workflow.add_node("critic", critic_node)
    workflow.add_node("chairman_synthesis", chairman_synthesis)

    workflow.add_edge(START, "debate_round")

    def should_continue(state: CouncilState):
        if state.get("current_round", 1) > state.get("num_rounds", 1):
            return "chairman_synthesis"
        return "critic"

    workflow.add_conditional_edges(
        "debate_round",
        should_continue,
        {"critic": "critic", "chairman_synthesis": "chairman_synthesis"}
    )

    workflow.add_edge("critic", "debate_round")
    workflow.add_edge("chairman_synthesis", END)

    return workflow.compile()


council_graph = build_council_graph()