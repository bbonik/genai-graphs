import streamlit as st
import streamlit.components.v1 as components
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
import base64
import bedrock
import time
import os
import re
import json
import numpy as np
from IPython.display import Image
import datetime



#----------------------------------------------------------- helper functions

# return the text from an html page
def get_html_text(url, postprocess=False, print_text=False):
    request = Request(
        url , 
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36"}
    )
    rawpage = urlopen(request).read()
    soup = BeautifulSoup(rawpage, features="html.parser")
    # kill all script and style elements
    for script in soup(["script", "style", "meta"]):
        script.extract()    # rip it out
    # get text
    text = soup.get_text()
    st.session_state.webpage_title = soup.title.text
    
    if postprocess is True:
        # break into lines and remove leading and trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
    if print_text is True:
        print(text)
    return text


# parsing completion
# def find_between( s, first, last ):
#     try:
#         start = s.index( first ) + len( first )
#         end = s.index( last, start )
#         return s[start:end]
#     except ValueError:
#         return ""
    
    
    
def find_between( s, first, last ):
    try:
        ls_graphs = re.findall(r'<mermaid>(.*?)</mermaid>', s, re.DOTALL)
        return ls_graphs
    except ValueError:
        return ""
    
    
    

def render_graph(graph, show_link=False):
    graphbytes = graph.encode("utf8")
    base64_bytes = base64.urlsafe_b64encode(graphbytes)
    base64_string = base64_bytes.decode("ascii")
    url_rendering = "https://mermaid.ink/img/" + base64_string
    if show_link is True:
        print(url_rendering)
    rendered_graph = Image(url=url_rendering)
    
    return rendered_graph


    
    
def check_graph_validity(graph):
    # checks syntax validity of a mermaid graph
    # st.write("```" + graph)
    graphbytes = graph.encode("utf8")
    base64_bytes = base64.urlsafe_b64encode(graphbytes)
    base64_string = base64_bytes.decode("ascii")
    url = "https://mermaid.ink/img/" + base64_string
    req = Request(url, headers={'User-Agent' : "Magic Browser"})
    flag_valid = True
    try: 
        con = urlopen(req)
    except:
        flag_valid = False
    return flag_valid


    
def standardize_graph(graph):
    # apply string transformation to fix some common mermaid mistakes
    graph = graph.replace('subgraph ""', 'subgraph " "')
    
    return graph



def display_variants(
        diagram,
        webpage_title, 
        window_hight=500,
        theme='default'
    ):

    with st.container(border=True):

        ls_tabs = [
                "Visual gist", 
                "Summary",
                "Mermaid code", 
                "Reasoning"
            ]
            
        for i,current_tab in enumerate(st.tabs(ls_tabs)):
            with current_tab:
                
                if i == 0:  # display selected variant
                    st.markdown("**" + webpage_title + "**")
                    html_code = f"""
                                <html>
                                  <body>
                                    <pre class="mermaid">
                                    {diagram["processed_graph"]}
                                    </pre>
                                    <script type="module">
                                      import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
                                      mermaid.initialize({{ startOnLoad: true, 'theme': '{theme}' }});
                                    </script>
                                  </body>
                                </html>
                                """
                    html_code = html_code.replace("{{", "{")
                    html_code = html_code.replace("}}", "}")
                    components.html(
                        html_code,
                        height=window_hight,
                        scrolling=True
                    )
                
                if i == 1:  # text summary
                    summary = re.findall(
                        r"<summary>(.*?)</summary>", 
                        diagram["raw"], 
                        re.DOTALL
                    )
                    st.markdown(summary[0])
                    
                if i == 2:  # mermaid code
                    st.markdown("```" + diagram["processed_graph"] + "```")
                     
                if i == 3:  # raw llm selection output
                    st.markdown(diagram["justification"])
                


