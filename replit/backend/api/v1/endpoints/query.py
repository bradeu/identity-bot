from fastapi import APIRouter
from fastapi import Depends
from dependencies import get_query_service, get_conversation_service, get_session_service
from models.request import InitializeSessionRequest
from models.request import CloseSessionRequest
from models.request import TwoCountriesRequest
from models.response import QueryResponse
from fastapi import HTTPException
from infra.logger import logger

query_router = APIRouter(
    tags=["query"],
    responses={
        200: {"description": "Query successful"},
        503: {"description": "Service unhealthy"}
    }
)

# @query_router.post("/ask")
# async def ask(request: QueryRequest, service = Depends(get_query_service)):
#     """
#     Query endpoint

#     Args:
#         request: QueryRequest
#         service: QueryService

#     Returns:
#         QueryResponse: Query status of the API
#     """
#     try:
#         results = service.query(request.query, request.country, request.top_k)
#         return QueryResponse(message="Query successful", data=results)
#     except Exception as e:
#         raise HTTPException(
#             status_code=503,
#             detail=f"Service unhealthy: {str(e)}"
#         )

@query_router.post("/initialize-session")
async def initialize_session(
    request: InitializeSessionRequest,
    conversation_service = Depends(get_conversation_service)
):
    """
    Initialize session endpoint for conversation history

    Args:
        request: InitializeSessionRequest
        conversation_service: ConversationService

    Returns:
        QueryResponse: Initialize session status of the API
    """
    try:
        if await conversation_service.hydrate_redis(request.user_id, request.home_country, request.host_country):
            return QueryResponse(message="Initialize session successful", data={"initialized": True})
        else:
            return QueryResponse(message="Initialize session failed", data={"initialized": False})
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Service unhealthy: {str(e)}"
        )

@query_router.post("/close-session")
async def close_session(
    request: CloseSessionRequest,
    session_service = Depends(get_session_service)
):
    """
    Close session endpoint

    Args:
        request: CloseSessionRequest
        session_service: SessionService

    Returns:
        QueryResponse: Close session status of the API
    """
    try:
        if await session_service.close_session(request.session_id):
            return QueryResponse(message="Close session successful", data={"closed": True})
        else:
            return QueryResponse(message="Close session failed", data={"closed": False})
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Service unhealthy: {str(e)}"
        )

@query_router.post("/two-countries")
async def two_countries(
    request: TwoCountriesRequest, 
    query_service = Depends(get_query_service),
    conversation_service = Depends(get_conversation_service),
    session_service = Depends(get_session_service)
):
    """
    Query endpoint for home and host country queries with conversation history

    Args:
        request: TwoCountriesRequest
        query_service: QueryService
        conversation_service: ConversationService
        session_service: SessionService
    Returns:
        QueryResponse: Query status of the API
    """ 
    try:
        if await conversation_service.should_end_conversation(request.user_id, request.home_country, request.host_country):
            return QueryResponse(
                message="Conversation ended - maximum turns reached",
                data={
                    "response": "This conversation has reached its maximum limit. Please start a new conversation.",
                    "conversation_ended": True,
                    "turns_completed": conversation_service.max_turns,
                    "user_id": request.user_id
                }
            )

        # Auto-hydrate Redis from database summary if Redis is empty
        conversation_history = await conversation_service.get_conversation_history(
            request.user_id, request.home_country, request.host_country
        )

        # If Redis is empty, try to hydrate from database summary
        if not conversation_history:
            hydrated = await conversation_service.hydrate_redis(
                request.user_id, request.home_country, request.host_country
            )
            if hydrated:
                logger.info(f"Auto-hydrated Redis from database summary for user {request.user_id}")
                # Get the hydrated conversation history
                conversation_history = await conversation_service.get_conversation_history(
                    request.user_id, request.home_country, request.host_country
                )
        
        results = query_service.query_two_countries(
            request.query, 
            request.home_country, 
            request.host_country, 
            request.top_k,
            conversation_history
        )
        
        current_turns = await conversation_service.add_message_pair(
            user_id=request.user_id,
            home_country=request.home_country,
            host_country=request.host_country,
            user_message=request.query,
            assistant_response=results.get("response", "")
        )

        logger.info(f"Current turns: {current_turns}, Background SQL operations queued")
        
        results["current_turns"] = current_turns
        results["max_turns"] = conversation_service.max_turns
        results["conversation_will_end"] = current_turns >= conversation_service.max_turns
        results["user_id"] = request.user_id
        
        return QueryResponse(message="Query successful", data=results)
        
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Service unhealthy: {str(e)}"
        )

