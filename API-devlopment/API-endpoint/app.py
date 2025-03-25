from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import Response
from contextlib import asynccontextmanager
from pydantic import BaseModel
from pathlib import Path
import shutil
import logging
import sys
import os

from langchain_huggingface import HuggingFaceEmbeddings
from sentence_transformers import CrossEncoder
from langchain.memory import ConversationBufferWindowMemory

from Models.refine_query import RefineQuery
from Models.process_doc import process_document
from Models.find_context import get_context
from Models.handle_doc_chat import get_llm_response
from Models.data_visualize import visualize_data

# Create logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# Set up logging to file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/fatapi_main.log'),
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
        memory = ConversationBufferWindowMemory(k=10, memory_key="chat_history", return_messages=True, output_key="output")

        app.state.embedding_model = embedding_model
        app.state.cross_encoder_model = cross_encoder_model
        app.state.memory = memory
        app.state.chat_file_name = None
        app.state.visualize_file_name = None
        app.state.vector_store = None

        yield
    finally:
        app.state.embedding_model = None
        app.state.cross_encoder_model = None
        app.state.memory = None
        app.state.chat_file_name = None
        app.state.visualize_file_name = None
        app.state.vector_store = None

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
    
    # Initialize vector store from persist directory if it exists
    try:
        chroma_db_path = os.path.join(os.path.dirname(__file__), "Models", "../chroma-db")
        if os.path.exists(chroma_db_path):
            logger.info("Found existing chroma-db directory")
            # We'll initialize the vector store when needed in the endpoints
            app.state.vector_store = None
        else:
            logger.info("No existing chroma-db directory found")
            app.state.vector_store = None
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        app.state.vector_store = None
    

#### recieve document and process it
class DocumentResponse(BaseModel):
    response: str;
    status: str

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
        file_path, chat_file_name = await save_uploaded_file(file)
        app.state.chat_file_name = chat_file_name
        logger.info(f"File received: {chat_file_name} at {file_path}")
        
        if os.path.exists(file_path):
            try:
                logger.info("Starting document processing...")
                vector_store = process_document(file_path, chat_file_name, app.state.embedding_model, app.state.cross_encoder_model)
                logger.info("Document processing completed")
                
                # Verify vector store has documents
                count = len(vector_store.get()['ids'])
                logger.info(f"Documents in vector store: {count}")
                
                app.state.vector_store = vector_store
                return DocumentResponse(status="success" ,response=f"Successfully processed file {chat_file_name}. Added {count} documents to vector store.")
            except Exception as proc_error:
                logger.error(f"Document Processing error: {str(proc_error)}")
                raise HTTPException(
                    status_code=404, 
                    detail="Error in document processing.")
                # return DocumentResponse(status="error", response=str(proc_error))
        else:
            logger.error("file was not saved successfully in server for processing.")
            raise HTTPException(
                status_code=404,
                detail="File was not saved successfully in server for processing."
            )
        
    except HTTPException as e:
        logger.error(f"error processing document: {str(e)}")
        raise e
            
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal Server Error", "message": "An unexpected error occurred. Please try again later."}
        )
    

### process query and send LLM response
class ChatRequest(BaseModel):
    prompt: str

class ChatResponse(BaseModel):
    response: str

@app.post("/doc-chat", response_model=ChatResponse)
async def Chat(request: ChatRequest):
    try:
        vector_store = app.state.vector_store
        embedding_model = app.state.embedding_model
        cross_encoder_model = app.state.cross_encoder_model
        memory = app.state.memory
        chat_file_name = app.state.chat_file_name

        if vector_store and embedding_model and cross_encoder_model:
            logger.info("Processing user query...")
            context = get_context(
                vector_store=vector_store, 
                query=request.prompt, 
                cross_encoder=cross_encoder_model, 
                embedding_model=embedding_model
            )

            if context:
                refined_query = RefineQuery(request.prompt)
                logger.info("getting LLM response...")
                llm_response = get_llm_response(user_query=refined_query,
                                                vector_store=vector_store, 
                                                query_context=context, 
                                                memory=memory,
                                                embedding_model=embedding_model,
                                                file_name=chat_file_name)

                return ChatResponse(response=llm_response)
            else:
                logger.error("No context found")
                raise HTTPException(
                status_code=404, 
                detail={"error": "Context Not Found", "message": "Sorry, I couldn't find relevant information to answer your question."})
            
        else:
            logger.error("Required components not initialized")
            raise HTTPException(
                status_code=500, 
                detail={"error": "Initialization Error", "message": "System is not properly initialized. Please ensure a document is processed first."})
        
    except HTTPException as e:
        logger.error(f"Error processing user query: {str(e)}")
        raise e
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal Server Error", "message": "An unexpected error occurred. Please try again later."}
        )
    

