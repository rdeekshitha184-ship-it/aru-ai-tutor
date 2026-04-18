from typing import TypedDict
from langgraph.graph import StateGraph, END

from utils import (
    get_context,
    explain_and_question,
    evaluate_answer,
    extract_score,
    generate_correct_answer
)

# ------------------- STATE -------------------

class AgentState(TypedDict):
    concept: str
    vectorstore: object

    context: str
    explanation: str
    question: str

    answer: str
    evaluation: str
    score: int

    attempts: int
    decision: str

    hint: str
    simplified_explanation: str
    correct_answer: str


# ------------------- NEW: HINT AGENT -------------------

def hint_agent(state: AgentState):
    context = state["context"]

    prompt = f"""
    Give a small helpful hint (1-2 lines).
    Do NOT give the full answer.

    CONTEXT:
    {context}
    """

    from utils import llm
    hint = llm.invoke(prompt).content

    return {"hint": hint}


# ------------------- NEW: SIMPLIFIER AGENT -------------------

def simplifier_agent(state: AgentState):
    context = state["context"]
    concept = state["concept"]

    prompt = f"""
    Explain this concept in an even simpler way 
    like teaching a 10-year-old.

    CONTEXT:
    {context}
    """

    from utils import llm
    simple = llm.invoke(prompt).content

    return {"simplified_explanation": simple}


# ------------------- EXPLAINER -------------------

def explainer_agent(state: AgentState):
    concept = state["concept"]
    vectorstore = state["vectorstore"]

    context = get_context(vectorstore, concept)
    explanation, question = explain_and_question(concept, context)

    return {
        "context": context,
        "explanation": explanation,
        "question": question
    }


# ------------------- EVALUATOR -------------------

def evaluator_agent(state: AgentState):
    answer = state["answer"]
    context = state["context"]

    evaluation = evaluate_answer(answer, context)
    score = extract_score(evaluation)

    return {
        "evaluation": evaluation,
        "score": score
    }


# ------------------- CONTROLLER (UPGRADED) -------------------

def controller_agent(state: AgentState):
    score = state["score"]
    attempts = state["attempts"]

    # ✅ GOOD
    if score >= 7:
        return {"decision": "next", "attempts": 0}

    # 🔁 FIRST FAILURE → GIVE HINT
    elif attempts == 0:
        return {"decision": "hint", "attempts": 1}

    # 🔁 SECOND FAILURE → SIMPLIFY
    elif attempts == 1:
        return {"decision": "simplify", "attempts": 2}

    # ❌ FINAL → SHOW ANSWER
    else:
        correct = generate_correct_answer(state["context"])
        return {
            "decision": "fail",
            "correct_answer": correct,
            "attempts": 0
        }


# ------------------- GRAPH -------------------

def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("explainer", explainer_agent)
    graph.add_node("evaluator", evaluator_agent)
    graph.add_node("controller", controller_agent)

    graph.add_node("hint", hint_agent)
    graph.add_node("simplify", simplifier_agent)

    graph.set_entry_point("explainer")

    graph.add_edge("explainer", "evaluator")
    graph.add_edge("evaluator", "controller")

    graph.add_conditional_edges(
        "controller",
        lambda state: state["decision"],
        {
            "next": END,
            "hint": "hint",
            "simplify": "simplify",
            "fail": END
        }
    )

    graph.add_edge("hint", END)
    graph.add_edge("simplify", END)

    return graph.compile()