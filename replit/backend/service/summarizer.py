from openai import AsyncOpenAI
from config.config import get_settings

from infra.logger import logger

class SummarizerService:
    def __init__(self):
        from dependencies import get_db_client
        self.sql_client = get_db_client()
        settings = get_settings()
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def _summarize_from_json(self, json_data: str) -> str:
        """
        Summarizes the given JSON data.

        Args:
            json_data: JSON data
        Returns:
            str: Summarized string
        """

        try:
            messages = [
                {"role": "system", "content": "You are a helpful assistant that summarizes user's chat data as a context for a chatbot. Create a concise summary of the conversation."},
                {"role": "user", "content": json_data}
            ]
            logger.info(f"Summarizing json_data {json_data}")
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.2,
                max_tokens=350,
                stream=False
            )
            logger.info(f"Summarized data into: {response.choices[0].message.content}")
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error summarizing json_data {json_data}: {e}")
            return None

    # async def _get_summary_sql(self, user_id: str) -> str:
    #     """
    #     Retrieves the summary from the database.

    #     Args:
    #         user_id: User ID
    #     """
    #     try:
    #         select_sql = """
    #         SELECT summary_text, last_session_id, updated_at
    #         FROM "LlmApp_summary"
    #         WHERE user_id = :user_id    
    #         """
    #         result = await self.sql_client.async_execute_one(
    #             select_sql,
    #             {
    #                 "user_id": user_id
    #             }
    #         )
    #         return result
    #     except Exception as e:
    #         logger.error(f"Error retrieving summary for user_id {user_id}: {e}")
    #         return ""

    async def _add_summary_sql(self, summary_text: str, user_id: str, session_id: str) -> bool:
        """
        Sends the summary to the database.

        Args:
            summary_text: Summary text
            user_id: User ID
            session_id: Session ID

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            insert_sql = """
            INSERT INTO "LlmApp_summary"(user_id, summary_text, last_session_id)
            VALUES (:user_id, :summary_text, :last_session_id)
            ON CONFLICT (user_id) DO UPDATE
            SET summary_text = EXCLUDED.summary_text,
                last_session_id = EXCLUDED.last_session_id
            """
            await self.sql_client.async_execute_command(
                insert_sql,
                {
                    "summary_text": summary_text,
                    "last_session_id": session_id,
                    "user_id": user_id
                }
            )
            
            return True
        except Exception as e:
            logger.error(f"Error adding summary for user_id {user_id}: {e}")
            return False

    async def add_summary(self, json_data: str, user_id: str, session_id: str) -> bool:
        """
        Adds the summary to the database.

        Args:
            json_data: JSON data
            user_id: User ID
            session_id: Session ID

        Returns:
            bool: True if successful, False otherwise
        """

        try:
            logger.info(f"Summarizing for user_id: {user_id} and session_id: {session_id}")
            summary_text = await self._summarize_from_json(json_data)

            logger.info(f"Adding summary for user_id: {user_id} and session_id: {session_id}")
            result = await self._add_summary_sql(summary_text, user_id, session_id)

            logger.info(f"Summary added to database for user_id: {user_id} and session_id: {session_id}")
            return result
        except Exception as e:
            logger.error(f"Error adding summary for user_id: {user_id} and session_id: {session_id}: {e}")
            return False