def display_diagram(dc_diagram, webpage_title, iteration, theme='default', window_hight=500):
    
    with st.container(border=True):
        st.markdown("##### Visual gist variation " + str(iteration))

        tab_image, tab_st_graph, tab_graph, tab_raw = st.tabs(
            [
                "Image", 
                "Postprocessed", 
                "Original", 
                "Raw LLM output"
            ]
        )

        with tab_image:
            st.markdown("**" + webpage_title + "**")

            html_code = f"""
                        <html>
                          <body>
                            <pre class="mermaid">
                            {dc_diagram["processed_graph"]}
                            </pre>
                            <script type="module">
                              import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
                              mermaid.initialize({{ startOnLoad: true, 'theme': '{theme}' }});
                            </script>
                          </body>
                        </html>
                        """

            html_code = html_code.replace("{{", "{")
            html_code = html_code.replace("}}", "}")
            components.html(
                html_code,
                height=window_hight,
                scrolling=True
            )

        with tab_st_graph:
            st.markdown("```" + dc_diagram["processed_graph"] + "```")
        with tab_graph:
            st.markdown("```" + dc_diagram["graph"] + "```")
        with tab_raw:
            st.markdown(dc_diagram["raw"])
    

    
    
    
def refine_diagram(
    diagram, 
    iterations=3
):
    
    html_text = st.session_state.text_content
    theme=st.session_state.selectbox_color
    system_prompt = st.session_state.prompt_template_system
    modelId = st.session_state.model_reflect
    window_hight=500
    
    prompt_template = """  
    Here is a given text for you to reference for the following task. Read it carefully because it is necessary for the task that you will have to solve. 

    <text>
    {html_text}
    </text>
    
    Here is a Mermaid diagram intented to summarize the content of the previous text. The intention is that someone who only viewed the given Mermaid diagram, would understand the main concepts of the text, without having to read it.

    <diagram>
    {diagram}
    </diagram>

    Evaluate whether the given Mermaid diagram is a good visual approximation of the given text.
    Here are some points to consider:
    1. What are the most important points of the text, that someone should know about?
    2. Does the diagram mention all these points?
    3. Does the diagram capture all the interactions between all the important points?
    4. Does the diagram use different colors, shapes and arrows to capture the important points and their interactions?
    5. Is the diagramm too simplistic? 
    6. Is the diagram too complicated?
    7. Is the diagram visually pleasing?
    8. Do you think that the diagram can be improved?
    
    Think whether the given diagram can be improved or not, and explain your thought process inside <justification></justification> XML tags.
    If you think that the given Mermaid diagram can be improved, refine it and include the new Mermaid code inside <new_diagram></new_diagram> XML tags.
    If you think that the given Mermaid diagram can not be improved, include the original Mermaid code inside <new_diagram></new_diagram> XML tags.
    Remember don't forget to "close" the new diagram XML tags with </new_diagram>.
    """
    
    # prepare prompt
    prompt = prompt_template.replace("{html_text}", st.session_state.text_content)
    prompt = prompt.replace("{diagram}", diagram)
    
    for i in range(iterations):
        st.write("Iteration " + str(i) + ":")
        
        response = st.session_state.bedrock_runtime.converse(
            modelId=modelId,
            inferenceConfig={
                "temperature": 0.1,  # be more factual
                "maxTokens": 2048,
                "topP": 1,
            },
            system=[
                {
                    "text": system_prompt
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
        )
        response_text = response["output"]["message"]["content"][0]["text"]

        # parsing output
        justification = re.findall(
            r"<justification>(.*?)</justification>", 
            response_text, 
            re.DOTALL
        )
        
        new_diagram = re.findall(
            r"<new_diagram>(.*?)</new_diagram>", 
            response_text, 
            re.DOTALL
        )
        
        # st.write(new_diagram)
        
        html_code = f"""
                    <html>
                      <body>
                        <pre class="mermaid">
                        {new_diagram[0]}
                        </pre>
                        <script type="module">
                          import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
                          mermaid.initialize({{ startOnLoad: true, 'theme': '{theme}' }});
                        </script>
                      </body>
                    </html>
                    """

        html_code = html_code.replace("{{", "{")
        html_code = html_code.replace("}}", "}")
        components.html(
            html_code,
            height=window_hight,
            scrolling=True
        )
        
        # prepare prompt
        prompt = prompt_template.replace("{html_text}", st.session_state.text_content)
        prompt = prompt.replace("{diagram}", new_diagram[0])
        
    dc_output = {
        'refined_diagram': new_diagram[0], 
        'justification': justification[0],
        'raw_output': response_text
    }
        
    return dc_output
        

        
        
        
    
    
    
def select_diagram(   
    ls_diagrams
):
    
    num_of_diagrams = len(ls_diagrams)
    html_text = st.session_state.text_content
    modelId = st.session_state.model_reflect
    system_prompt = st.session_state.prompt_template_system
    
    prompt = f"""
    Here is a given text for you to reference for the following task. Read it carefully because it is necessary for the task that you will have to solve. 

    <text>
    {html_text}
    </text>

    Think step by step and select the most informative and visually pleasing Mermaid diagram among the following {num_of_diagrams}.
    The candidate Mermaid diagrams are included inside XML tags, along with their corresponding index number. 
    The most informative Mermaid diagram should be the one that includes the most details from the text and displays it in an easy to understand way.
    Someone who would only view the selected Mermaid diagram, should understand the main concepts of the text, without having to read it.
    Explain which of the Mermaid diagrams is the most informative and provide its index inside <selected_index></selected_index> XML tags.
    """
    
    # adding the candidate mermaid diagrams and their indices
    for i,diagram in enumerate(ls_diagrams):
        prompt += ("\n\n<diagram " + str(i) + ">\n")
        prompt += diagram["processed_graph"]
        prompt += ("\n</diagram " + str(i) + ">\n")  
    
    
    response = st.session_state.bedrock_runtime.converse(
        modelId=modelId,
        inferenceConfig={
            "temperature": 0.1,  # be more factual
            "maxTokens": 2048,
            "topP": 1,
        },
        system=[
            {
                "text": system_prompt
            }
        ],
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
    )
    response_text = response["output"]["message"]["content"][0]["text"]

    # parse index from the completion
    indx_selected = re.findall(
        r"<selected_index>(.*?)</selected_index>", 
        response_text, 
        re.DOTALL
    )
    indx_selected = int(indx_selected[0])
    
    dc_output = {'indx_selected': indx_selected, 'raw_output': response_text}

    return dc_output

    
    
    


def generate_diagram_variants(
    url,
    prompt,
    number_of_diagrams=1,
    orientation="LR", # "LR" or "TD"
    repeat_on_error=True,
    max_tokens_to_sample=500,
    temperature=0.9,
    top_k=250,
    top_p=1,
):
    
    start_time = time.time()
    
    with st.status("Generating " + str(number_of_diagrams) + " visual gist variants at once...", expanded=True) as status:
        
        ls_diagrams = []
        ls_valid_indx = []
        key_count = 0
        modelId = st.session_state.model_generate
        system_prompt = st.session_state.prompt_template_system

        while len(ls_valid_indx) == 0:
            # generate graphs
            response = st.session_state.bedrock_runtime.converse(
                    modelId=modelId,
                    inferenceConfig={
                        "temperature": temperature,
                        "maxTokens": max_tokens_to_sample,
                        "topP": top_p,
                        # "topK": top_k,
                    },
                    system=[
                        {
                            "text": system_prompt
                        }
                    ],
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "text": prompt
                                }
                            ]
                        }
                    ],
                )
            response_text = response["output"]["message"]["content"][0]["text"]

            # parse graphs from the completion
            ls_str_mermaid_graph = find_between(
                response_text, 
                "<mermaid>", 
                "</mermaid>"
            )

            # check validity of graphs and extract details
            for d,str_mermaid_graph in enumerate(ls_str_mermaid_graph):
                graph_validity = check_graph_validity(
                        standardize_graph(str_mermaid_graph),
                    )
                if graph_validity is True:
                    ls_valid_indx.append(d)
                    dc_output = {}
                    dc_output["raw"] = response_text
                    dc_output["graph"] = str_mermaid_graph
                    dc_output["processed_graph"] = standardize_graph(str_mermaid_graph)
                    dc_output["valid"] = graph_validity
                    ls_diagrams.append(dc_output)

                    display_diagram(
                        dc_diagram=dc_output, 
                        webpage_title=st.session_state.webpage_title, 
                        iteration=d+1,
                        theme=st.session_state.selectbox_color
                    )
                else:
                    st.write("Variant " + str(d) + " is not valid!")
            if len(ls_valid_indx) == 0:
                st.write("No valid candidate was found. Regenerating...")
               
        duration = time.time() - start_time
        status.update(label="Visual gist completed! (in " + str(round(duration,1)) + " sec)", state="complete", expanded=True)
    return ls_diagrams





