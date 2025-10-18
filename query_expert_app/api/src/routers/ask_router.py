"""
Router for ask-related endpoints with logging and error handling.
"""
import logging
from fastapi import APIRouter, HTTPException
from typing import Optional

from api.src.services.task_service import send_task_to_celery
from api.src.models.input_model import AskInput
from api.src.models.schemas import TaskResponse
from common.enum.task_enum import TaskType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

router = APIRouter(tags=["ask"])

@router.post("/ask", response_model=TaskResponse)
def ask_question(request: AskInput):
    """
    Submit a question to be answered by the LLM.

    This endpoint sends a task to the Celery worker through Redis.
    """
    logger.info("Received /ask request: %s", request.dict())

    try:
        # Prepare the task data
        question_data = {
            "question": request.question
        }
        logger.debug("Prepared question data: %s", question_data)

        # Send the task to Celery
        logger.info("Sending task to Celery...")
        task_id = send_task_to_celery(
            TaskType.ASK_QUESTION,
            kwargs={"question_data": question_data}
        )

        if not task_id:
            logger.error("Celery did not return a valid task ID.")
            raise HTTPException(status_code=500, detail="Failed to create task.")

        logger.info("Task successfully sent to Celery with ID: %s", task_id)
        return TaskResponse(task_id=task_id)

    except HTTPException as http_err:
        # Already an HTTPException — just log and re-raise
        logger.error("HTTPException while processing /ask request: %s", str(http_err))
        raise http_err

    except Exception as e:
        # Unexpected error
        logger.exception("Unexpected error while processing /ask request: %s", str(e))
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred while submitting the question: {str(e)}"
        )
