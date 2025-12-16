class DSLParseError(Exception):
    """Raised when the DSL script cannot be parsed correctly."""

    def __init__(self, message: str, line_number: int | None = None) -> None:
        suffix = f" (line {line_number})" if line_number is not None else ""
        super().__init__(f"{message}{suffix}")
        self.line_number = line_number

