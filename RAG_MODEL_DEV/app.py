from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from pathlib import Path
import shutil
import logging
import sys
import os

from Models.refine_query import RefineQuery

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

def receive_signal(signalNumber, frame):
    print('Received:', signalNumber)
    sys.exit()


@app.on_event("startup")
async def startup_event():
    import signal
    signal.signal(signal.SIGINT, receive_signal)
    # startup tasks

# # receive user query and process it
class ChatRequest(BaseModel):
    prompt: str

class ChatResponse(BaseModel):
    response: str

@app.post("/chat", response_model = ChatResponse)
async def Chat(request: ChatRequest):
    refined_query = RefineQuery(request.prompt)
    return ChatResponse(response=refined_query)
    

# recieve document and process it
class DocumentResponse(BaseModel):
    response: str

# Create temp directory if it doesn't exist
UPLOAD_DIR = Path("./upload_files")
UPLOAD_DIR.mkdir(exist_ok=True)

async def save_uploaded_file(file: UploadFile) -> tuple[str, str]:
    try:
        # Create full file path
        file_path = UPLOAD_DIR / file.filename
        
        # Save uploaded file
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return str(file_path), file.filename
        
    except Exception as e:
        logger.error(f"Error saving file: {str(e)}")
        raise Exception(f"Could not save file: {str(e)}")

@app.post("/process-document", response_model=DocumentResponse)
async def upload_and_process_document(file: UploadFile = File(...)):
    try:
        # Save the file
        file_path, file_name = await save_uploaded_file(file)
        logger.info(f"File received: {file_name} at {file_path}")
        
        # Verify file was saved
        if not os.path.exists(file_path):
            raise Exception("File was not saved successfully")
            
        return DocumentResponse(response=f"File received: {file_name} at {file_path}")
        
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))