def generate_diagram(
    url,
    prompt,
    number_of_diagrams=1,
    orientation="LR", # "LR" or "TD"
    repeat_on_error=True,
    max_tokens_to_sample=500,
    temperature=0.9,
    top_k=250,
    top_p=1,
):
    
    start_time = time.time()
    
    with st.status("Generating " + str(number_of_diagrams) + " visual gists...", expanded=True) as status:
        
        ls_diagrams=[]
        key_count = 0
        modelId = st.session_state.model_generate
        system_prompt = st.session_state.prompt_template_system

        for d in range(number_of_diagrams):

            # generate graph
            attempt = 1
            graph_error = True
            while graph_error == True:
                key_count += 1
                st.write("Generating variation " + str(d+1) + " out of " + str(number_of_diagrams) + " (attempt " + str(attempt) + ")")
                
                response = st.session_state.bedrock_runtime.converse(
                    modelId=modelId,
                    inferenceConfig={
                        "temperature": temperature,
                        "maxTokens": max_tokens_to_sample,
                        "topP": top_p,
                        # "topK": top_k,
                    },
                    system=[
                        {
                            "text": system_prompt
                        }
                    ],
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "text": prompt
                                }
                            ]
                        }
                    ],
                )
                response_text = response["output"]["message"]["content"][0]["text"]

                # parse graphs from the completion
                ls_mermaid_graph = find_between(
                    response_text, 
                    "<mermaid>", 
                    "</mermaid>"
                )
                str_mermaid_graph = ls_mermaid_graph[0]
                graph_validity = check_graph_validity(
                    standardize_graph(str_mermaid_graph),
                )

                if repeat_on_error is True:
                    graph_error = not graph_validity
                    attempt += 1
                    if graph_error is True:
                        st.write("Graph has errors! Reattempting...")
                else:
                    graph_error = False

            # log outputs
            dc_output = {}
            dc_output["raw"] = response_text
            dc_output["graph"] = str_mermaid_graph
            dc_output["processed_graph"] = standardize_graph(str_mermaid_graph)
            dc_output["valid"] = graph_validity
            ls_diagrams.append(dc_output)
            
            display_diagram(
                dc_diagram=dc_output, 
                webpage_title=st.session_state.webpage_title,
                iteration=d+1,
                theme=st.session_state.selectbox_color
            )
    
        duration = time.time() - start_time
        status.update(
            label="Visual gist completed! (in " + str(round(duration,1)) + " sec)", 
            state="complete", 
            expanded=True
        )
    return ls_diagrams




