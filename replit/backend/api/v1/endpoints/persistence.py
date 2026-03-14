from fastapi import APIRouter, HTTPException, Depends
from models.response import APIResponse
from db.pinecone_db import PineconeDB
# from infra import mongo  # Commented out MongoDB
from dependencies import get_vector_db
from infra.logger import logger

persistence_router = APIRouter(
    tags=["persistence"],
    responses={
        200: {"description": "Persistence operation successful"},
        500: {"description": "Persistence operation failed"}
    })

@persistence_router.delete("/country/{country}")
async def delete_country_persistence(
    country: str,
    vector_db: PineconeDB = Depends(get_vector_db)
):
    """
    Delete all persistence data for a specific country from Pinecone.
    
    Args:
        country (str): Country name to delete
        
    Returns:
        APIResponse: Confirmation of deletion
    """
    try:
        vector_db.delete_country_collection(country)
        # mongo.delete_country_collection(country)  # Commented out MongoDB
        
        logger.info(f"Successfully deleted all persistence data for country: {country}")
        
        return APIResponse(
            message=f"Successfully deleted all persistence data for country: {country}",
            data={"country": country, "status": "deleted"}
        )
    except Exception as e:
        logger.error(f"Error deleting country persistence for {country}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete persistence data for country {country}: {str(e)}"
        )

@persistence_router.delete("/flush-all")
async def flush_all_persistence(
    vector_db: PineconeDB = Depends(get_vector_db)
):
    """
    Delete all persistence data from Pinecone.
    
    Returns:
        APIResponse: Confirmation of flush operation
    """
    try:
        vector_db.flush_all_collections()
        # mongo.flush_all_collections()  # Commented out MongoDB
        
        logger.info("Successfully flushed all persistence data")
        
        return APIResponse(
            message="Successfully flushed all persistence data from Pinecone",
            data={"status": "flushed", "databases": ["Pinecone"]}
        )
    except Exception as e:
        logger.error(f"Error flushing all persistence data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to flush all persistence data: {str(e)}"
        )