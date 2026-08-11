import time
from dataclasses import dataclass, field
from typing import Optional
import yaml
import os


@dataclass
class FormSlot:
    name: str
    label: str
    ask: str
    required: bool = True
    field_type: str = "text"
    options: list[str] = None


@dataclass
class FormTemplate:
    intent: str
    title: str
    slots: list[FormSlot]
    confirm_template: str
    done_message: str


class FormEngine:
    def __init__(self, config_dir: str = "config/forms"):
        if not os.path.isabs(config_dir):
            # 优先使用当前工作目录（uvicorn 从项目根启动）
            cwd = os.getcwd()
            candidate = os.path.join(cwd, config_dir)
            if os.path.isdir(candidate):
                config_dir = candidate
            else:
                # 回退：从本文件位置推算项目根
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
                config_dir = os.path.join(base_dir, config_dir)
        self.config_dir = config_dir
        self._templates: dict[str, dict] = {}

    def _load_tenant(self, tenant_id: str) -> dict:
        if tenant_id in self._templates:
            return self._templates[tenant_id]
        yaml_path = os.path.join(self.config_dir, f"{tenant_id}.yaml")
        if not os.path.exists(yaml_path):
            self._templates[tenant_id] = {}
            return {}
        with open(yaml_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        parsed = {}
        for intent, cfg in raw.items():
            slots = []
            for s in cfg.get("slots", []):
                slots.append(FormSlot(
                    name=s.get("name", ""),
                    label=s.get("label", ""),
                    ask=s.get("ask", ""),
                    required=s.get("required", True),
                    field_type=s.get("field_type", "text"),
                    options=s.get("options"),
                ))
            parsed[intent] = FormTemplate(
                intent=cfg.get("intent", intent),
                title=cfg.get("title", ""),
                slots=slots,
                confirm_template=cfg.get("confirm_template", ""),
                done_message=cfg.get("done_message", ""),
            )
        self._templates[tenant_id] = parsed
        return parsed

    def get_template(self, intent: str, tenant_id: str) -> Optional[FormTemplate]:
        templates = self._load_tenant(tenant_id)
        return templates.get(intent)

    def get_form_intents(self, tenant_id: str) -> list[str]:
        templates = self._load_tenant(tenant_id)
        return list(templates.keys())

    def _collecting_slot(self, template, index):
        slot = template.slots[index]
        return {
            "type": "form_slot",
            "field": slot.name,
            "label": slot.label,
            "prompt": slot.ask,
        }

    def start(self, intent: str, tenant_id: str, trigger_message: str = "") -> tuple[dict, str]:
        template = self.get_template(intent, tenant_id)
        if not template:
            return None, ""
        state = {
            "intent": intent,
            "current_slot_index": 0,
            "filled": {},
            "status": "collecting",
            "started_at": time.time(),
        }
        # 从触发消息中预填已有答案，跳过不需要再问的槽位
        if trigger_message:
            self._prefill_from_message(state, template, trigger_message)
        idx = state["current_slot_index"]
        if idx < len(template.slots):
            return state, template.slots[idx].ask
        # 所有槽位都已预填，直接进确认
        state["status"] = "confirming"
        return state, ""

    def _prefill_from_message(self, state: dict, template, msg: str):
        """从用户消息中提取匹配的选项，跳过已填槽位"""
        for i, slot in enumerate(template.slots):
            if not slot.required:
                continue  # 选填槽位不预填
            if slot.field_type == "select" and slot.options:
                for opt in slot.options:
                    if opt in msg:
                        state["filled"][slot.name] = opt
                        state["current_slot_index"] = i + 1
                        break

    def process(self, text: str, state: dict, intent: str, tenant_id: str) -> dict:
        template = self.get_template(intent, tenant_id)
        if not template:
            return {"type": "form_slot", "field": "", "label": "", "prompt": "表单模板未找到"}

        slots = template.slots
        index = state["current_slot_index"]

        if state["status"] == "confirming":
            if any(w in text for w in ["修改", "不对", "改一下", "重填"]):
                state["status"] = "collecting"
                state["current_slot_index"] = 0
                state["filled"] = {}
                return self._collecting_slot(template, 0)
            if any(w in text for w in ["确认", "提交", "可以", "没问题", "是的", "确认提交"]):
                state["status"] = "done"
                return {"type": "form_done", "result": template.done_message}
            # 未識別的確認階段回复，再次提示
            return {
                "type": "form_confirm",
                "summary": self._build_confirm_summary(template, state["filled"]),
                "action_label": "确认提交",
            }

        # collecting
        if index < len(slots):
            slot = slots[index]
            state["filled"][slot.name] = text
            state["current_slot_index"] = index + 1

            if state["current_slot_index"] < len(slots):
                return self._collecting_slot(template, state["current_slot_index"])
            else:
                state["status"] = "confirming"
                return {
                    "type": "form_confirm",
                    "summary": self._build_confirm_summary(template, state["filled"]),
                    "action_label": "确认提交",
                }

        return {"type": "form_done", "result": template.done_message}

    def _build_confirm_summary(self, template, filled):
        summary = template.confirm_template
        for slot in template.slots:
            val = filled.get(slot.name, "")
            placeholder = f"{{{slot.name}}}"
            if placeholder in summary:
                summary = summary.replace(placeholder, val)
            note_placeholder = f"{{{slot.name}_{slot.name}}}"
            if note_placeholder in summary:
                if val:
                    summary = summary.replace(note_placeholder, f"📝 {slot.label}：{val}")
                else:
                    summary = summary.replace(note_placeholder, "")
        return summary

    def handle_cancel(self, state: dict) -> dict:
        state["status"] = "cancelled"
        return {"type": "form_slot", "field": "cancelled", "label": "", "prompt": "已取消当前操作，有什么可以帮您的？"}