def text_url_changed():
    if st.session_state.text_url != "":
        try:
            html_text = get_html_text(
                st.session_state.text_url, 
                postprocess=False, 
                print_text=False
            )
            st.session_state.text_raw = ""  # deactivate the raw text input
        except Exception as e:
            st.write(str(e))
            html_text = ""
        st.session_state.text_content = html_text
        
    else:
        st.session_state.text_content = None
        
        
        
def text_raw_changed():
    if st.session_state.text_raw != "":
        st.session_state.text_content = st.session_state.text_raw
        st.session_state.text_url = ""  # deactivate the URL input
    else:
        st.session_state.text_content = None

        
def model_generate_changed():
    st.session_state.model_generate = st.session_state.dc_available_model_ids[st.session_state.selectbox_model_generate]
 
def model_reflect_changed():
    st.session_state.model_reflect = st.session_state.dc_available_model_ids[st.session_state.selectbox_model_reflect]


#----------------------------------------------------------- setting up environment

if 'bedrock_runtime' not in st.session_state:
    st.session_state.bedrock_runtime = bedrock.get_bedrock_client(
        assumed_role = os.environ.get("BEDROCK_ASSUME_ROLE", None),
        region = os.environ.get("AWS_DEFAULT_REGION", None),
        runtime = True
    )
