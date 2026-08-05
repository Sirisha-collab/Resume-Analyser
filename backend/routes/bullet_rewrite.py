import os
import re
from typing import List, Optional, TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
MAX_ATTEMPTS = 3
MAX_LENGTH_RATIO = 1.7

NUMBER_PATTERN = re.compile(r"\d+(?:[.,]\d+)?\s*%?")
FIRST_PERSON = re.compile(r"\b(?:i|my|me|we|our)\b", re.IGNORECASE)
TECH_TOKEN = re.compile(r"\b[A-Za-z][A-Za-z0-9.+#-]{2,}\b")

SYSTEM_PROMPT = """You rewrite resume bullets to be stronger and more specific.

Hard rules:
- Never invent numbers, percentages, durations, team sizes, or dollar amounts.
  If the original has no metric, leave a bracketed placeholder instead.
- Never introduce a technology, tool, company, or achievement not present in
  the original bullet.
- Open with a strong past-tense action verb.
- One sentence. No first person. No trailing period needed.
- Keep it close in length to the original.

Return ONLY the rewritten bullet. No preamble, no quotes, no explanation."""


class BulletState(TypedDict):
    original: str
    context: str
    draft: Optional[str]
    issues: List[str]
    attempts: int
    accepted: bool
    source: str


_llm = None


def get_llm():
    global _llm
    if _llm is None:
        _llm = ChatGroq(model=GROQ_MODEL, temperature=0.3)
    return _llm


# ----------------------------------------------------------------- nodes -----
def rewrite_node(state: BulletState) -> dict:
  
    parts = [f"Original bullet:\n{state['original']}"]

    if state.get("context"):
        parts.append(
            f"\nTarget role context (for emphasis only — do not import "
            f"claims from it):\n{state['context'][:600]}"
        )

    if state.get("issues"):
        parts.append(
            "\nYour previous attempt was rejected for:\n"
            + "\n".join(f"- {issue}" for issue in state["issues"])
            + "\nFix these and try again."
        )

    try:
        response = get_llm().invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content="\n".join(parts)),
        ])
        draft = (response.content or "").strip().strip('"').strip()
    except Exception as exc:
        return {
            "draft": None,
            "issues": [f"LLM call failed: {exc}"],
            "attempts": state["attempts"] + 1,
        }

    return {"draft": draft, "attempts": state["attempts"] + 1}


def validate_node(state: BulletState) -> dict:
    
    from services.resume_fix_service import _looks_like_verb, _first_word

    draft = (state.get("draft") or "").strip()
    original = state["original"]
    issues: List[str] = []

    if not draft:
        return {"issues": ["Empty rewrite."], "accepted": False}

    # 1. Fabricated numbers — the failure mode that matters most.
    original_numbers = {n.replace(" ", "") for n in NUMBER_PATTERN.findall(original)}
    draft_numbers = {n.replace(" ", "") for n in NUMBER_PATTERN.findall(draft)}
    invented = draft_numbers - original_numbers
    if invented:
        issues.append(
            f"Invented figures not in the original: {', '.join(sorted(invented))}. "
            f"Use a bracketed placeholder instead."
        )

    # 2. Invented technologies or entities.
    original_tokens = {t.lower() for t in TECH_TOKEN.findall(original)}
    new_tokens = {
        t for t in TECH_TOKEN.findall(draft)
        if t.lower() not in original_tokens
        and (any(c.isdigit() for c in t) or "." in t or t[0].isupper())
        and not _looks_like_verb(t.lower())
    }
    # A leading capitalized verb is expected, so ignore the first word.
    new_tokens.discard(draft.split()[0] if draft.split() else "")
    if new_tokens:
        issues.append(
            f"Introduced terms absent from the original: "
            f"{', '.join(sorted(new_tokens))}."
        )

    # 3. Opens with an action verb.
    if not _looks_like_verb(_first_word(draft)):
        issues.append("Does not open with a past-tense action verb.")

    # 4. First person.
    if FIRST_PERSON.search(draft):
        issues.append("Contains first-person pronouns.")

    # 5. Length drift.
    if len(draft.split()) > len(original.split()) * MAX_LENGTH_RATIO + 6:
        issues.append("Substantially longer than the original.")

    return {"issues": issues, "accepted": not issues}


def fallback_node(state: BulletState) -> dict:
   
    from services.resume_fix_service import rewrite_bullet

    result = rewrite_bullet(state["original"])
    return {
        "draft": result.get("improved") or state["original"],
        "accepted": True,
        "source": "regex-fallback",
    }


def approval_node(state: BulletState) -> dict:
    """
    Human-in-the-loop gate.
    """
    if not state.get("draft"):
        return {}

    if os.getenv("BULLET_REWRITE_HITL", "").lower() in ("1", "true", "yes"):
        from langgraph.types import interrupt

        decision = interrupt({
            "original": state["original"],
            "proposed": state["draft"],
            "question": "Approve this rewrite?",
        })
        if isinstance(decision, dict) and decision.get("approved") is False:
            return {"draft": state["original"], "source": "rejected-by-user"}

    return {}


# ------------------------------------------------------------- routing -------
def route_after_validate(state: BulletState) -> str:
    if state.get("accepted"):
        return "approval"
    if state["attempts"] >= MAX_ATTEMPTS:
        return "fallback"
    return "rewrite"


_graph = None


def build_bullet_graph(checkpointer=None):
    global _graph
    if _graph is not None and checkpointer is None:
        return _graph

    builder = StateGraph(BulletState)
    builder.add_node("rewrite", rewrite_node)
    builder.add_node("validate", validate_node)
    builder.add_node("fallback", fallback_node)
    builder.add_node("approval", approval_node)

    builder.add_edge(START, "rewrite")
    builder.add_edge("rewrite", "validate")
    builder.add_conditional_edges(
        "validate",
        route_after_validate,
        {"rewrite": "rewrite", "fallback": "fallback", "approval": "approval"},
    )
    builder.add_edge("fallback", "approval")
    builder.add_edge("approval", END)

    compiled = builder.compile(checkpointer=checkpointer)

    if checkpointer is None:
        _graph = compiled
    return compiled


# -------------------------------------------------------------- public -------
def rewrite_bullets(bullets: List[str], context: str = "") -> List[dict]:
  
    graph = build_bullet_graph()
    results = []

    for bullet in bullets:
        initial: BulletState = {
            "original": bullet,
            "context": context,
            "draft": None,
            "issues": [],
            "attempts": 0,
            "accepted": False,
            "source": "llm",
        }

        try:
            final = graph.invoke(initial)
            results.append({
                "original": bullet,
                "improved": final.get("draft") or bullet,
                "source": final.get("source", "llm"),
                "attempts": final.get("attempts", 0),
                "rejected_for": final.get("issues", []),
            })
        except Exception as exc:
            print(f"BULLET REWRITE FAILED: {bullet[:60]} -> {exc}")
            results.append({
                "original": bullet,
                "improved": bullet,
                "source": "error",
                "attempts": 0,
                "rejected_for": [str(exc)],
            })

    return results