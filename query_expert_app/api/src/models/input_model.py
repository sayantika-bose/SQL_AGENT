from pydantic import BaseModel

class AskInput(BaseModel):
    question: str