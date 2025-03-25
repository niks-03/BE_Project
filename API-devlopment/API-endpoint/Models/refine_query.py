from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import os

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

def PromptTempplate():
    template = ChatPromptTemplate.from_messages(
        [("assistant",
          """Your a helpul assistant and your task is to enhance the clarity and completeness of the user query while following these strict requirements:
          REQUIREMENTS:
                1. Respond ONLY with the enhanced version of the query
                2. Preserve ALL original terms exactly as written - do not substitute or remove any words
                3. Maintain the original meaning and intent completely
                4. Add any missing context or implicit requirements
                5. Clarify any ambiguous parts
                6. Structure the query to be clear and precise
                7. Do not include any explanations, notes, or additional text
                8. Do not use bullet points or numbered lists in your response
                9. Format as a single, well-structured paragraph
                10. End the enhanced query with a period
        Provide ONLY the enhanced query in your response, nothing else.
          """),
        ("human", "{input}")]
    )

    return template

# def RefineQuery(query):
#     template = PromptTempplate()
#     chain = template | llm
    
#     result = chain.invoke({
#         "input": query
#     })

#     return result.content

def RefineQuery(query):
    template = PromptTempplate()
    chain = template | llm
    
    try:
        result = chain.invoke({
            "input": query
        })
        return result.content
    except Exception as e:
        return f"An error occurred: {str(e)}"