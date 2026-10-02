"""Violation record shared by the artifact checkers (QA-04)."""


class InvariantViolation:
    def __init__(self, inv_id: str, message: str, artifact: str = ""):
        self.inv_id = inv_id
        self.message = message
        self.artifact = artifact

    def __str__(self):
        art = f" [{self.artifact}]" if self.artifact else ""
        return f"{self.inv_id}{art}: {self.message}"

    def __repr__(self):
        return str(self)
