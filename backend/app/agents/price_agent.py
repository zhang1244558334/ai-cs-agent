import yaml

from .base_agent import BaseAgent


class PriceAgent(BaseAgent):
    def __init__(self, llm_client=None, bargain_config="config/bargain.yaml"):
        super().__init__(llm_client)
        with open(bargain_config) as f:
            self.params = yaml.safe_load(f)

    def _calc_temperature(self, bargain_count: int) -> float:
        return min(
            self.params["temperature_start"]
            + bargain_count * self.params["temperature_step"],
            self.params["temperature_max"],
        )

    def _build_messages(
        self, user_msg: str, context: list, extra_context: dict
    ) -> list:
        bc = extra_context.get("bargain_count", 0)
        temp = self._calc_temperature(bc)
        system = {
            "role": "system",
            "content": (
                f"你是电商议价助手。当前温度{temp:.2f}，最大让步比例"
                f"{self.params['max_discount_ratio']*100:.0f}%，最多"
                f"{self.params['max_rounds']}轮。根据温度决定让步幅度，温度越高越灵活。"
            ),
        }
        return [system] + context + [{"role": "user", "content": user_msg}]
