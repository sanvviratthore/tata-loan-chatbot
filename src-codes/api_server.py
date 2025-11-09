"""
FastAPI Server for EY Tata Capital Loan Chatbot
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
from datetime import datetime
import base64

from master_agent import create_master_agent
from utils.session_manager import SessionManager
from utils.logger import get_logger

# Initialize FastAPI app
app = FastAPI(title="EY Tata Capital Loan Platform", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize logger
logger = get_logger("api_server")


def convert_bytes_to_base64(data):
    """
    Recursively convert all bytes objects to base64 strings in a data structure.
    Also normalizes pdf_bytes to pdf_content for frontend compatibility.
    
    Args:
        data: Dictionary, list, or other data structure that may contain bytes
    
    Returns:
        Data structure with all bytes converted to base64 strings
    """
    if isinstance(data, bytes):
        return base64.b64encode(data).decode('utf-8')
    elif isinstance(data, dict):
        result = {key: convert_bytes_to_base64(value) for key, value in data.items()}
        # Normalize pdf_bytes to pdf_content for frontend
        if 'pdf_bytes' in result and 'pdf_content' not in result:
            result['pdf_content'] = result.pop('pdf_bytes')
        return result
    elif isinstance(data, list):
        return [convert_bytes_to_base64(item) for item in data]
    elif isinstance(data, tuple):
        return tuple(convert_bytes_to_base64(item) for item in data)
    else:
        return data


# Initialize session manager and master agent
session_manager = SessionManager(session_ttl=3600)
api_key = os.getenv("OPENROUTER_API_KEY")
use_mock_llm = api_key is None or api_key.strip() == ""

if use_mock_llm:
    logger.warning("OPENROUTER_API_KEY not found, using mock LLM")
else:
    logger.info("Using OpenRouter LLM")

master_agent = create_master_agent(
    session_manager=session_manager,
    use_mock_llm=use_mock_llm
)

# Pydantic models
class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    success: bool
    message: str
    agent: str
    session_id: str
    current_stage: str
    data: Optional[Dict[str, Any]] = None
    
    class Config:
        arbitrary_types_allowed = True

class SessionCreate(BaseModel):
    pass

class SessionResponse(BaseModel):
    session_id: str
    created_at: str

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main HTML page"""
    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Frontend not found. Please ensure static/index.html exists.</h1>", status_code=404)


@app.post("/api/session/create", response_model=SessionResponse)
async def create_session():
    """Create a new chat session"""
    try:
        session_id = session_manager.create_session()
        logger.info(f"Created new session: {session_id}")
        
        return SessionResponse(
            session_id=session_id,
            created_at=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create session")


@app.post("/api/chat", response_model=ChatResponse)
async def chat(chat_message: ChatMessage):
    """Process chat message"""
    try:
        # Create session if not provided
        session_id = chat_message.session_id
        if not session_id:
            session_id = session_manager.create_session()
            logger.info(f"Created new session: {session_id}")
        
        # Route message through master agent
        response = master_agent.route_message(
            user_message=chat_message.message,
            session_id=session_id
        )
        
        # Handle PDF data if present - recursively convert all bytes to base64
        response_data = response.get("data")
        if response_data:
            response_data = convert_bytes_to_base64(response_data)
        
        return ChatResponse(
            success=response.get("success", False),
            message=response.get("message", ""),
            agent=response.get("agent", "assistant"),
            session_id=session_id,
            current_stage=response.get("current_stage", "INIT"),
            data=response_data
        )
    
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process message")


@app.get("/api/session/{session_id}/summary")
async def get_session_summary(session_id: str):
    """Get session summary"""
    try:
        summary = master_agent.get_conversation_summary(session_id)
        if summary is None:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return summary
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session summary: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get session summary")


@app.delete("/api/session/{session_id}")
async def reset_session(session_id: str):
    """Reset/delete a session"""
    try:
        master_agent.reset_session(session_id)
        return {"success": True, "message": "Session reset successfully"}
    
    except Exception as e:
        logger.error(f"Error resetting session: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to reset session")


@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    """Handle document upload"""
    try:
        # Validate file type
        allowed_types = ["application/pdf", "image/jpeg", "image/png", "image/jpg"]
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Invalid file type")
        
        # Validate file size (max 5MB)
        content = await file.read()
        if len(content) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size exceeds 5MB limit")
        
        # Encode file content
        encoded_content = base64.b64encode(content).decode()
        
        return {
            "success": True,
            "filename": file.filename,
            "content_type": file.content_type,
            "size": len(content),
            "encoded_content": encoded_content
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to upload document")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "using_mock_llm": use_mock_llm
    }


if __name__ == "__main__":
    import uvicorn
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run server
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
