"""
Task type enumerations for log application.
"""
class TaskType:
    """
    Enumeration of task types.
    
    These values should be used instead of hardcoded task names to ensure
    consistency and enable loose coupling between API and worker components.
    """
    
    ASK_QUESTION = "ask_question"