import redis.asyncio as redis
import json
from typing import List, Dict
from config.config import get_settings
from infra.logger import logger

class ConversationService:
    def __init__(self):
        """
        Initialize Redis connection for conversation storage
        """
        self.settings = get_settings()
        self.redis_client = redis.Redis(
            host=self.settings.REDIS_HOST,
            port=self.settings.REDIS_PORT,
            db=self.settings.REDIS_DB,
            password=self.settings.REDIS_PASSWORD,
            decode_responses=True
        )
        self.max_turns = self.settings.MAX_TURNS
        
    def _get_conversation_key(self, user_id: str, home_country: str, host_country: str) -> str:
        """
        Generate Redis key for user conversation

        Args:
        user_id: str
        home_country: str
        host_country: str

        Returns:
            str: Redis key for user conversation
        """
        return f"conversation:{user_id}:{home_country}:{host_country}"
    
    def _get_turn_count_key(self, user_id: str, home_country: str, host_country: str) -> str:
        """
        Generate Redis key for turn counter

        Args:
            user_id: str
            home_country: str
            host_country: str

        Returns:
            str: Redis key for turn counter
        """
        return f"turns:{user_id}:{home_country}:{host_country}"
    
    async def get_conversation_history(self, user_id: str, home_country: str, host_country: str) -> List[Dict[str, str]]:
        """
        Retrieve conversation history for a user

        Args:
            user_id: str
            home_country: str
            host_country: str

        Returns:
            List of conversation messages in format: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        """
        try:
            conversation_key = self._get_conversation_key(user_id, home_country, host_country)
            conversation_data = await self.redis_client.get(conversation_key)
            
            if conversation_data:
                conversation = json.loads(conversation_data)
                logger.info(f"Retrieved {len(conversation)} messages for user {user_id}")
                return conversation
            else:
                logger.info(f"No conversation history found for user {user_id}")
                return []
                
        except Exception as e:
            logger.error(f"Error retrieving conversation history for user {user_id}: {e}")
            return []
        
    async def add_message_pair(self, user_id: str, home_country: str, host_country: str, user_message: str, assistant_response: str) -> int:
        """
        Add a user message and assistant response pair to conversation history

        Args:
            user_id: str
            home_country: str
            host_country: str
            user_message: str
            assistant_response: str
        
        Returns:
            Current turn count after adding the message
        """
        try:
            conversation_key = self._get_conversation_key(user_id, home_country, host_country)
            turn_count_key = self._get_turn_count_key(user_id, home_country, host_country)
            
            # Get current conversation history
            conversation = await self.get_conversation_history(user_id, home_country, host_country)
            
            # Add new message pair
            conversation.extend([
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_response}
            ])
            
            # Increment turn count
            current_turns = await self.redis_client.incr(turn_count_key)
            
            # Set expiration for turn counter (24 hours)
            await self.redis_client.expire(turn_count_key, 86400)
            
            # Check if we've reached max turns
            if current_turns >= self.max_turns:
                logger.info(f"User {user_id} reached max turns ({self.max_turns}). Flushing conversation.")
                
                # Get conversation data BEFORE flushing Redis
                conversation_data = await self.get_conversation_history(user_id, home_country, host_country)
                
                # Do essential SQL operations before flushing (message logging and MessageLogLink)
                # Skip timer reset to avoid cancelling immediate cleanup task
                from dependencies import get_session_service
                session_service = get_session_service()
                
                # Get session_id first to avoid duplicate calls
                session_id = await session_service.get_or_create_session_sql(user_id)
                
                import asyncio
                asyncio.create_task(self._background_sql_operations(
                    user_id, home_country, host_country, user_message, assistant_response, skip_timer_reset=True, session_id=session_id
                ))
                
                # Flush conversation from Redis
                await self.flush_conversation(user_id, home_country, host_country)
                
                # Trigger cleanup and summarization with conversation data
                if session_id:
                    from tasks.background_tasks import cleanup_single_session_task
                    # Pass conversation data to avoid race condition
                    cleanup_single_session_task.delay(session_id, user_id, home_country, host_country, conversation_data)
                    logger.info(f"Triggered cleanup and summarization for user {user_id} after reaching max turns")
                
                return self.max_turns
            else:
                # Save updated conversation
                await self.redis_client.setex(
                    conversation_key,
                    86400,  # 24 hour expiration
                    json.dumps(conversation)
                )
                
                # Fire-and-forget background SQL operations (non-blocking)
                import asyncio
                asyncio.create_task(self._background_sql_operations(
                    user_id, home_country, host_country, user_message, assistant_response
                ))
                
                logger.info(f"Added message pair for user {user_id}. Turn count: {current_turns}/{self.max_turns}")
                return current_turns
                
        except Exception as e:
            logger.error(f"Error adding message pair for user {user_id}: {e}")
            return 0
    
    async def get_turn_count(self, user_id: str, home_country: str, host_country: str) -> int:
        """
        Get current turn count for a user

        Args:
            user_id: str
            home_country: str
            host_country: str

        Returns:
            int: Current turn count
        """
        try:
            turn_count_key = self._get_turn_count_key(user_id, home_country, host_country)
            count = await self.redis_client.get(turn_count_key)
            return int(count) if count else 0
        except Exception as e:
            logger.error(f"Error getting turn count for user {user_id}: {e}")
            return 0
    
    async def flush_conversation(self, user_id: str, home_country: str, host_country: str) -> bool:
        """
        Flush (delete) conversation history and reset turn counter for a user
        
        Args:
            user_id: str
            home_country: str
            host_country: str

        Returns:
            True if successful, False otherwise
        """
        try:
            conversation_key = self._get_conversation_key(user_id, home_country, host_country)
            turn_count_key = self._get_turn_count_key(user_id, home_country, host_country)
            
            # Delete conversation and turn counter
            deleted_count = await self.redis_client.delete(conversation_key, turn_count_key)
            
            logger.info(f"Flushed conversation for user {user_id}. Deleted {deleted_count} keys.")
            return deleted_count > 0
            
        except Exception as e:
            logger.error(f"Error flushing conversation for user {user_id}: {e}")
            return False
    
    async def should_end_conversation(self, user_id: str, home_country: str, host_country: str) -> bool:
        """
        Check if conversation should end (reached max turns)
        
        Args:
            user_id: str
            home_country: str
            host_country: str

        Returns:
            bool: True if conversation should end, False otherwise
        """
        return await self.get_turn_count(user_id, home_country, host_country) >= self.max_turns
    
    async def format_conversation_for_llm(self, user_id: str, home_country: str, host_country: str, current_query: str) -> List[Dict[str, str]]:
        """
        Format conversation history for LLM, including current query

        Args:
            user_id: str
            home_country: str
            host_country: str
            current_query: str

        Returns:
            Formatted messages list for LLM API
        """
        # Get conversation history
        history = await self.get_conversation_history(user_id, home_country, host_country)
        
        # Add system prompt
        system_prompt = f"""You are an AI chatbot that helps immigrants make their minds up about political parties in their current country. The context is party platforms for the parties in question. Please be helpful. Be as accurate as possible. Do not include any persuasive arguments for the other side. Your goal is not to convince people of one side or the other. Your goal is to help people make up their minds. Return the information in an accessible reading level (high school). Always end in complete sentences. Use details from conversation history to seem more personable. This chat is for people on the go. Be terse but helpful (2-3 sentences MAX). Pay attention to the query. Always begin by drawing a clear contrast between the parties in question (e.g., The X, Y, and Z parties [specific difference, avoid mealymouthed responses]). Pretend you are a neutral expert having a natural conversation. Your goal is to translate party systems from one country to another. Do your best to provide a guess of how parties in two countries relate. Being too vague will harm the participation of immigrants. Be concrete and take creative liberties in drawing comparisons. Mention multiple parties when necessary and disclose whether they have recently been in the governing coalition. Provide a balanced take and make sure to mention all of the relevant parties. Do not leave parties out. If the user starts talking in a foreign language, follow their lead. Ask follow-up questions to help the participant determine which party in the host country they are closest to. Take it step by step.

Background: the immigrant is from {home_country} and is now living in {host_country}."""

        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        messages.extend(history)
        
        # Add current query
        messages.append({"role": "user", "content": current_query})
        
        return messages

    async def hydrate_redis(self, user_id: str, home_country: str, host_country: str) -> bool:
        """
        Hydrate Redis with conversation context from summary table
        
        Args:
            user_id: User ID
            home_country: User's home country
            host_country: User's host country
            
        Returns:
            bool: True if context was hydrated, False otherwise
        """
        try:
            # Get summary from database
            from dependencies import get_db_client
            sql_client = get_db_client()
            
            summary_sql = """
            SELECT summary_text, last_session_id, updated_at
            FROM "LlmApp_summary"
            WHERE user_id = :user_id
            """
            
            summary_result = await sql_client.async_execute_one(summary_sql, {"user_id": user_id})

            if not summary_result:
                logger.info(f"No summary found for user {user_id}")
                return False

            # Convert Row object to mapping for dictionary-style access
            summary_data = summary_result._mapping if hasattr(summary_result, '_mapping') else dict(summary_result)

            # Create conversation context from summary
            # Store as assistant message to avoid conflicts with system prompts
            conversation_context = [
                {
                    "role": "assistant",
                    "content": f"[Context from previous conversation: {summary_data['summary_text']}]"
                }
            ]
            
            # Store in Redis
            conversation_key = self._get_conversation_key(user_id, home_country, host_country)
            await self.redis_client.setex(
                conversation_key,
                86400,  # 24 hour expiration
                json.dumps(conversation_context)
            )
            
            # Set turn count to 0 (new conversation with context)
            turn_count_key = self._get_turn_count_key(user_id, home_country, host_country)
            await self.redis_client.setex(turn_count_key, 86400, "0")
            
            logger.info(f"Hydrated Redis with summary context for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error hydrating Redis for user {user_id}: {e}")
            return False

    async def _background_sql_operations(self, user_id: str, home_country: str, host_country: str, user_message: str, assistant_response: str, skip_timer_reset: bool = False, session_id: str = None) -> None:
        """
        Background SQL operations that don't block the main conversation flow
        
        Args:
            user_id: User ID
            home_country: Home country
            host_country: Host country
            user_message: User message content
            assistant_response: Assistant response content
            skip_timer_reset: Skip timer reset to avoid cancelling immediate cleanup tasks
            session_id: Optional session ID to use instead of creating/finding one
        """
        try:
            from dependencies import get_session_service
            session_service = get_session_service()
            
            # 1. Add message, get/create session, and create link all in one transaction
            if session_id:
                # Use provided session_id (from max turns flow)
                message_id = await session_service.add_message_and_link_sql(user_id, home_country, host_country, user_message, assistant_response, session_id)
            else:
                # Do everything in one transaction (normal flow)
                session_id, message_id = await session_service.add_message_with_session_and_link_sql(user_id, home_country, host_country, user_message, assistant_response)
            
            if session_id:
                # 2. Update heartbeat
                await session_service.heartbeat(session_id)
                
                # 4. Reset cleanup timer (4 hours from now) - skip if immediate cleanup is pending
                if not skip_timer_reset:
                    session_service.reset_session_cleanup_timer(session_id, user_id, home_country, host_country)
                else:
                    logger.info(f"Skipped timer reset for user {user_id} to avoid cancelling immediate cleanup task")
                
            logger.info(f"Background SQL operations completed for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error in background SQL operations for user {user_id}: {e}")
            # Don't raise - this is fire-and-forget