if 'webpage_title' not in st.session_state:
    st.session_state.webpage_title = ""

if "dc_available_model_ids" not in st.session_state:
    st.session_state.dc_available_model_ids = {
        "Claude Haiku 3": "anthropic.claude-3-haiku-20240307-v1:0",
        "Claude Haiku 3.5": "anthropic.claude-3-5-haiku-20241022-v1:0",
        "Claude Sonnet 3": "anthropic.claude-3-sonnet-20240229-v1:0",
        "Claude Sonnet 3.5": "anthropic.claude-3-5-sonnet-20240620-v1:0",
        "Claude Sonnet 3.5 v2":  "anthropic.claude-3-5-sonnet-20241022-v2:0",
         "Nova Pro":  "amazon.nova-pro-v1:0"
    }

if "ls_available_models" not in st.session_state:
    models = st.session_state.dc_available_model_ids.keys()
    st.session_state.ls_available_models = list(models)

# if "ls_available_llms" not in st.session_state:
#     client = bedrock.get_bedrock_client(
#         assumed_role = os.environ.get("BEDROCK_ASSUME_ROLE", None),
#         region = os.environ.get("AWS_DEFAULT_REGION", None),
#         runtime = False
#     )
#     response = client.list_foundation_models(
#         byOutputModality='TEXT'
#     )
#     models = response["modelSummaries"]
#     st.session_state.ls_available_llms = [models[i]["modelId"] for i in range(len(models)) if models[i]["modelLifecycle"]["status"] == "ACTIVE"]
#     # st.session_state.dc_available_model_ids = {models[i]["modelName"]: models[i]["modelId"] for i in range(len(models)) if models[i]["modelLifecycle"]["status"] == "ACTIVE"}
#     # st.write(models)

if 'model_generate' not in st.session_state:
    st.session_state.model_generate = "anthropic.claude-3-sonnet-20240229-v1:0"
    
if 'model_reflect' not in st.session_state:
    st.session_state.model_reflect = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    
if 'text_content' not in st.session_state:
    st.session_state.text_content = None
    
if 'diagrams' not in st.session_state:
    st.session_state.diagrams = []
    
if 'prompt_template_system' not in st.session_state:
    st.session_state.prompt_template_system = """
    You are a wise professor who can read any document, break it down to its essentials, and explain it visually to anyone, using Mermaid graphs.
    """
    
if 'prompt_template_variants' not in st.session_state:
    st.session_state.prompt_template_variants = """         
    Here is a given text for you to reference for the following task. Read it carefully because it is necessary for the task that you will have to solve. 

    <text>
    {html_text}
    </text>

    <task>
    Summarize the given text and provide the summary inside <summary> tags. 
    Then convert the summary to {how_many} diagrams using Mermaid notation. 
    All Mermaid diagrams should capture the main gist of the summary. 
    Someone who would only view the Mermaid diagrams, should understand the gist of the summary. 
    The Mermaid diagrams should follow all the correct notation rules and should compile without any syntax errors.
    Use the following specifications for the generated Mermaid diagrams:
    </task>

    <specifications>
    1. Use different colors, node shapes (e.g. rectangle, circle, rhombus, hexagon, trapezoid, parallelogram etc.), and subgraphs to represent different concepts in the given text.
    2. If you are using subgraphs, each subgraph should have its own indicative name inside quotes. 
    3. Use "links with text" to indicate actions, relationships or influence between a source nodes and destination nodes.
    4. The orientation of each of the {how_many} Mermaid diagrams should be {orientation}.
    5. Include each of the {how_many} Mermaid diagrams inside <mermaid> </mermaid> tags.
    6. Use only information from within the given text. Don't make up new information.
    </specifications>
    """
    
    
