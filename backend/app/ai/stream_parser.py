import json


class JsonObjectStreamParser:
    """Incrementally extracts top-level JSON objects from noisy model output."""

    def __init__(self) -> None:
        self.buffer = ""
        self.cursor = 0
        self.depth = 0
        self.start: int | None = None
        self.in_string = False
        self.escape = False
        self.in_think = False

    def feed(self, chunk: str) -> list[dict]:
        self.buffer += chunk
        found: list[dict] = []
        consumed = 0
        index = self.cursor
        while index < len(self.buffer):
            remainder = self.buffer[index:]
            if remainder.startswith("<") and any(
                tag.startswith(remainder) for tag in ("<think>", "</think>")
            ):
                break
            if self.buffer.startswith("<think>", index):
                self.in_think = True
                index += 7
                continue
            if self.buffer.startswith("</think>", index):
                self.in_think = False
                index += 8
                continue
            if self.in_think:
                index += 1
                continue
            char = self.buffer[index]
            if self.start is None:
                if char == "{":
                    self.start = index
                    self.depth = 1
                    self.in_string = False
                    self.escape = False
            elif self.in_string:
                if self.escape:
                    self.escape = False
                elif char == "\\":
                    self.escape = True
                elif char == '"':
                    self.in_string = False
            elif char == '"':
                self.in_string = True
            elif char == "{":
                self.depth += 1
            elif char == "}":
                self.depth -= 1
                if self.depth == 0:
                    try:
                        value = json.loads(self.buffer[self.start : index + 1])
                        if isinstance(value, dict):
                            found.append(value)
                    except json.JSONDecodeError:
                        pass
                    consumed = index + 1
                    self.start = None
            index += 1
        self.cursor = index
        if consumed:
            self.buffer = self.buffer[consumed:]
            self.cursor -= consumed
            if self.start is not None:
                self.start -= consumed
        elif self.start is None and len(self.buffer) > 4096:
            self.buffer = self.buffer[-1024:]
            self.cursor = len(self.buffer)
        return found
