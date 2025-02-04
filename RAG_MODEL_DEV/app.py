from fastapi import FastAPI, UploadFile, File, HTTPException
from contextlib import asynccontextmanager
from pydantic import BaseModel
from pathlib import Path
import shutil
import logging
import sys
import os

from langchain_huggingface import HuggingFaceEmbeddings
from sentence_transformers import CrossEncoder

from Models.refine_query import RefineQuery
from Models.process_doc import process_document

# Create logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# Set up logging to file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        # logging.StreamHandler()  # This will also print to console
    ]
)

logger = logging.getLogger(__name__)

# *************************************************

## laod the embedding and cross-encoder models
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        cross_encoder_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

        app.state.embedding_model = embedding_model
        app.state.cross_encoder_model = cross_encoder_model

        yield
    finally:
        app.state.embedding_model = None
        app.state.cross_encoder_model = None

# Initialize FastAPI app
app = FastAPI(lifespan=lifespan)

## use for closing the Fastapi connection
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

## Create temp directory if it doesn't exist
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
        
        if os.path.exists(file_path):
            try:
                # Add more detailed logging
                logger.info("Starting document processing...")
                vector_store = process_document(file_path, file_name, app.state.embedding_model, app.state.cross_encoder_model)
                logger.info("Document processing completed")
                
                # Verify vector store has documents
                if hasattr(vector_store, '_collection'):
                    count = vector_store._collection.count()
                    logger.info(f"Documents in vector store: {count}")
                
                app.state.vector_store = vector_store
                return DocumentResponse(response=f"Successfully processed file {file_name}")
            except Exception as proc_error:
                logger.error(f"Processing error: {str(proc_error)}")
                return DocumentResponse(response=f"An error occurred while processing the document: {str(proc_error)}")
        else:
            raise Exception("File was not saved successfully")
            
    except Exception as e:
        logger.error(f"Error in upload endpoint: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
    
@app.get("/check-documents")
async def check_documents():
    try:
        if hasattr(app.state, 'vector_store'):
            count = len(app.state.vector_store.get()['ids'])
            return {"status": "success", "document_count": count}
        return {"status": "error", "message": "Vector store not initialized"}
    except Exception as e:
        return {"status": "error", "message": str(e)}