# if 'prompt_template_single' not in st.session_state:
#     st.session_state.prompt_template_single = """             
#     Here is a given text for you to reference for the following task. Read it carefully because it is necessary for the task that you will have to solve. 

#     <text>
#     {html_text}
#     </text>

#     <task>
#     Summarize the given text and provide the summary inside <summary> tags. 
#     The summary should capture the main points, concepts and entities of the given text, without too many low-level details. 
#     Then convert the summary to a diagram using Mermaid notation. 
#     Use the following specifications for the generated Mermaid diagram:
#     </task>

#     <specifications>
#     1. The Mermaid diagram should follow all the correct notation rules and should compile without any syntax errors.
#     2. Use different colors, node shapes (e.g. rectangle, circle, rhombus, hexagon, trapezoid, parallelogram etc.), and subgraphs to represent different concepts and entities in the given text.
#     3. If you are using subgraphs, each subgraph should have its own indicative name inside quotes. 
#     4. Use "links with text" to indicate actions, relationships or influence between a source nodes and destination nodes.
#     5. The orientation of the Mermaid diagram should be {orientation}.
#     6. The Mermaid diagram should be visually pleasing, easy to understand and not overly complicated.
#     7. Use only information from within the given text. Don't make up new information.
#     8. Include the Mermaid diagram inside <mermaid> </mermaid> tags.
#     9. Before the output, check the result for any errors. 
#     </specifications>
#     """    

    
if 'prompt_template_single' not in st.session_state:
    st.session_state.prompt_template_single = """             
    Here is a given text for you to reference for the following task. Read it carefully because it is necessary for the task that you will have to solve. 

    <text>
    {html_text}
    </text>

    <task>
    Summarize the given text and provide the summary inside <summary> tags. 
    Then convert the summary to a visually pleasing diagram using Mermaid notation. 
    The diagram should capture the main gist of the summary, without too many low-level details. 
    Someone who would only view the Mermaid diagram, should understand the gist of the summary. 
    The Mermaid diagram should follow all the correct notation rules and should compile without any syntax errors.
    Use the following specifications for the generated Mermaid diagram:
    </task>

    <specifications>
    1. Use different colors, node shapes (e.g. rectangle, circle, rhombus, hexagon, trapezoid, parallelogram etc.), and subgraphs to represent different concepts and entities in the given text.
    2. If you are using subgraphs, each subgraph should have its own indicative name inside quotes. 
    3. Use "links with text" to indicate actions, relationships or influence between a source nodes and destination nodes.
    4. The orientation of the Mermaid diagram should be {orientation}.
    5. Include the Mermaid diagram inside <mermaid> </mermaid> tags.
    6. Do not write anything after the </mermaid> tag.
    7. Use only information from within the given text. Don't make up new information.
    8. Before the output, check the result for any errors. 
    </specifications>
    """
    

#-------------------------------------------------------------------------------------------------------
#----------------------------------------------------------- streamlit UI ------------------------------
#-------------------------------------------------------------------------------------------------------

st.set_page_config(layout="wide")
st.header('Visual Gist')
st.subheader('Automatic generation of visual summaries using GenAI')
st.markdown("One image is a 1000 words! This app puts this saying in to practice. It captures the text of a webpage, and it generates a **visual graph representing the summary of the text**. Taking a glance at this 'Visual Gist', will help you understand the main content without having to actually read the whole webpage.")

col1, col2 = st.columns(2)



#------------- COL1

