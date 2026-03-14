from pydantic import BaseModel

class QueryRequest(BaseModel):
    """Query request model"""
    query: str
    country: str = "Canada"
    top_k: int = 3

class TwoCountriesRequest(BaseModel):
    """Two countries request model"""
    query: str
    home_country: str = "Canada"
    host_country: str = "Germany"
    user_id: str = "001"
    top_k: int = 3

class InitializeSessionRequest(BaseModel):
    """Initialize request model"""
    user_id: str
    home_country: str
    host_country: str

class CloseSessionRequest(BaseModel):
    """Close session request model"""
    session_id: str
