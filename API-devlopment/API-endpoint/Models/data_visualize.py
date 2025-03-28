from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
import matplotlib.pyplot as plt
import pandas as pd
import textwrap
import logging
import json
import re
import io
import os
from dotenv import load_dotenv

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

llm_pro = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro",
    temperature=1,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    api_key=KEY
)


def extract_code_block(response_text):
    code_blocks = re.findall(r"```(python)?(.*?)```", response_text, re.DOTALL)
    code = "\n".join([block[1].strip() for block in code_blocks])
    # print(f"CODE: {code}")

    logger.info(f"extracted code block successfully: {code}")
    return code

def execute_code(response_text: str, df: pd.DataFrame, query):
    code = extract_code_block(response_text=response_text)
    
    # Remove any plt.show() commands from the code
    code_lines = code.split('\n')
    filtered_code = '\n'.join([line for line in code_lines if 'plt.show()' not in line])
    
    local_vars = {'df': df}
    try:
        # Make sure we're using the 'Agg' backend which doesn't require a display
        import matplotlib
        matplotlib.use('Agg')
        
        # Clear any existing plots
        plt.clf()
        plt.close('all')
        
        # Execute the plotting code
        exec(textwrap.dedent(filtered_code), globals(), local_vars)
        
        # Create a buffer and save the figure
        buf = io.BytesIO()
        
        # Get the current figure - important if code doesn't assign to a variable
        fig = plt.gcf()
        
        # Save the figure to buffer
        fig.savefig(buf, format='png', bbox_inches='tight', dpi=100)
        
        # Close the figure to free memory
        plt.close(fig)
        
        # Reset buffer position
        buf.seek(0)
        
        image_bytes = buf.getvalue()
        logger.info(f"Generated image buffer size: {len(image_bytes)} bytes")
        
        return image_bytes
    
    except Exception as e:
        logger.error(f"Error while generating image buffer: {e}")
        plt.close('all')  # Clean up any open figures
        raise Exception(e)

def handle_query(df, column_names, data_type_list, query):
    prompt_content = f"""
    Dataset 'df' is pre-loaded with columns: {column_names}
    Data types: {data_type_list}

    Data Validation Steps:
    1. Find key query values
    2. Verify numeric columns
    3. Use df[df['key_column_name'].str.lower().str.contains('key_value')] for row matching
    4. Validate columns/rows
    5. Use numeric data for charts
    6. Text columns for labels

    Chart Specs (Pandas/Matplotlib/Seaborn only):
    - Set: sns.set_theme(style="whitegrid")
    - Colors: 
    - Fig background: #f4f4f8
    - Axes background: #ffffff
    - Palette: [#e60049", "#0bb4ff", "#50e991", "#e6d800", "#9b19f5", "#ffa300", "#dc0ab4", "#b3d4ff", "#00bfa0"]
    - Legend: visible, white background, black border
    - Text: Black titles, #333333 labels/ticks

    Format:
    - Single code block (```)
    - Create fig object
    - No comments/explanations
    - Debug before submission
    - Validate row selection

    Query: `{query}` """

    try:
        response = llm.invoke(prompt_content)
        logger.info(f"successfully invoked llm: {response}")
        result = response.content.strip()
    except Exception as e:
        logger.error(f"Error while invoking llm: {str(e)}")
        raise Exception(e)

    graph_bytes_string = execute_code(response_text=result, df=df, query=query)
    return graph_bytes_string

