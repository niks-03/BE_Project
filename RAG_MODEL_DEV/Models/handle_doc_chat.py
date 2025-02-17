from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.document_loaders import PyMuPDFLoader
from langchain.prompts import PromptTemplate
from langchain.tools import Tool
from langchain.agents.agent_toolkits import (VectorStoreInfo, VectorStoreToolkit)
from langchain.agents import (AgentExecutor, create_react_agent)

from sklearn.cluster import KMeans
from dotenv import load_dotenv
import numpy as np
import os
import logging

logger = logging.getLogger(__name__)

load_dotenv()
KEY = os.getenv("API_KEY_1")

llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=1,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    api_key=KEY
)

def get_summary_doc_context(embedding_model, file_name):
    base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "upload_files")
    closest_indices = []

    try:
        if os.path.exists(os.path.join(base_path, file_name)):
            loader = PyMuPDFLoader(os.path.join(base_path, file_name))
            pages = loader.load_and_split()
            logger.info(f"loaded document: {len(pages)}")

            vectors = embedding_model.embed_documents([page.page_content for page in pages])

            if len(pages) > 20:
                num_clusters = 11
            else:
                num_clusters = int(len(vectors)/2)

            kmeans = KMeans(n_clusters=num_clusters, random_state=100).fit(vectors)

            for i in range(num_clusters):
                distances = np.linalg.norm(vectors - kmeans.cluster_centers_[i], axis=1)
                closest_index = np.argmin(distances)
                closest_indices.append(closest_index)

            selected_indices = sorted(closest_indices)
            selected_docs = [pages[index] for index in selected_indices]
            final_selected_docs = [doc for doc in selected_docs if len(doc.page_content) > 250]
            logger.info(f"final selected docs: {len(final_selected_docs)}")

            summary_context = "\n\n".join(doc.page_content for doc in final_selected_docs)
            logging.info("summary context generated")

            return summary_context
        
        else:
            logging.error("File not found for summary context")
            raise Exception(f"File not found for summary context")
    except Exception as e:
        logging.error(f"Error finding summary context: {str(e)}")
        raise Exception(f"Error finding summary context: {str(e)}")



def summarization_tool_fun(summary_context):
    summary_prompt = """You will be given a financial document containing key financial data, insights, and analysis. The document context will be enclosed in triple backticks (```).  
                Your goal is to generate a structured and concise summary in bullet points highlighting the important financial metrics, trends, and insights from the document. Ensure that the summary includes key figures, performance indicators, and any notable observations.  
                NOTE : *Please return the output got in first attempt*. Do not refine it further.
                ```{text}```  
                FINANCIAL SUMMARY: """
    summary_prompt_template = PromptTemplate(template=summary_prompt, input_variables=["text"])

    summary_chain = summary_prompt_template | llm

    def summarize_chain(text):
        return summary_chain.invoke({"text":summary_context})

    summarizing_tool = Tool.from_function(
        name="summarization_tool",
        description="Use this tool when asked to summarize the document or provide an overview.",
        func=summarize_chain,
    )

    return summarizing_tool


def classify_query(query):
    summary_keywords = ["summary", "summarize", "summarise", "overview", "brief", "about"]

    if any(keyword in query.lower() for keyword in summary_keywords):
        return "summary_request"
    else:
        return "direct_question"

def get_llm_response(user_query, vector_store, query_context, memory, embedding_model, file_name):

    if classify_query(query=user_query) == "summary_request":
        query = user_query + "In proper bullet points with long context."
        context = get_summary_doc_context(embedding_model=embedding_model,
                                          file_name=file_name)
    else:
        query = user_query
        context = query_context
    
    SUMMARIZATION_TOOL = summarization_tool_fun(summary_context=context)
    vectorStoreInfo = VectorStoreInfo(name="financial_analysis",
                                      description="Comprehensive financial report analysis tool for banking and corporate finance",
                                      vectorstore=vector_store)
    vectorStoreTool = VectorStoreToolkit(vectorstore_info=vectorStoreInfo, llm=llm)

    tools = vectorStoreTool.get_tools() + [SUMMARIZATION_TOOL]
    logger.info(f"tools built up: {tools}")

    baseprompt = """You are a helpful financial analyst AI assistant. Your task is to answer questions based on the given context, which is derived from an uploaded document. If asked to explain, elaborate the terms in your final answer.
    Always use the information provided in the context to answer the query. This context represents the content of the uploaded document.

    Answer the following questions as best you can. You have access to the following tools:
    {tools}

    When answering queries:
    1. Provide accurate and relevant information from the uploaded document.
    2. Use financial terminology appropriately.
    3. If asked for calculations or comparisons, double-check your math.
    4. If the information is not in the uploaded document, clearly state that.
    5. Offer concise but comprehensive answers, and ask if the user needs more details.
    6. If applicable, mention any important caveats or contexts for the financial data.
    7. While explaining terms, explain them in short way to minimize number of tokens.

    Use the following format:

    Question: the input question you must answer
    Thought: you should always think about what to do and Do I need to use a tool? 
    Action: the action to take, should be one of {tool_names}

    Final Answer: the final answer to the original input question

    Begin!
    Question: {input}
    context:{context}
    chat_history: {memory}
    Thought:{agent_scratchpad}"""


    baseprompttemplate = PromptTemplate(template=baseprompt, partial_variables={"context":context, "memory":memory.buffer})

    try:
        agent = create_react_agent(
            llm=llm,
            tools=tools,
            prompt=baseprompttemplate,
        )
        logger.info(f"agent created: {agent}")
    except Exception as e:
        logger.error(f"error creating agent: {str(e)}")
        raise Exception(f"error creating agent: {str(e)}")

    try:
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=True,
            return_intermediate_steps=True,
            memory=memory
        )
        logger.info(f"agent executor created: {agent_executor}")
    except Exception as e:
        logger.error(f"error creating agent executor: {str(e)}")
        raise Exception(f"error creating agent executor: {str(e)}")

    try:
        output = agent_executor.invoke({"input": query})
        logger.info(f"response generated: {output}")
        return output["output"]
    except Exception as e:
        logger.info(f"error generating response: {str(e)}")
        raise Exception(f"error generating response: {str(e)}")
