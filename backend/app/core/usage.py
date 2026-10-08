from datetime import date
from .errors import AppError


class UsageCounter:
    def __init__(self, cap: int):
        self.cap, self.day, self.count = cap, date.today(), 0

    def hit(self) -> None:
        today = date.today()
        if today != self.day:
            self.day, self.count = today, 0
        if self.count >= self.cap:
            raise AppError(
                "daily_cap",
                "Daily AI limit reached. Try again tomorrow or raise DAILY_AI_CALL_CAP in .env.",
                429,
            )
        self.count += 1
