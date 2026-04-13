import asyncio
from typing import TypedDict, Annotated, List, Dict
from operator import add
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from litellm import acompletion

# ====================== STATE DEFINITION ======================
class CouncilState(TypedDict):
    query: str                          # Original user question
    messages: Annotated[List[BaseMessage], add_messages]  # Full conversation history
    round_responses: Annotated[List[Dict], add]   # List of responses per round
    current_round: int
    num_rounds: int
    selected_models: List[str]
    personas: Dict[str, str]
    final_answer: str                   # Final chairman synthesis


# ====================== HELPER: CALL MODEL ASYNC ======================
async def call_model(model: str, system_prompt: str, user_content: str, temperature: float = 0.7, max_tokens: int = 500):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
    ]
    response = await acompletion(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens
    )
    return response.choices[0].message.content.strip()


# ====================== NODE: DEBATE ROUND (Parallel) ======================
async def debate_round(state: CouncilState) -> Dict:
    """One debate round where all council members respond in parallel"""
    current_round = state.get("current_round", 1)
    models = state["selected_models"]
    personas = state["personas"]
    query = state["query"]

    # Build context from previous responses
    previous_context = ""
    if state.get("round_responses"):
        previous = state["round_responses"][-len(models):]  # last round only
        previous_context = "\n\nPrevious round:\n" + "\n".join(
            [f"[{resp['model'].split('/')[-1]}]: {resp['content'][:400]}" for resp in previous]
        )

    tasks = []
    model_responses = []

    for model in models:
        system_prompt = f"""You are {model.split('/')[-1]} on the AI Council.
Your persona: {personas.get(model, 'Expert')}.
Be concise, insightful, constructive, and direct. Avoid fluff."""

        user_content = query + previous_context

        tasks.append(call_model(model, system_prompt, user_content))

    # Run all models in parallel
    raw_responses = await asyncio.gather(*tasks, return_exceptions=True)

    for i, content in enumerate(raw_responses):
        model_name = models[i]
        if isinstance(content, Exception):
            content = f"Error calling model: {str(content)}"
        
        response_dict = {
            "model": model_name,
            "content": str(content),
            "round": current_round
        }
        model_responses.append(response_dict)

        # Add to LangChain messages for history
        short_name = model_name.split("/")[-1]
        state["messages"].append(AIMessage(content=content, name=short_name))

    return {
        "round_responses": model_responses,
        "current_round": current_round + 1,
        "messages": []  # reducer will handle appending
    }


# ====================== NODE: CHAIRMAN SYNTHESIS ======================
async def chairman_synthesis(state: CouncilState) -> Dict:
    """Chairman model synthesizes the best final answer"""
    chairman = state["selected_models"][0]  # For now, use first model as chairman (we'll improve this)
    # In next part we'll make chairman selectable properly

    discussion = "\n\n".join([
        f"[{resp['model'].split('/')[-1]} Round {resp['round']}]: {resp['content']}"
        for round_list in state.get("round_responses", [])
        for resp in (round_list if isinstance(round_list, list) else [])
    ])

    system_prompt = """You are the impartial Chairman of the AI Council.
Synthesize the strongest, most balanced, and actionable final answer.
Combine the best ideas, resolve contradictions, and deliver a clear consensus."""

    user_content = f"""Original Question: {state['query']}

Council Discussion:
{discussion}

Provide the best consolidated solution."""

    final_content = await call_model(
        model=chairman,
        system_prompt=system_prompt,
        user_content=user_content,
        temperature=0.5,
        max_tokens=700
    )

    # Add final answer to messages
    state["messages"].append(AIMessage(content=final_content, name="Chairman"))

    return {
        "final_answer": final_content
    }


# ====================== BUILD THE GRAPH ======================
def build_council_graph():
    workflow = StateGraph(CouncilState)

    # Add nodes
    workflow.add_node("debate_round", debate_round)
    workflow.add_node("chairman_synthesis", chairman_synthesis)

    # Define flow
    workflow.add_edge(START, "debate_round")

    # Conditional routing: repeat debate rounds or go to chairman
    def should_continue(state: CouncilState):
        if state.get("current_round", 1) > state.get("num_rounds", 1):
            return "chairman_synthesis"
        return "debate_round"

    workflow.add_conditional_edges(
        "debate_round",
        should_continue,
        {
            "debate_round": "debate_round",
            "chairman_synthesis": "chairman_synthesis"
        }
    )

    workflow.add_edge("chairman_synthesis", END)

    return workflow.compile()


# For easy import
council_graph = build_council_graph()