from infra.logger import logger
from celery_app import celery_app


class SessionService:
    def __init__(self):
        from dependencies import get_db_client
        self.sql_client = get_db_client()

    async def get_or_create_session_sql(self, user_id: str) -> str:
        """
        Creates a new session in the database.

        Args:
            user_id: User ID

        Returns:
            str: Result of the create
        """
        try:

            select_sql = """
            SELECT id
            FROM "LlmApp_session"
            WHERE user_id = :user_id AND status = 'active'
            ORDER BY last_activity_at DESC
            LIMIT 1
            """
            row = await self.sql_client.async_execute_scalar(
                select_sql,
                {
                    "user_id": user_id
                }
            )
            if row:
                return str(row)


            insert_sql = """
            INSERT INTO "LlmApp_session"(user_id)
            VALUES (:user_id)
            RETURNING id
            """
            result = await self.sql_client.async_execute_scalar(
                insert_sql,
                {
                    "user_id": user_id
                }
            )
            if result:
                session_id = str(result)
                logger.info(f"Created new session {session_id} for user {user_id}")
                return session_id
            logger.warning(f"Failed to create session for user {user_id} - no result returned")
            return ""
        except Exception as e:
            logger.error(f"Error creating session for user_id {user_id}: {e}")
            return ""

    async def heartbeat(self, session_id: str) -> str:
        """
        Updates the session in the database.

        Args:
            session_id: Session ID

        Returns:
            str: Result of the update
        """
        try:
            update_sql = """
            UPDATE "LlmApp_session"
            SET last_activity_at = NOW()
            WHERE id = :session_id
            """
            result = await self.sql_client.async_execute_command(
                update_sql,
                {
                    "session_id": session_id
                }
            )
            return result
        except Exception as e:
            logger.error(f"Error updating session for session_id {session_id}: {e}")
            return ""


    async def add_message_pair_sql(self, user_id: str, home_country: str, host_country: str, user_message: str, assistant_response: str) -> str:
        """
        Add a user message and assistant response pair to long-term conversation history

        Args:
            user_id: str
            home_country: str
            host_country: str
            user_message: str
            assistant_response: str

        Returns:
            str: Message ID of the inserted record
        """
        try:
            # Use async wrapper to avoid blocking the event loop
            insert_sql = """
            INSERT INTO "LlmApp_messagelog" (user_id, home_country, host_country, message, response) 
            VALUES (:user_id, :home_country, :host_country, :message, :response)
            RETURNING id
            """
            result = await self.sql_client.async_execute_scalar(
                insert_sql,
                {
                    "user_id": user_id,
                    "home_country": home_country,
                    "host_country": host_country,
                    "message": user_message,
                    "response": assistant_response
                }
            )
            
            if result:
                return str(result)
            return ""
        except Exception as e:
            logger.error(f"Error adding message pair for user {user_id}: {e}")
            return ""

    async def add_message_with_session_and_link_sql(self, user_id: str, home_country: str, host_country: str, user_message: str, assistant_response: str) -> tuple[str, str]:
        """
        Add a message pair, get/create session, and create MessageLogLink all in a single transaction

        Args:
            user_id: str
            home_country: str
            host_country: str
            user_message: str
            assistant_response: str

        Returns:
            tuple[str, str]: (session_id, message_id)
        """
        try:
            import anyio
            from sqlalchemy import text
            
            def _execute_in_transaction():
                with self.sql_client.engine.connect() as conn:
                    with conn.begin():
                        # 1. Get or create session
                        select_sql = """
                        SELECT id
                        FROM "LlmApp_session"
                        WHERE user_id = :user_id AND status = 'active'
                        ORDER BY last_activity_at DESC
                        LIMIT 1
                        """
                        session_id = conn.execute(text(select_sql), {"user_id": user_id}).scalar()
                        
                        if not session_id:
                            # Create new session
                            insert_session_sql = """
                            INSERT INTO "LlmApp_session"(user_id)
                            VALUES (:user_id)
                            RETURNING id
                            """
                            session_id = conn.execute(text(insert_session_sql), {"user_id": user_id}).scalar()
                            logger.info(f"Created new session {session_id} for user {user_id}")
                        
                        # 2. Insert message
                        insert_message_sql = """
                        INSERT INTO "LlmApp_messagelog" (user_id, home_country, host_country, message, response) 
                        VALUES (:user_id, :home_country, :host_country, :message, :response)
                        RETURNING id
                        """
                        message_id = conn.execute(text(insert_message_sql), {
                            "user_id": user_id,
                            "home_country": home_country,
                            "host_country": host_country,
                            "message": user_message,
                            "response": assistant_response
                        }).scalar()
                        
                        if message_id and session_id:
                            # 3. Create MessageLogLink in the same transaction
                            link_sql = """
                            INSERT INTO "LlmApp_messagelog_link"(message_id, session_id)
                            VALUES (:message_id, :session_id)
                            ON CONFLICT (message_id) DO NOTHING
                            """
                            conn.execute(text(link_sql), {
                                "message_id": str(message_id),
                                "session_id": str(session_id)
                            })
                            logger.info(f"Created message {message_id} and linked to session {session_id}")
                            return (str(session_id), str(message_id))
                        return ("", "")
            
            # Run in thread pool to avoid blocking
            result = await anyio.to_thread.run_sync(_execute_in_transaction)
            return result
            
        except Exception as e:
            logger.error(f"Error adding message with session and link for user {user_id}: {e}")
            return ("", "")

    async def add_message_and_link_sql(self, user_id: str, home_country: str, host_country: str, user_message: str, assistant_response: str, session_id: str) -> str:
        """
        Add a message pair and create MessageLogLink in a single transaction to avoid isolation issues

        Args:
            user_id: str
            home_country: str
            host_country: str
            user_message: str
            assistant_response: str
            session_id: str

        Returns:
            str: Message ID of the inserted record
        """
        try:
            # Use a single transaction to avoid isolation issues
            import anyio
            from sqlalchemy import text
            
            def _execute_in_transaction():
                with self.sql_client.engine.connect() as conn:
                    with conn.begin():
                        # 1. First verify the session exists (it should since we just created it)
                        verify_sql = """
                        SELECT id FROM "LlmApp_session" WHERE id = :session_id
                        """
                        session_exists = conn.execute(text(verify_sql), {"session_id": session_id}).scalar()
                        
                        if not session_exists:
                            logger.error(f"Session {session_id} does not exist in database - cannot create MessageLogLink")
                            return ""
                        
                        # 2. Insert message
                        insert_sql = """
                        INSERT INTO "LlmApp_messagelog" (user_id, home_country, host_country, message, response) 
                        VALUES (:user_id, :home_country, :host_country, :message, :response)
                        RETURNING id
                        """
                        result = conn.execute(text(insert_sql), {
                            "user_id": user_id,
                            "home_country": home_country,
                            "host_country": host_country,
                            "message": user_message,
                            "response": assistant_response
                        })
                        message_id = result.scalar()
                        
                        if message_id:
                            # 3. Create MessageLogLink in the same transaction
                            link_sql = """
                            INSERT INTO "LlmApp_messagelog_link"(message_id, session_id)
                            VALUES (:message_id, :session_id)
                            ON CONFLICT (message_id) DO NOTHING
                            """
                            conn.execute(text(link_sql), {
                                "message_id": str(message_id),
                                "session_id": session_id
                            })
                            logger.info(f"Created message {message_id} and linked to session {session_id}")
                            return str(message_id)
                        return ""
            
            # Run in thread pool to avoid blocking
            result = await anyio.to_thread.run_sync(_execute_in_transaction)
            return result
            
        except Exception as e:
            logger.error(f"Error adding message and link for user {user_id}: {e}")
            return ""

    async def insert_link_sql(self, session_id: str, message_id: str) -> str:
        """
        Inserts a link into the database.

        Args:
            session_id: Session ID
            message_id: Message ID

        Returns:
            str: Result of the insert
        """
        try:
            insert_sql = """
            INSERT INTO "LlmApp_messagelog_link"(message_id, session_id)
            VALUES (:message_id, :session_id)
            ON CONFLICT (message_id) DO NOTHING
            """
            result = await self.sql_client.async_execute_command(
                insert_sql,
                {
                    "message_id": message_id, 
                    "session_id": session_id
                }
            )
            logger.info(f"Created MessageLogLink: message_id={message_id}, session_id={session_id}")
            return result
        except Exception as e:
            logger.error(f"Error inserting link for session_id {session_id}: {e}")
            return ""

    async def close_session(self, session_id: str) -> bool:
        """
        Close a session and mark it as inactive
        
        Args:
            session_id: Session ID to close
            
        Returns:
            bool: True if session was successfully closed, False otherwise
        """
        try:
            update_sql = """
            UPDATE "LlmApp_session"
            SET status = 'closed'
            WHERE id = :session_id AND status = 'active'
            """
            result = await self.sql_client.async_execute_command(
                update_sql,
                {
                    "session_id": session_id
                }
            )
            
            if result > 0:
                logger.info(f"Closed session {session_id}")
                return True
            else:
                logger.warning(f"Session {session_id} was already closed or not found")
                return False
                
        except Exception as e:
            logger.error(f"Error closing session {session_id}: {e}")
            return False

    def reset_session_cleanup_timer(self, session_id: str, user_id: str, home_country: str, host_country: str) -> None:
        """
        Reset the cleanup timer for a session
        
        Args:
            session_id: Session ID
            user_id: User ID
            home_country: Home country
            host_country: Host country
        """
        try:
            # Cancel any existing cleanup task for this session
            self.cancel_existing_cleanup(session_id)
            
            # Schedule new cleanup (4 hours from now)
            from tasks.background_tasks import cleanup_single_session_task
            cleanup_single_session_task.apply_async(
                args=[session_id, user_id, home_country, host_country],
                countdown=4 * 60 * 60,  # 4 hours in seconds
                task_id=f"cleanup_{session_id}"  # Unique task ID
            )
            
            logger.info(f"Reset cleanup timer for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error resetting cleanup timer for session {session_id}: {e}")

    def cancel_existing_cleanup(self, session_id: str) -> None:
        """
        Cancel any existing cleanup task for this session
        
        Args:
            session_id: Session ID
        """
        try:
            task_id = f"cleanup_{session_id}"
            celery_app.control.revoke(task_id, terminate=True)
            logger.info(f"Cancelled existing cleanup task for session {session_id}")
        except Exception as e:
            logger.warning(f"Error cancelling cleanup task for session {session_id}: {e}")
