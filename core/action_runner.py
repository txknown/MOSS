from datetime import datetime

from core import registry


class ActionRunner:
    def __init__(self, memory):
        self.memory = memory
        self.action_log_path = self.memory.logs / "action_log.txt"

    def run(self, action_name, payload=None, log=True):
        payload = payload or {}
        module = registry.load_action_type(action_name)
        result = module.run(self.memory, payload, runner=self)

        if log:
            message = result.get("log")
            if message:
                self.write_log(message)

        return result

    def write_log(self, message):
        self.action_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.action_log_path.open("a", encoding="utf-8") as file:
            file.write(f"{self._timestamp()} — {message}\n")

    def _timestamp(self):
        now = datetime.now().astimezone()
        hour = now.strftime("%I").lstrip("0") or "12"
        return f"{now.strftime('%B')} {now.day}, {now.year}, {hour}:{now.strftime('%M %p')}"
