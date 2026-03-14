from celery import current_task
from celery_app import celery_app
from dependencies import get_db_client, get_session_service, get_summarizer_service, get_conversation_service
from service.csv_processor import CSVProcessor
from sqlalchemy import text
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def csv_task(self, csv_content: bytes, filename: str) -> Dict[str, Any]:
    """
    Celery task for CSV ingestion into PostgreSQL.

    Args:
        csv_content: Raw CSV file bytes
        filename: Original filename (for logging)

    Returns:
        Dict with status and rows_inserted count
    """
    try:
        logger.info(f"Starting CSV ingestion task for: {filename}")

        try:
            current_task.update_state(
                state='PROGRESS',
                meta={'status': 'Parsing CSV...', 'progress': 0}
            )
        except Exception as e:
            logger.warning(f"Failed to update task state: {e}")

        processor = CSVProcessor()
        rows = processor.parse(csv_content)

        try:
            current_task.update_state(
                state='PROGRESS',
                meta={'status': f'Inserting {len(rows)} rows...', 'progress': 50}
            )
        except Exception as e:
            logger.warning(f"Failed to update task state: {e}")

        insert_sql = text("""
            INSERT INTO "LlmApp_partysupport"
                (outcome, group_variable, group_label, n, n_flag,
                 pct_lib, pct_con, pct_ndp, pct_bq, pct_grn,
                 pct_other, pct_none, none_label, year, dataset, mode)
            VALUES
                (:outcome, :group_variable, :group_label, :n, :n_flag,
                 :pct_lib, :pct_con, :pct_ndp, :pct_bq, :pct_grn,
                 :pct_other, :pct_none, :none_label, :year, :dataset, :mode)
        """)

        db_client = get_db_client()
        with db_client.transaction() as conn:
            conn.execute(insert_sql, rows)

        try:
            current_task.update_state(
                state='PROGRESS',
                meta={'status': 'Ingestion completed', 'progress': 100}
            )
        except Exception as e:
            logger.warning(f"Failed to update task state: {e}")

        logger.info(f"CSV ingestion task completed for: {filename}, rows inserted: {len(rows)}")
        return {
            'status': 'success',
            'filename': filename,
            'rows_inserted': len(rows),
        }

    except Exception as exc:
        logger.error(f"CSV ingestion task failed for {filename}: {str(exc)}")
        raise


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def cleanup_single_session_task(self, session_id: str, user_id: str, home_country: str, host_country: str, conversation_data: dict = None) -> Dict[str, Any]:
    """
    Celery task for cleaning up a single session and summarizing the conversation.
    """
    try:
        logger.info(f"Starting single session cleanup for session_id: {session_id}, user_id: {user_id}, home_country: {home_country}, host_country: {host_country}")

        session_service = get_session_service()
        summarizer_service = get_summarizer_service()

        import asyncio
        success = asyncio.run(session_service.close_session(session_id))

        if success:
            if conversation_data:
                conversation = conversation_data
                logger.info(f"Using provided conversation data for summarization")
            else:
                conversation_service = get_conversation_service()
                conversation = asyncio.run(conversation_service.get_conversation_history(user_id, home_country, host_country))
                logger.info(f"Retrieved conversation from Redis for summarization")

            import json
            conversation_json = json.dumps(conversation)
            summarization_success = asyncio.run(summarizer_service.add_summary(conversation_json, user_id, session_id))
            logger.info(f"Session {session_id} closed and summarization completed: {summarization_success}")
        else:
            logger.warning(f"Failed to close session {session_id}")

        return {
            'status': 'success',
            'session_id': session_id,
            'user_id': user_id,
            'closed': success,
            'summarization_completed': success and 'summarization_success' in locals() and summarization_success
        }

    except Exception as exc:
        logger.error(f"Single session cleanup failed for session_id: {session_id}: {str(exc)}")
        raise