@query_router.post("/conversation/reset")
async def reset_conversation(
    request: TwoCountriesRequest,
    conversation_service = Depends(get_conversation_service),
    session_service = Depends(get_session_service)
):
    """
    Reset conversation history for a user and trigger session cleanup
    
    Args:
        request: TwoCountriesRequest (only user_id, home_country, host_country needed)
        conversation_service: ConversationService
        session_service: SessionService
        
    Returns:
        QueryResponse: Reset status
    """
    try:
        # 1. Flush conversation history
        success = await conversation_service.flush_conversation(
            user_id=request.user_id,
            home_country=request.home_country,
            host_country=request.host_country
        )
        
        # 2. Get current active session for the user
        current_session_id = await session_service.get_or_create_session_sql(request.user_id)
        
        # 3. Trigger session cleanup if session exists
        session_cleanup_triggered = False
        if current_session_id:
            try:
                # Cancel any existing cleanup timer
                session_service.cancel_existing_cleanup(current_session_id)
                
                # Trigger immediate session cleanup
                from tasks.background_tasks import cleanup_single_session_task
                cleanup_single_session_task.delay(current_session_id, request.user_id, request.home_country, request.host_country)
                session_cleanup_triggered = True
                
                logger.info(f"Triggered session cleanup for user {request.user_id}, session {current_session_id}")
            except Exception as e:
                logger.error(f"Error triggering session cleanup for user {request.user_id}: {e}")
        
        if success:
            return QueryResponse(
                message="Conversation reset successfully", 
                data={
                    "reset": True, 
                    "turns_available": conversation_service.max_turns,
                    "session_cleanup_triggered": session_cleanup_triggered,
                    "session_id": current_session_id
                }
            )
        else:
            return QueryResponse(
                message="No conversation to reset", 
                data={
                    "reset": False, 
                    "turns_available": conversation_service.max_turns,
                    "session_cleanup_triggered": session_cleanup_triggered,
                    "session_id": current_session_id
                }
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Service unhealthy: {str(e)}"
        )
    
# @query_router.post("/two-countries/stream")
# async def two_countries_stream(request: TwoCountriesRequest, service = Depends(get_query_service)):
#     """
#     Query endpoint for home and host country queries with streaming

#     Args:
#         request: TwoCountriesRequest
#         service: QueryService

#     Returns:
#         StreamingResponse: Streaming tokens from the LLM
#     """
    
#     async def generate_stream():
#         try:
#             for chunk in service.query_two_countries_stream(
#                 request.query, 
#                 request.home_country, 
#                 request.host_country, 
#                 request.top_k
#             ):
#                 # Send each chunk as Server-Sent Events format
#                 chunk_json = json.dumps(chunk)
#                 yield f"data: {chunk_json}\n\n"
                    
#         except Exception as e:
#             error_chunk = json.dumps({"type": "error", "error": str(e)})
#             yield f"data: {error_chunk}\n\n"
    
#     return StreamingResponse(
#         generate_stream(),
#         media_type="text/event-stream",
#         headers={
#             "Cache-Control": "no-cache", 
#             "Connection": "keep-alive",
#             "Access-Control-Allow-Origin": "*",
#             "Access-Control-Allow-Headers": "*"
#         }
#     )