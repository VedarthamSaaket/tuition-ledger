import random
from datetime import date

from ..domain.ids import Counter
from ..schema import TABLES
from .profile import Profile


class Dataset:
    def __init__(self, profile: Profile) -> None:
        self.profile = profile
        self.rng = random.Random(profile.seed)
        self.tables: dict[str, list[dict]] = {t.name: [] for t in TABLES}
        self.ground_truth: list[dict] = []
        self.counter = Counter()
        self.idx: dict = {}

    def add(self, table: str, row: dict) -> dict:
        self.tables[table].append(row)
        return row

    def event(self, entity_type: str, entity_id: str, event_type: str, from_state, to_state,
              on: date, actor: str = "system", detail: str | None = None) -> None:
        n = self.counter.next("event")
        self.add("events", {
            "event_id": f"EVT-{n:09d}", "entity_type": entity_type, "entity_id": entity_id,
            "event_type": event_type, "from_state": from_state, "to_state": to_state, "occurred_on": on,
            "actor_role": actor, "detail": detail,
        })

    def decision(self, rule_id: str, entity_type: str, entity_id: str, outcome: str, on: date,
                 explanation: str, amount: int | None = None) -> None:
        n = self.counter.next("decision")
        self.add("decisions", {
            "decision_id": f"DEC-{n:09d}", "rule_id": rule_id, "entity_type": entity_type,
            "entity_id": entity_id, "outcome": outcome, "amount": amount, "decided_on": on,
            "explanation": explanation,
        })
