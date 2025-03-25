import os
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.documents import Document

from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import re

global stop_words
stop_words = set(stopwords.words('english'))

def preprocess_text(page, metadata):
    filter_page = page.lower().replace("\n", " ")
    return Document(page_content=filter_page, metadata=metadata)
    # documents.append(Document(page_content=filter_page, metadata=metadata))

def preprocess_and_contextadd(metadata, chunk_content):
    tokens = word_tokenize(chunk_content)
    filter_tokens = [token for token in tokens if token not in stop_words]
    doc_context = " ".join([word for word in filter_tokens[:30] if re.match(r'^[a-zA-Z]+$|^(?=.*[a-zA-Z])(?=.*\d)[a-zA-Z0-9]+$', word)])

    # context_documents.append(Document(page_content=f'DOCUMENT-CONTEXT:[{doc_context}]. DOCUMENT-CONTENT: {" ".join(filter_tokens)}', metadata=metadata))
    return Document(page_content=f'DOCUMENT-CONTEXT:[{doc_context}]. DOCUMENT-CONTENT: {" ".join(filter_tokens)}', metadata=metadata)

def process_document(filepath: str, filename: str, embedding_model, cross_encoder_model):
    base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "upload_files")
    documents_with_context=[]
    documents = []

    try:
        if os.path.exists(os.path.join(base_path, filename)):
            #load the document laoder
            loader = PyMuPDFLoader(os.path.join(base_path, filename))
            pages = loader.load_and_split()

            for page in pages:
                cleaned_page = preprocess_text(page=page.page_content, metadata=page.metadata)
                documents.append(cleaned_page)

            text_splitter = RecursiveCharacterTextSplitter(chunk_size = 800, chunk_overlap=200)
            chunks = text_splitter.split_documents(documents=documents)

            for chunk in chunks:
                context_chunk = preprocess_and_contextadd(metadata=chunk.metadata, chunk_content=chunk.page_content)
                documents_with_context.append(context_chunk)

            # Ensure the chroma-db directory exists
            chroma_db_path = os.path.join(os.path.dirname(__file__), "../chroma-db")
            os.makedirs(chroma_db_path, exist_ok=True)

            # Initialize vector store with persist directory
            vector_store = Chroma.from_documents(
                documents=documents_with_context,
                embedding=embedding_model,
                persist_directory=chroma_db_path,
                collection_name=f"report_{filename}" 
            )

            return vector_store

        else:
            raise Exception(f"File not found at {filepath}")

    except Exception as e:
        raise Exception(f"Error processing document: {str(e)}")
   
