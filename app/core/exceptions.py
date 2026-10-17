class PlanGenerationError(Exception):
    """
    Raised when all LLM providers in the failover chain fail to produce
    a schema-compliant workout plan.
    """

    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