with col1:

    with st.container(border=True):
        st.subheader("Parameters & Prompt")

        tab_parameters, tab_webpage_text, tab_prompt_template, tab_prompt = st.tabs(
            [
                "Inputs", 
                "Text", 
                "Prompt template", 
                "Prompt"
            ]
        )

        with tab_parameters:
            
            with st.container(border=True):
                st.markdown("##### Input text") 
                st.text_input(
                    label='Text from a webpage URL:', 
                    key='text_url',
                    placeholder='Paste the URL of a webpage from which you want to generate a visual gist diagram',
                    on_change=text_url_changed
                )
                
                st.write("or")
                
                st.text_area(
                    label="Raw text:",
                    key="text_raw",
                    placeholder='Paste any raw text from which you want to generate a visual gist diagram',
                    on_change=text_raw_changed,
                    height=50
                )

            with st.container(border=True):
                st.markdown("##### Prompt parameters") 
                ccol0, ccol1, ccol2 = st.columns(3)

                with ccol0:
                    with st.container(border=True):
                        st.markdown("**Generation**") 
                        st.number_input(
                            label='Number of diagrams to generate', 
                            key="input_number_of_diagrams",
                            min_value=1,
                            max_value=10,
                            step=1,
                            value=1
                        )
                        st.selectbox(
                            label='Technique', 
                            key='selectbox_technique',
                            options=('Generate separately', 'Generate together'),
                            index=0
                        )
                        st.checkbox(
                            'Repeat on error',
                            value=True,
                            key='checkbox_repeat',
                        )
                        st.selectbox(
                            label='Model', 
                            key='selectbox_model_generate',
                            options=(st.session_state.ls_available_models),
                            index=2,
                            on_change=model_generate_changed
                        )
                        
                with ccol1:  
                    with st.container(border=True):
                        st.markdown("**Appearance**") 
                        st.selectbox(
                            label='Orientation', 
                            key='selectbox_orientation',
                            options=('LR', 'RL', 'TD', 'BT'),
                            index=0
                        )
                        st.selectbox(
                            label='Color Theme', 
                            key='selectbox_color',
                            options=('default', 'neutral', 'dark', 'forest'),
                            index=0
                        )
                        st.markdown(" \n\n\n\n\n\n")
                        
                with ccol2:  
                    with st.container(border=True):
                        st.markdown("**Reflection**") 
                        st.checkbox(
                            'Select the best diagram',
                            value=True,
                            key='checkbox_select_diag',
                        )
                        st.checkbox(
                            'Refine diagram',
                            value=True,
                            key='checkbox_refine_diag',
                        )
                        # st.selectbox(
                        #     label='Approach', 
                        #     key='selectbox_approach',
                        #     options=('Select best diagram', 'Select & refine best diagram'),
                        #     index=0
                        # )
                        st.number_input(
                            label='Number of reflection cycles', 
                            key="input_number_cycles",
                            min_value=1,
                            max_value=10,
                            step=1,
                            value=3
                        )
                        st.selectbox(
                            label='Model', 
                            key='selectbox_model_reflect',
                            options=(st.session_state.ls_available_models),
                            index=3,
                            on_change=model_reflect_changed
                        )

            with st.container(border=True):
                st.markdown("##### LLM parameters") 
                st.slider(
                    'Max tokens',
                    min_value=1, 
                    max_value=2048, 
                    value=2048,
                    step=1,
                    key='slider_max_tokens',
                )
                st.slider(
                    'Temperature (creativity)',
                    min_value=0.0, 
                    max_value=1.0, 
                    value=0.15,
                    step=0.01,
                    key='slider_temperature',
                )
                # st.slider(
                #     'Top K',
                #     min_value=0, 
                #     max_value=500, 
                #     value=250,
                #     step=1,
                #     key='slider_top_k',
                # )
                st.slider(
                    'Top P',
                    min_value=0.0, 
                    max_value=1.0, 
                    value=1.0,
                    step=0.01,
                    key='slider_top_p',
                )
                
        with tab_webpage_text:
            if st.session_state.text_content is None:
                st.markdown("No webpage URL has been provided in the Parameters tab!") 
            elif st.session_state.text_content == "":
                st.markdown("There was a problem extracting text from the webpage!")
            else:
                st.markdown(st.session_state.text_content)                
        
        with tab_prompt_template:
            if st.session_state.selectbox_technique == 'Generate separately':
                st.text(st.session_state.prompt_template_single)
            else:
                st.text(st.session_state.prompt_template_variants)

        with tab_prompt:
            if st.session_state.text_content is None:
                st.markdown("No webpage URL has been provided in the Parameters tab!") 
            elif st.session_state.text_content == "":
                st.markdown("There was a problem extracting text from the webpage!")
            else:
                orientation = st.session_state.selectbox_orientation
                number_of_diagrams = st.session_state.input_number_of_diagrams

                # preparing prompt
                if st.session_state.selectbox_technique == 'Generate separately':
                    prompt = st.session_state.prompt_template_single  # start from prompt template
                else:
                    prompt = st.session_state.prompt_template_variants  # start from prompt template

                prompt = prompt.replace("{html_text}", st.session_state.text_content)
                prompt = prompt.replace("{orientation}", orientation)
                prompt = prompt.replace("{how_many}", str(number_of_diagrams))
                
                st.text_area(
                    label="Customize the prompt as needed:",
                    value=prompt,
                    key="text_prompt",
                    height=600
                )

        
