import argparse
import json
import os
import shutil

BASE_DIR = "data/auto_patches"


def _list():
    if not os.path.isdir(BASE_DIR):
        print("no rollbacks available")
        return
    found = False
    for entry in sorted(os.listdir(BASE_DIR), reverse=True):
        originals_dir = os.path.join(BASE_DIR, entry, "originals")
        manifest_path = os.path.join(originals_dir, "manifest.json")
        if not os.path.isfile(manifest_path):
            continue
        with open(manifest_path, encoding="utf-8") as f:
            targets = json.load(f)
        status_path = os.path.join(BASE_DIR, entry, "status.json")
        status = "unknown"
        if os.path.isfile(status_path):
            with open(status_path, encoding="utf-8") as f:
                status = json.load(f).get("status", "unknown")
        print(f"{entry} [{status}] {', '.join(targets)}")
        found = True
    if not found:
        print("no rollbacks available")


def _rollback(entry_id: str):
    originals_dir = os.path.join(BASE_DIR, entry_id, "originals")
    manifest_path = os.path.join(originals_dir, "manifest.json")
    if not os.path.isfile(manifest_path):
        print(f"no backups found for {entry_id}")
        return
    with open(manifest_path, encoding="utf-8") as f:
        targets = json.load(f)
    for target_path in targets:
        safe_name = target_path.replace("/", "_").replace("\\", "_")
        backup_file = os.path.join(originals_dir, safe_name)
        if os.path.isfile(backup_file):
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            shutil.copy2(backup_file, target_path)
            print(f"restored {target_path}")
    status_path = os.path.join(BASE_DIR, entry_id, "status.json")
    if os.path.isfile(status_path):
        with open(status_path, encoding="utf-8") as f:
            data = json.load(f)
        data["status"] = "rolled_back"
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Rollback auto-patches")
    parser.add_argument("command", choices=["list", "rollback"])
    parser.add_argument("id", nargs="?", help="proposal id to rollback")
    args = parser.parse_args()
    if args.command == "list":
        _list()
    elif args.command == "rollback":
        if not args.id:
            print("usage: rollback.py rollback <id>")
            return
        _rollback(args.id)


if __name__ == "__main__":
    main()