def get_chart_explanation(df, column_names, data_type_list, query):
    data_template = """Dataset 'df' is pre-loaded with columns: {column_names}
                Data types: {data_type_list}
                Sample Data: {sample_data}
                
                **Your Task**:
                - your an AI assistant that helps to get the idea of user question what is he asking in the question and write a pandas query to get the data that is required to create the chart/graph asked by user. 
                - I have provided the column names and column_data_types, take help of it.
                - Recheck the code before answering the final output.
                - Pandas query should contain only given columns.
                - Take help of *Sample data* given to you.
                - Always focus on what user is asking and create the pandas query according to that.
                - Take help of other columns that you think are related to key query values like, quarter related to years and so...

                **Format**:
                - Single code block (```)
                - Always use the variable named *chart_data* to store the last result of all pandas query.
                - Result should be in *JSON* format only.
                - No comments/explanations
                - Debug before submission
                
                Question: `{input}`"""
    
    chart_data_template = PromptTemplate(template=data_template, partial_variables={"column_names":column_names, "data_type_list":data_type_list, "sample_data":df.head(10)})
    data_chain = chart_data_template | llm_pro
    result = data_chain.invoke({"input":query})

    code = extract_code_block(response_text=result.content.strip())
    local_vars = {'df': df}
    exec(textwrap.dedent(code), globals(), local_vars)

    chart_data = local_vars.get('chart_data', None)

    if chart_data is not None:
        explanation_template = """You are an AI assistant that is good at explaining the data.
                            Trend, changes, impact of change in data points are explained by you should be always in well format and professional speak.

                            Dataset 'df' is pre-loaded with columns: {column_names}
                            Data types: {data_type_list}
                            
                            **Your task**:
                            - You have provided with the *chart_data* and the *user_query*.
                            - You have to explain how the data trend is changed according to user query.
                            - What insights data is trying to explain basis on user query.
                            - Always provide the answer basis on the chart_data you have. 

                            **Note*: Don't give any suggestions to user query. Only provide the explanation over given data and nothing else.
                            
                            *chart_data*: `{chart_data}`
                            *user_query*: `{input}`"""
        
        chart_explanation_template = PromptTemplate(template=explanation_template, partial_variables={"chart_data":chart_data, "column_names":column_names, "data_type_list":data_type_list})
        explanation_chain = chart_explanation_template | llm
        explanation = explanation_chain.invoke({"input":query})

        # print(f"chart_data: {chart_data}","\n\n")
        # print(f"explanation: {explanation}","\n\n")
        
        return [chart_data, explanation.content]
    
    else:
        logger.error(f"error in chart_data creation")
        raise Exception("error in chart_data creation")

def visualize_data(query, file_name, advance="false"):
    base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "upload_files")
    file_path = os.path.join(base_path, file_name)
    file_exists = os.path.exists(file_path)
    try:
        if file_exists:
            if file_name.endswith(".csv"):
                logger.info(f"found visualization file: {str(file_name)}")
                df = pd.read_csv(file_path)

            elif file_name.endswith(".xlsx") or file_name.endswith('.xls'):
                logger.info(f"found visualization file: {str(file_name)}")
                df = pd.read_excel(file_path)

            else:
                df = None
                data_type_list = None

            try:
                if df is not None:
                    if not df.empty:
                        logger.info(f"generating visualization for file: {str(file_name)}")
                        column_names = df.columns
                        data_type_list = df.dtypes.tolist()
                        
                        if advance == "true":
                            graph_bytes_string = handle_query(df=df, column_names=column_names, data_type_list=data_type_list, query=query)
                            graph_info = get_chart_explanation(df=df, query=query, column_names=column_names, data_type_list=data_type_list)

                            return {"graph_byte_string":graph_bytes_string,
                            "graph_data":json.loads(graph_info[0]),
                            "graph_explanation":graph_info[1]}
                        
                        else:
                            graph_bytes_string = handle_query(df=df, column_names=column_names, data_type_list=data_type_list, query=query)
                            
                            return graph_bytes_string
                    else:
                        raise Exception("Visualization data file is empty.")
                else:
                    raise Exception("Error while processing visualization data file.")
                
            except Exception as e:
                return str(e)
        
        else:
            logger.error(f"visualization file does not exist at : {file_path}")
            raise Exception("Visualization file does not exist in server.")
            
    except Exception as e:
        return str(e)