### endpoint to process structured data to get visuals
class VisualizeDocumentResponse(BaseModel):
    response: str;

@app.post("/save-visualize-data", response_model=VisualizeDocumentResponse)
async def upload_and_save_document(file: UploadFile = File(...)):
    try:
        # Save the file
        file_path, visualize_file_name = await save_uploaded_file(file)
        app.state.visualize_file_name = visualize_file_name
        logger.info(f"Visualize data File received: {visualize_file_name} at {file_path}")
    
        if visualize_file_name:
            return VisualizeDocumentResponse(response=f"Visualization file saved successfully {visualize_file_name}")
        else:
            raise HTTPException(
                status_code=500, 
                detail={"error": "File saving error", "message": "Error while saving Visualization file."})

    except HTTPException as e:
        logger.error(f"{str(e)}")
        return e
    
    except Exception as e:
        logger.info(f"Unexpected error while saving visualization data file: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal Server Error", "message": "An unexpected error occurred. Please try again later."}
        )
    

### process and create data visualization
class VisualizeRequest(BaseModel):
    prompt: str

# class VisualizeResponse(BaseModel):
#     response: str

# @app.post("/visualize", response_model=VisualizeResponse)
@app.post("/visualize")
async def visualize_data_func(request: VisualizeRequest):
    try:
        visualize_file_name = app.state.visualize_file_name

        try:
            graph_byte_string = visualize_data(file_name=visualize_file_name, query=request.prompt)
            logger.info(f"generated graph byte string: {graph_byte_string}")
            return Response(
                content=graph_byte_string, 
                media_type="image/png"
            )
        
        except Exception as e:
            logger.error(f"error while generating graphs: {str(e)}")
            raise HTTPException(status_code=404,
                                detail={"error":"graph generation error", "message":"Error while generating graph."})

    except HTTPException as e:
        return e
    
    except Exception as e:
        logger.error(f"Unexpected error occured: {str(e)}")
        raise HTTPException(status_code=500,
                            detail={"error":"unexpected error occured.", "message": "An unexpected error occurred. Please try again later."})


### ddelte file resources
@app.delete("/clear-uploads")
async def delete_all_files():
    try:
        base_path = os.path.join(os.path.dirname(__file__), "upload_files")
        
        # Check if directory exists
        if not os.path.exists(base_path):
            return {"message": "Upload directory does not exist or is already empty"}
        
        # Count files before deletion
        files = os.listdir(base_path)
        file_count = len(files)
        
        # Option 1: Delete individual files (keeps the directory)
        for filename in files:
            file_path = os.path.join(base_path, filename)
            if os.path.isfile(file_path):
                os.unlink(file_path)
        
        logger.info(f"Successfully deleted {file_count} files from upload directory")
        return {"message": f"Successfully deleted {file_count} files"}
        
    except Exception as e:
        logger.error(f"Error deleting files: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "file deletion error", "message": f"Error while deleting files: {str(e)}"}
        )


### endpoint to check if vectore store is created
@app.get("/check-documents")
async def check_documents():
    try:
        logger.info("Checking vector store state...")
        if not hasattr(app.state, 'vector_store'):
            logger.warning("Vector store not found in app state")
            return {"status": "error", "message": "Vector store not initialized"}
            
        vector_store = app.state.vector_store
        if vector_store is None:
            logger.warning("Vector store is None")
            return {"status": "error", "message": "Vector store is None"}
            
        # Try to load from persist directory if vector store exists
        try:
            chroma_db_path = os.path.join(os.path.dirname(__file__), "Models", "../chroma-db")
            if os.path.exists(chroma_db_path):
                collections = os.listdir(chroma_db_path)
                logger.info(f"Found collections in chroma-db: {collections}")
                
            count = len(vector_store.get()['ids'])
            logger.info(f"Successfully retrieved {count} documents from vector store")
            return {"status": "success", "document_count": count}
        except Exception as e:
            logger.error(f"Error accessing vector store: {str(e)}")
            return {"status": "error", "message": f"Error accessing vector store: {str(e)}"}
            
    except Exception as e:
        logger.error(f"Unexpected error in check-documents: {str(e)}")
        return {"status": "error", "message": str(e)}