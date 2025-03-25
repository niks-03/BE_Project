from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import os
import logging


logger = logging.getLogger(__name__)

global stop_words
stop_words = set(stopwords.words('english'))

def get_query_context(query: str):
    clean_query = query.lower().replace("\n", " ")
    tokens = word_tokenize(clean_query)
    clean_tokens = [token for token in tokens if token not in stop_words]
    context = " ".join(clean_tokens)
    # context_query = f"context:[{context}] content :{query}"
    
    return context

def get_context(vector_store, query, cross_encoder, embedding_model):
    try:
        query_context = get_query_context(query)
        logger.info(f"Query context generated: {query_context[:100]}...")

        embedded_query_context = embedding_model.embed_query(query_context)
        logger.info("Query embedding generated successfully")

        context = vector_store.similarity_search_by_vector_with_relevance_scores(embedded_query_context, k=10)
        logger.info(f"Found {len(context)} similar documents")

        if not context:
            logger.warning("No similar documents found")
            return None

        # Create pairs for cross-encoder
        pairs = [(query_context, doc[0].page_content) for doc in context]
        scores = cross_encoder.predict(pairs)

        # Create list of (score, document) tuples and sort by score
        scored_results = list(zip(scores, [doc[0] for doc in context]))
        sorted_results = sorted(scored_results, key=lambda x: x[0], reverse=True)
        
        # Extract just the documents from sorted results
        reranked_docs = [doc for _, doc in sorted_results]
        
        # Join the page contents of top 6 documents
        final_context = " \n\n ".join(doc.page_content for doc in reranked_docs[:6])
        
        if final_context:
            logger.info(f"Final context generated (length: {len(final_context)})")
            return final_context
        else:
            logger.warning("No final context generated")
            return None

    except Exception as e:
        logger.error(f"Error in get_context: {str(e)}")
        raise Exception(f"Error getting context: {str(e)}")