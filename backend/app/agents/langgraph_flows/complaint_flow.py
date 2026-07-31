from typing import Literal, TypedDict

from langgraph.graph import END, StateGraph

from app.core.config import settings
from app.core.llm import LLMClient
from app.knowledge.retriever import Retriever

llm = LLMClient(
    api_key=settings.llm_api_key,
    base_url=settings.llm_base_url,
    model=settings.llm_model,
)

retriever = Retriever(alpha=0.7)


class ComplaintState(TypedDict):
    user_id: str
    message: str
    session_id: str
    severity: str
    order_info: str
    policy: str
    solution: str
    user_accepts: bool
    step: int


async def classify_severity(state: ComplaintState) -> dict:
    prompt = (
        f"用户投诉: {state['message']}\n请判断严重程度: high / medium / low，只返回一个词。"
    )
    r = await llm.chat([{"role": "user", "content": prompt}])
    severity = r.strip().lower()
    if severity not in ["high", "medium", "low"]:
        severity = "medium"
    return {"severity": severity, "step": 1}


async def query_order(state: ComplaintState) -> dict:
    return {"order_info": "订单信息已查询（模拟）", "step": 2}


async def check_policy(state: ComplaintState) -> dict:
    results = await retriever.retrieve(state["message"], top_k=2)
    policy = (
        "\n\n".join([r["text"] for r in results])
        if results
        else "未找到相关政策，需转人工确认"
    )
    return {"policy": policy, "step": 3}


async def generate_solution(state: ComplaintState) -> dict:
    prompt = (
        f"投诉: {state['message']}\n严重程度: {state['severity']}\n"
        f"相关政策知识:\n{state['policy']}\n\n"
        "请依据上述政策知识给出解决方案，不超过80字。"
        "如果政策是'未找到相关政策，需转人工确认'，则建议转人工处理。"
    )
    r = await llm.chat([{"role": "user", "content": prompt}])
    return {"solution": r, "step": 4}


async def escalate_human(state: ComplaintState) -> dict:
    return {"solution": "已转接人工客服，请稍候。", "step": 5}


async def confirm_resolution(state: ComplaintState) -> dict:
    return {"user_accepts": True, "step": 6}


def route_after_classify(
    state: ComplaintState,
) -> Literal["escalate_human", "query_order"]:
    if state["severity"] == "high":
        return "escalate_human"
    return "query_order"


def route_after_solution(state: ComplaintState) -> Literal["escalate_human", END]:
    if not state.get("user_accepts", False):
        return "escalate_human"
    return END


workflow = StateGraph(ComplaintState)
workflow.add_node("classify_severity", classify_severity)
workflow.add_node("query_order", query_order)
workflow.add_node("check_policy", check_policy)
workflow.add_node("generate_solution", generate_solution)
workflow.add_node("escalate_human", escalate_human)
workflow.add_node("confirm_resolution", confirm_resolution)
workflow.set_entry_point("classify_severity")
workflow.add_conditional_edges("classify_severity", route_after_classify)
workflow.add_edge("query_order", "check_policy")
workflow.add_edge("check_policy", "generate_solution")
workflow.add_edge("generate_solution", "confirm_resolution")
workflow.add_conditional_edges("confirm_resolution", route_after_solution)
workflow.add_edge("escalate_human", END)

complaint_graph = workflow.compile()
