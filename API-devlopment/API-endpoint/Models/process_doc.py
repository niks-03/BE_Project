import os
from collections import defaultdict
from typing import List
import logging

from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.documents import Document

from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import re

from unstructured_client.models import shared, operations
from unstructured_client.models.errors import SDKError
from unstructured.staging.base import dict_to_elements
from unstructured_client import UnstructuredClient
import markdownify

from dotenv import load_dotenv
load_dotenv()

client = UnstructuredClient(
    api_key_auth=os.getenv("UNSTRUCTURED_API_KEY"),
    server_url=os.getenv("UNSTRUCTURED_API_URL")
)

global stop_words
stop_words = set(stopwords.words('english'))

logger = logging.getLogger(__name__)

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

def combine_documents_by_page(documents: List[Document]) -> List[Document]:
    # Group documents by page_number
    page_groups = defaultdict(list)
    for doc in documents:
        page_num = doc.metadata.get("page_number", 1)  # Default to 1 if not present
        page_groups[page_num].append(doc)
    
    merged_docs = []
    
    for page_num, docs in page_groups.items():
        if not docs:
            continue
        
        # Combine page_content
        combined_content = "\n".join(doc.page_content for doc in docs)
        
        # Merge metadata (take the first doc's metadata as base, then update if needed)
        merged_metadata = docs[0].metadata.copy()
        
        # Optionally, handle special cases (e.g., parent_id, filename conflicts)
        for doc in docs[1:]:
            for key, value in doc.metadata.items():
                if key not in merged_metadata or merged_metadata[key] != value:
                    # Handle conflicts (here, we just take the latest)
                    merged_metadata[key] = value
        
        merged_doc = Document(
            page_content=combined_content,
            metadata=merged_metadata
        )
        merged_docs.append(merged_doc)
    
    return merged_docs

def sanitize_metadata(metadata):
    """Convert any list values in metadata to strings."""
    sanitized = {}
    for key, value in metadata.items():
        if isinstance(value, list):
            sanitized[key] = ", ".join(str(v) for v in value)
        else:
            sanitized[key] = value
    return sanitized

def process_document(filepath: str, filename: str, embedding_model, cross_encoder_model):
    base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "upload_files")
    documents_with_context=[]
    documents = []
    unstructured_docs = []

    try:
        if os.path.exists(os.path.join(base_path, filename)):
            with open(os.path.join(base_path, filename), "rb") as f:
                files = shared.Files(
                    content=f.read(),
                    file_name=os.path.join(base_path, filename)
                )
            
            req = operations.PartitionRequest(
                partition_parameters=shared.PartitionParameters(
                files=files,
                strategy="hi_res",
                hi_res_model_name="yolox",
                skip_infer_table_types=[],
                pdf_infer_table_structure=True))
            
            try:
                resp = client.general.partition(request=req)
                elements = dict_to_elements(resp.elements)
                logger.info(f"loaded document: {len(elements)}")
            except SDKError as e:
                logger.error(f"Error processing document with unstructured: {str(e)}")
                raise Exception(f"Error processing document with unstructured: {str(e)}")
            
            for element in elements:
                if element.category == "Table":
                    table_html = element.metadata.text_as_html
                    markdown_table = markdownify.markdownify(table_html, heading_style="ATX")
                    metadata = sanitize_metadata(element.to_dict()['metadata'])
                    unstructured_docs.append(Document(page_content=markdown_table, metadata=metadata))
                else:      
                    metadata = sanitize_metadata(element.to_dict()['metadata'])
                    unstructured_docs.append(Document(page_content=element.text, metadata=metadata))

            merged_documents = combine_documents_by_page(unstructured_docs)

            for page in merged_documents:
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
   