#------------- COL2

with col2:
    
    with st.container(border=True):
        st.subheader("Visual gist")

        if (st.session_state.text_content is None) | (st.session_state.text_content == ""):
            button_disabled = True
        else:
            button_disabled = False

        if st.button(
                label='Generate visual gist',
                key='button_generate',
                disabled=button_disabled,
            ):
            
            if st.session_state.selectbox_technique == 'Generate separately':
                # individual graphs
                ls_diagrams = generate_diagram(
                    url=st.session_state.text_url,
                    prompt=st.session_state.text_prompt,
                    number_of_diagrams=st.session_state.input_number_of_diagrams,
                    orientation=st.session_state.selectbox_orientation,
                    repeat_on_error=st.session_state.checkbox_repeat,
                    max_tokens_to_sample=st.session_state.slider_max_tokens,
                    temperature=st.session_state.slider_temperature,
                    top_p=st.session_state.slider_top_p,
                )
            else:
                # variants and selecting the best
                ls_diagrams = generate_diagram_variants(
                    url=st.session_state.text_url,
                    prompt=st.session_state.text_prompt,
                    number_of_diagrams=st.session_state.input_number_of_diagrams,
                    orientation=st.session_state.selectbox_orientation,
                    repeat_on_error=st.session_state.checkbox_repeat,
                    max_tokens_to_sample=st.session_state.slider_max_tokens,
                    temperature=st.session_state.slider_temperature,
                    top_p=st.session_state.slider_top_p,
                )
                
            
            #------
            
            
            if st.session_state.checkbox_select_diag == True:
                st.markdown("""---""") 
                st.write("Selecting the best among " + str(str(len(ls_diagrams))) + " diagrams...")
        
                if len(ls_diagrams) > 1:
                    dc_selection = select_diagram(ls_diagrams)
                    selected_diagram = ls_diagrams[dc_selection["indx_selected"]]
                    selected_diagram["justification"] = dc_selection["raw_output"]
                else:
                    selected_diagram = ls_diagrams[0]
                    selected_diagram["justification"] = "This is the only available diagram"

                display_variants(
                    diagram = selected_diagram,
                    webpage_title=st.session_state.webpage_title, 
                    theme=st.session_state.selectbox_color
                )
            else:
                selected_diagram = ls_diagrams[0]
                selected_diagram["justification"] = "This is the only available diagram"

                
            if st.session_state.checkbox_refine_diag == True:
                st.markdown("""---""") 
                st.write("Refining diagram...")
        
                refined_diagram = refine_diagram(
                    diagram=selected_diagram["processed_graph"], 
                    iterations=st.session_state.input_number_cycles
                )

                
                
            
            
            

                
            
