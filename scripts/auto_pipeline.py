import argparse
import logging
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import auto_execute
import auto_verify
import rollback as rollback_mod


def _setup_log(timestamp: str) -> str:
    log_dir = os.path.join(auto_execute.BASE_DIR, timestamp)
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "pipeline.log")

    logger = logging.getLogger("pipeline")
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(fh)
    logger.addHandler(logging.StreamHandler())
    return log_path


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    _setup_log(ts)
    log = logging.getLogger("pipeline")

    items = auto_execute._scan()
    if not items:
        log.info("no proposals to process")
        return {"passed": True, "processed": 0}

    log.info("pipeline start (dry-run=%s)", args.dry_run)
    log.info("found %d proposal(s) to process", len(items))

    passed_total = 0
    failed_total = 0

    for entry_id, proposal in items:
        action = proposal.get("action", "")
        content = proposal.get("content", "")
        log.info("[%s] processing: action=%s", entry_id, action)

        if args.dry_run:
            log.info("[%s] dry-run: would execute %s", entry_id, action)
            continue

        try:
            if action == "add_faq":
                path = auto_execute._execute_add_faq(content)
            elif action == "update_rules":
                path = auto_execute._execute_update_rules(entry_id, content)
            elif action == "optimize_prompt":
                path = auto_execute._execute_optimize_prompt(content)
            else:
                log.warning("[%s] unknown action: %s", entry_id, action)
                continue
            auto_execute._set_status(entry_id, "executed")
            log.info("[%s] executed -> %s", entry_id, path)
        except Exception as e:
            log.error("[%s] execution failed: %s", entry_id, e)
            failed_total += 1
            continue

        try:
            route_result = await auto_verify.verify_route()
            knowledge_result = await auto_verify.verify_knowledge()
            prompt_result = await auto_verify.verify_prompt()

            route_ok = route_result["accuracy"] >= 0.8 and len(route_result["failures"]) == 0
            knowledge_ok = knowledge_result["knowledge_hits"] > 0
            prompt_ok = prompt_result["passed"]

            log.info(
                "[%s] verify: route=%.1f%%(%s) knowledge=%d/%d(%s) prompt=%s",
                entry_id,
                route_result["accuracy"] * 100,
                "pass" if route_ok else "fail",
                knowledge_result["knowledge_hits"],
                knowledge_result["total_queries"],
                "pass" if knowledge_ok else "fail",
                "pass" if prompt_ok else "fail",
            )

            if route_ok and knowledge_ok and prompt_ok:
                auto_execute._set_status(entry_id, "verified")
                log.info("[%s] verified", entry_id)
                passed_total += 1
            else:
                rollback_mod._rollback(entry_id)
                auto_execute._set_status(entry_id, "verification_failed")
                log.info("[%s] verification failed, rolled back", entry_id)
                failed_total += 1
        except Exception as e:
            log.error("[%s] verification error: %s", entry_id, e)
            failed_total += 1

    log.info("pipeline done: %d passed, %d failed", passed_total, failed_total)
    return {
        "passed": failed_total == 0,
        "processed": len(items),
        "passed_count": passed_total,
        "failed_count": failed_total,
    }


if __name__ == "__main__":
    import asyncio

    result = asyncio.run(main())
    sys.exit(0 if result["passed"] else 1)
