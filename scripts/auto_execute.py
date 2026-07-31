import json
import os
import shutil
from datetime import datetime

import yaml

BASE_DIR = "data/auto_patches"
DOCS_DIR = "docs"
PROMPTS_DIR = "prompts"
CONFIG_FILE = "config/router_rules.yaml"


def _scan() -> list[tuple[str, dict]]:
    if not os.path.isdir(BASE_DIR):
        return []
    results = []
    for entry in sorted(os.listdir(BASE_DIR)):
        proposal_path = os.path.join(BASE_DIR, entry, "proposal.json")
        status_path = os.path.join(BASE_DIR, entry, "status.json")
        if not os.path.isfile(proposal_path):
            continue
        with open(proposal_path, encoding="utf-8") as f:
            proposal = json.load(f)
        status = "pending"
        if os.path.isfile(status_path):
            with open(status_path, encoding="utf-8") as f:
                status = json.load(f).get("status", "pending")
        approved = status == "approved"
        auto_approve = proposal.get("level") == "L1" and status == "pending"
        if approved or auto_approve:
            results.append((entry, proposal))
    return results


def _backup(entry_id: str, target_path: str):
    originals_dir = os.path.join(BASE_DIR, entry_id, "originals")
    os.makedirs(originals_dir, exist_ok=True)
    if os.path.isfile(target_path):
        safe_name = target_path.replace("/", "_").replace("\\", "_")
        shutil.copy2(target_path, os.path.join(originals_dir, safe_name))
    manifest_path = os.path.join(originals_dir, "manifest.json")
    existing = []
    if os.path.isfile(manifest_path):
        with open(manifest_path, encoding="utf-8") as f:
            existing = json.load(f)
    if target_path not in existing:
        existing.append(target_path)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)


def _set_status(entry_id: str, status: str):
    path = os.path.join(BASE_DIR, entry_id, "status.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"status": status}, f, indent=2)


def _execute_add_faq(content: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(DOCS_DIR, f"{ts}.md")
    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def _execute_update_rules(entry_id: str, content: str) -> str:
    _backup(entry_id, CONFIG_FILE)
    new_rules = yaml.safe_load(content) or {}
    with open(CONFIG_FILE, encoding="utf-8") as f:
        existing = yaml.safe_load(f) or {}
    existing_intents = existing.get("intents", {})
    new_intents = new_rules.get("intents", {}) if isinstance(new_rules, dict) else {}
    for k, v in new_intents.items():
        if k in existing_intents:
            for field in ("keywords", "patterns"):
                if field in v and field in existing_intents[k]:
                    existing_set = set(existing_intents[k][field])
                    v[field] = list(existing_set | set(v[field]))
        existing_intents[k] = v
    existing["intents"] = existing_intents
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(existing, f, allow_unicode=True, default_flow_style=False)
    return CONFIG_FILE


def _execute_optimize_prompt(content: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(PROMPTS_DIR, f"{ts}.txt")
    os.makedirs(PROMPTS_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def main():
    items = _scan()
    if not items:
        print("no proposals to execute")
        return
    for entry_id, proposal in items:
        action = proposal.get("action", "")
        content = proposal.get("content", "")
        if action == "add_faq":
            path = _execute_add_faq(content)
        elif action == "update_rules":
            path = _execute_update_rules(entry_id, content)
        elif action == "optimize_prompt":
            path = _execute_optimize_prompt(content)
        else:
            print(f"[{entry_id}] unknown action: {action}")
            continue
        _set_status(entry_id, "executed")
        print(f"[{entry_id}] {action} -> {path}")
        print(f"[notification] 自动执行完成: {action} on {path}")


if __name__ == "__main__":
    main()
