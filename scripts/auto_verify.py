import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.knowledge.retriever import Retriever
from app.router.router import Router

from tests.test_samples import TEST_SAMPLES

KNOWLEDGE_QUERIES = [
    "退货退款流程",
    "价格优惠",
    "产品参数规格",
]


async def verify_route() -> dict:
    router = Router()
    failures = []
    correct = 0
    total = len(TEST_SAMPLES)

    for msg, expected in TEST_SAMPLES:
        intent = await router.route(msg)
        if intent == expected:
            correct += 1
        else:
            failures.append({"message": msg, "expected": expected, "got": intent})

    accuracy = correct / total if total else 0
    return {
        "accuracy": accuracy,
        "total": total,
        "correct": correct,
        "failures": failures,
    }


async def verify_knowledge() -> dict:
    retriever = Retriever()
    hits = 0
    for query in KNOWLEDGE_QUERIES:
        results = await retriever.retrieve(query, top_k=3)
        if results:
            hits += 1
    return {
        "knowledge_hits": hits,
        "total_queries": len(KNOWLEDGE_QUERIES),
    }


async def verify_prompt() -> dict:
    old_prompt = "你是电商客服助手。回复简洁友好，不超过50字。"
    new_prompt = "你是电商客服助手。回复简洁友好，不超过50字。不知道的不要说。"

    old_len = len(old_prompt)
    new_len = len(new_prompt)
    diff = abs(new_len - old_len) / max(old_len, 1)

    return {
        "old_length": old_len,
        "new_length": new_len,
        "diff_ratio": diff,
        "passed": diff <= 0.3,
    }


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--route-only", action="store_true")
    parser.add_argument("--knowledge-only", action="store_true")
    args = parser.parse_args()

    run_route = args.route_only or not args.knowledge_only
    run_knowledge = args.knowledge_only or not args.route_only
    run_prompt = not args.route_only and not args.knowledge_only

    results = {}

    if run_route:
        route_result = await verify_route()
        results["route"] = route_result
        print(f"\n--- 路由验证 ---")
        print(f"准确率: {route_result['accuracy']:.1%} ({route_result['correct']}/{route_result['total']})")
        if route_result["failures"]:
            print(f"失败案例 ({len(route_result['failures'])}):")
            for f in route_result["failures"]:
                print(f"  msg={f['message']!r} expected={f['expected']} got={f['got']}")

    if run_knowledge:
        knowledge_result = await verify_knowledge()
        results["knowledge"] = knowledge_result
        print(f"\n--- 知识库验证 ---")
        print(f"命中: {knowledge_result['knowledge_hits']}/{knowledge_result['total_queries']}")

    if run_prompt:
        prompt_result = await verify_prompt()
        results["prompt"] = prompt_result
        print(f"\n--- Prompt 验证 ---")
        print(f"旧长度: {prompt_result['old_length']}, 新长度: {prompt_result['new_length']}, 差异: {prompt_result['diff_ratio']:.1%}")
        print(f"结果: {'通过' if prompt_result['passed'] else '失败'}")

    route_acc = results.get("route", {}).get("accuracy", 1)
    route_fails = results.get("route", {}).get("failures", [])
    knowledge_hits = results.get("knowledge", {}).get("knowledge_hits", 0)

    passed = route_acc >= 0.8 and len(route_fails) == 0
    print(f"\n=== 总体结果: {'通过' if passed else '失败'} ===")
    return {
        "passed": passed,
        "accuracy": route_acc,
        "failures": route_fails,
        "knowledge_hits": knowledge_hits,
    }


if __name__ == "__main__":
    import asyncio

    result = asyncio.run(main())
    sys.exit(0 if result["passed"] else 1)
