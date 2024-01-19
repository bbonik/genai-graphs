import streamlit as st
# import streamlit.components.v1 as components
from mycomponent import mycomponent
from streamlit_javascript import st_javascript
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
import base64
import bedrock
import time
import os
import json
import numpy as np
from IPython.display import Image
import datetime



#----------------------------------------------------------- helper functions

# return the text from an html page
def get_html_text(url, postprocess=False, print_text=False):
    request = Request(url , headers={'User-Agent': 'Mozilla/5.0'})
    html = urlopen(request).read()
    soup = BeautifulSoup(html, features="html.parser")
    # kill all script and style elements
    for script in soup(["script", "style"]):
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
def find_between( s, first, last ):
    try:
        start = s.index( first ) + len( first )
        end = s.index( last, start )
        return s[start:end]
    except ValueError:
        return ""

def render_graph(graph, show_link=False):
    graphbytes = graph.encode("utf8")
    base64_bytes = base64.b64encode(graphbytes)
    base64_string = base64_bytes.decode("ascii")
    url_rendering = "https://mermaid.ink/img/" + base64_string
    if show_link is True:
        print(url_rendering)
    rendered_graph = Image(url=url_rendering)
    
    return rendered_graph


    
    
# def check_graph_validity(graph):
#     graphbytes = graph.encode("utf8")
#     base64_bytes = base64.b64encode(graphbytes)
#     base64_string = base64_bytes.decode("ascii")
#     url = "https://mermaid.ink/img/" + base64_string
#     req = Request(url, headers={'User-Agent' : "Magic Browser"})
    
#     flag_valid = True
#     try: 
#         con = urlopen(req)
#     except:
#         flag_valid = False
    
#     return flag_valid


def check_graph_validity(graph):
    
    js_code = f'''
    <html>
      <body>
        <script type="module">
        
          // ----------------------------------------------------
          // Just copy/paste these functions as-is:

          function sendMessageToStreamlitClient(type, data) {{
            var outData = Object.assign({{
              isStreamlitMessage: true,
              type: type,
            }}, data);
            window.parent.postMessage(outData, "*");
          }}

          function init() {{
            sendMessageToStreamlitClient("streamlit:componentReady", {{ apiVersion: 1 }});
          }}

          function setFrameHeight(height) {{
            sendMessageToStreamlitClient("streamlit:setFrameHeight", {{ height: height }});
          }}

          // The `data` argument can be any JSON-serializable value.
          function sendDataToPython(data) {{
            sendMessageToStreamlitClient("streamlit:setComponentValue", data);
          }}

          // ----------------------------------------------------
          // Now modify this part of the code to fit your needs:
        
        
          init();
        
          import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";
          let textStr = "{graph}";
          let valid = "True";
          try{{
            await mermaid.parse(textStr);
          }}
          catch(err){{
            valid = "False";
          }}
          
          
          // Function to send error value to Streamlit
          sendDataToPython({{
              value: valid,
              dataType: "json",
            }});

        </script>
      </body>
    </html>
    '''
    # js_code = js_code.replace("MERMAID_GRAPH", graph)  # substitute the mermaid graph
    js_code = js_code.replace("{{", "{")
    js_code = js_code.replace("}}", "}")
    
    st.markdown("```" + js_code)
    
    # out = components.html(
    #     js_code,
    #     height=1,
    #     width=1,
    # )
    
    
    value = mycomponent(my_input_value="graph TB\na-->b")
    st.write("Received", value)
    

    return value








def check_graph_validity2(graph):
    
    js_code = f"""
                <html>
                  <body>
                    <pre class="mermaid">
                    {graph}
                    </pre>
                    <script type="module">
                      import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
                      mermaid.initialize({{ startOnLoad: false }});
                      
                      let valid = "True";
                      try{{
                        await mermaid.run({{suppressErrors: true }})
                      }}
                      catch(err){{
                        valid = "False";
                      }}
                      parent.window.valid = valid;
                    </script>
                  </body>
                </html>
                """

    # js_code = js_code.replace("MERMAID_GRAPH", graph)  # substitute the mermaid graph
    js_code = js_code.replace("{{", "{")
    js_code = js_code.replace("}}", "}")
    
    # run the html code
    components.html(
        js_code,
        height=500,
        # width=1,
    )

    
    while True:
        valid = st_javascript('parent.window.valid')
        if (valid == "True") | (valid == "False"):
            break
        time.sleep(5)    

    return valid


    
def standardize_graph(graph):
    # double to single
    graph = graph.replace("((", "(")
    graph = graph.replace("))", ")")
    graph = graph.replace("{{", "{")
    graph = graph.replace("}}", "}")
    graph = graph.replace("[[", "[")
    graph = graph.replace("]]", "]")
    graph = graph.replace("||", "|")
    
    graph = graph.replace("([", "(")
    graph = graph.replace("])", ")")
    graph = graph.replace("[(", "[")
    graph = graph.replace(")]", "]")
    graph = graph.replace("({", "(")
    graph = graph.replace("})", ")")
    graph = graph.replace("{(", "{")
    graph = graph.replace(")}", "}")
    graph = graph.replace("{[", "{")
    graph = graph.replace("]}", "}")
    graph = graph.replace("[{", "[")
    graph = graph.replace("}]", "]")
    
    # remove quotes if they exist (to be added later)
    graph = graph.replace('("', '(')
    graph = graph.replace('")', ')')
    graph = graph.replace('["', '[')
    graph = graph.replace('"]', ']')
    graph = graph.replace('{"', '{')
    graph = graph.replace('"}', '}')
    
    # add quotes
    graph = graph.replace('(', '("')
    graph = graph.replace(')', '")')
    graph = graph.replace('[', '["')
    graph = graph.replace(']', '"]')
    graph = graph.replace('{', '{"')
    graph = graph.replace('}', '"}')
    
    # # remove spaces in arrows (to be added later)
    # graph = graph.replace(' -->', '-->')
    # graph = graph.replace('--> ', '-->')
    # graph = graph.replace('-->', ' --> ')
    
    # remove unsafe caracters for base64 encoding
    graph = graph.replace('/', '')
    graph = graph.replace('+', '')
    
    return graph




def linearize_graph(graph):
    
    lines = graph.splitlines()
    
    new_lines = []
    for line in lines:
        striped_line = line.strip()  # remove space before and after
        # if len(striped_line) > 5:  # only longer lines
        if (striped_line != "") & (striped_line != " "):
            if striped_line[-1] != ";":
                striped_line += ";"
            new_lines.append(striped_line)
    
    graph = "".join(new_lines)  # all in one line
    
    return graph




def generate_diagram(
    url,
    prompt,
    number_of_diagrams=1,
    kind="flowchart", # "mindmap" or "flowchart"
    orientation="LR", # "LR" or "TD"
    repeat_on_error=True,
    mermaid_context=True,
    max_tokens_to_sample=500,
    temperature=0.9,
    top_k=250,
    top_p=1,
):
    
    
    with st.status("Generating visual gist...", expanded=True) as status:
        
        ls_diagrams=[]

        for d in range(number_of_diagrams):

            # setting parameters 
            body = json.dumps(
                {
                    "prompt": prompt, 
                    "max_tokens_to_sample": max_tokens_to_sample,
                    "temperature": temperature,
                    "top_k": top_k,
                    "top_p": top_p,
                    "stop_sequences": ["\n\nHuman:"]
                }
            )
            modelId = "anthropic.claude-v2:1"
            accept = "application/json"
            contentType = "application/json"

            # generate graph
            attempt = 1
            graph_error = True
            while graph_error == True:
                st.write("Generating diagram " + str(d+1) + " out of " + str(number_of_diagrams) + " (attempt " + str(attempt) + ")")
                response = st.session_state.bedrock_runtime.invoke_model(
                    body=body, 
                    modelId=modelId, 
                    accept=accept, 
                    contentType=contentType
                )
                response_body = json.loads(response.get("body").read())

                str_mermaid_graph = find_between(
                    response_body.get("completion"), 
                    "<mermaid>", 
                    "</mermaid>"
                )
                graph_validity = check_graph_validity(
                    linearize_graph(str_mermaid_graph)
                    # str_mermaid_graph
                )

                if repeat_on_error is True:
                    graph_error = not graph_validity
                    attempt += 1
                    if graph_error is True:
                        st.write("Graph has errors! Reattempting...")
                        # st.write(standardize_graph(str_mermaid_graph))
                else:
                    graph_error = False

            # log outputs
            dc_output = {}
            dc_output["raw"] = response_body.get("completion")
            dc_output["graph"] = str_mermaid_graph
            dc_output["standardized_graph"] = standardize_graph(str_mermaid_graph)
            dc_output["valid"] = graph_validity
            ls_diagrams.append(dc_output)

        status.update(label="Diagram complete!", state="complete", expanded=False)
    return ls_diagrams




def generate_diagram_simple(
    url,
    prompt,
    kind="flowchart", # "mindmap" or "flowchart"
    orientation="LR", # "LR" or "TD"
    mermaid_context=True,
    max_tokens_to_sample=500,
    temperature=0.9,
    top_k=250,
    top_p=1,
):

    # setting parameters 
    body = json.dumps(
        {
            "prompt": prompt, 
            "max_tokens_to_sample": max_tokens_to_sample,
            "temperature": temperature,
            "top_k": top_k,
            "top_p": top_p,
            "stop_sequences": ["\n\nHuman:"]
        }
    )
    modelId = "anthropic.claude-v2:1"
    accept = "application/json"
    contentType = "application/json"

    # generate graph
    st.write("Generating diagram")
    response = st.session_state.bedrock_runtime.invoke_model(
        body=body, 
        modelId=modelId, 
        accept=accept, 
        contentType=contentType
    )
    response_body = json.loads(response.get("body").read())

    str_mermaid_graph = find_between(
        response_body.get("completion"), 
        "<mermaid>", 
        "</mermaid>"
    )
    
    st.write(str_mermaid_graph)
    
    # graph="""
    #  flowchart LR
    #      A[Use Case?] --> B{Built-in algorithm?}
    #      B --> |Yes| C[Use pre-built]
    #      B --> |No| D[Custom model?]
    #      D --> |Yes| E{Need custom<br/>packages?}
    #      E --> |No| F[Use pre-built]
    #      E --> |Yes| G{Pre-built supports<br/>requirements.txt?}
    #      G --> |Yes| H[Use requirements.txt]
    #      G --> |No| I[Extend pre-built]
    #      D --> |No| J[Build custom container]
    #  """
    
    graph="""
    flowchart LR 

    subgraph "Google Cloud" 
        direction TB 
        A["Training Data Indemnity"] 
        B["Generated Output Indemnity"] 
    end

    subgraph "Covers"
        direction TB 
        C["Claims related to<br>Google's use of<br>training data"]
        D["Claims related to<br>content generated<br>by customers"]
    end

    A --> C
    B --> D

    class A,B fill:#bbf,stroke:#333,stroke-width:2px
    class C,D fill:#f9f,stroke:#333,stroke-width:2px
    """
    
    
    st.write("-----------")
    st.write(graph)
    
    # log outputs
    dc_output = {}
    dc_output["raw"] = response_body.get("completion")
    # dc_output["graph"] = str_mermaid_graph
    dc_output["graph"] = graph
    dc_output["standardized_graph"] = standardize_graph(str_mermaid_graph)

    return dc_output


#----------------------------------------------------------- setting up environment

if 'bedrock_runtime' not in st.session_state:
    st.session_state.bedrock_runtime = bedrock.get_bedrock_client(
        assumed_role = os.environ.get("BEDROCK_ASSUME_ROLE", None),
        region = os.environ.get("AWS_DEFAULT_REGION", None),
        runtime = True
    )
if 'webpage_title' not in st.session_state:
    st.session_state.webpage_title = ""
    
if 'button_pressed' not in st.session_state:
    st.session_state.button_pressed = False

if 'prompt_template' not in st.session_state:
    st.session_state.prompt_template = """\n\nHuman:              
    You are an amazing professor who can read any webpage, break it down to its essentials, and explain it visually to anyone using Mermaid graphs. 
                
    Here is a revision of the Mermaid notation and a given webpage text for you to reference for the following task. Read both of them carefully because they are necessary for the task that you will have to solve. 
                
    <mermaid_notation>
    {context_mermaid_notation}
    </mermaid_notation>

    <text>
    {html_text}
    </text>

    <task>
    Summarize the given text and provide the summary inside <summary> tags. 
    Then convert the summary to a {kind} using Mermaid notation. 
    The {kind} should capture the main gist of the summary, without too many low-level details. 
    Someone who would only view the Mermaid {kind}, should understand the gist of the summary. 
    The Mermaid {kind} should follow all the correct notation rules and should compile without any syntax errors.
    Use the following specifications for the generated Mermaid {kind}:
    </task>

    <specifications>
    1. Use different colors, shapes (e.g. rectangle, circle, rhombus, hexagon, trapezoid, parallelogram etc.) and subgraphs to represent different concepts in the given text.
    2. If you are using subgraphs, each subgraph should have its own indicative name within quotes.
    3. The orientation of the Mermaid {kind} should be {orientation}.
    4. Any text inside parenthesis (), square brackets [], curly brackets {}, or bars ||, should be inside quotes "".
    5. Include the Mermaid {kind} inside <mermaid> </mermaid> tags.
    6. Do not write anything after the </mermaid> tag.
    7. Use only information from within the given text. Don't make up new information.
    8. Before the output, check the result for any errors. 
    </specifications>
    \n\nAssistant:
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
                "Parameters", 
                "Webpage text", 
                "Prompt template", 
                "Prompt"
            ]
        )

        with tab_parameters:
            st.text_input(
                label='Webpage URL', 
                key='text_url',
                placeholder='Paste the URL of a webpage which you want to generate a visual gist diagram'
            )

            with st.container(border=True):
                st.markdown("##### Prompt parameters") 
                col0, col1 = st.columns(2)

                with col0:
                    st.number_input(
                        label='Number of diagrams to generate', 
                        key='input_number_of_diagrams',
                        min_value=1,
                        max_value=10,
                        step=1,
                        value=1
                    )
                    st.checkbox(
                        'Repeat on error',
                        value=False,
                        key='checkbox_repeat',
                    )
                    st.checkbox(
                        'Include Mermaid context',
                        value=True,
                        key='checkbox_mermaid_context',
                    )
                
                with col1:
                    st.selectbox(
                        label='Type of diagram', 
                        key='selectbox_kind',
                        options=('flowchart', 'mindmap'),
                        index=0
                    )
                    st.selectbox(
                        label='Orientation', 
                        key='selectbox_orientation',
                        options=('LR', 'RL', 'TD', 'BT'),
                        index=0
                    )
                
            with st.container(border=True):
                st.markdown("##### LLM parameters") 
                st.slider(
                    'Max tokens to sample',
                    min_value=1, 
                    max_value=2048, 
                    value=500,
                    step=1,
                    key='slider_max_tokens',
                )
                st.slider(
                    'Temperature (creativity)',
                    min_value=0.0, 
                    max_value=1.0, 
                    value=0.9,
                    step=0.01,
                    key='slider_temperature',
                )
                st.slider(
                    'Top K',
                    min_value=0, 
                    max_value=500, 
                    value=250,
                    step=1,
                    key='slider_top_k',
                )
                st.slider(
                    'Top P',
                    min_value=0.0, 
                    max_value=1.0, 
                    value=1.0,
                    step=0.01,
                    key='slider_top_p',
                )
                
        with tab_webpage_text:
            if st.session_state.text_url != "":
                try:
                    html_text = get_html_text(
                        st.session_state.text_url, 
                        postprocess=False, 
                        print_text=False
                    )
                    st.markdown(html_text)
                except Exception as e:
                    st.markdown("There was a problem accessing the webpage!")
                    st.markdown(str(e))
            else:
                st.markdown("No webpage URL has been provided in the Parameters tab!") 
        
        with tab_prompt_template:
            st.text(st.session_state.prompt_template)

        with tab_prompt:

            if st.session_state.text_url != "":

                kind = st.session_state.selectbox_kind
                orientation = st.session_state.selectbox_orientation
                
                if st.session_state.checkbox_mermaid_context is True:
                    context_mermaid_notation = get_html_text(
                        url="https://mermaid.js.org/syntax/flowchart.html", 
                        postprocess=False, 
                        print_text=False
                    )
                
                html_text = get_html_text(
                    url=st.session_state.text_url, 
                    postprocess=False, 
                    print_text=False
                )
                
                # preparing prompt
                prompt = st.session_state.prompt_template  # start from prompt template
                if st.session_state.checkbox_mermaid_context is False:
                    prompt = prompt.replace(
                        prompt[prompt.find("<mermaid_notation>"):prompt.find("</mermaid_notation>")+21], 
                        ""
                    )
                prompt = prompt.replace("{context_mermaid_notation}", context_mermaid_notation)
                prompt = prompt.replace("{html_text}", html_text)
                prompt = prompt.replace("{kind}", kind)
                prompt = prompt.replace("{orientation}", orientation)
                
            
                st.text_area(
                    label="Customize the prompt as needed:",
                    value=prompt,
                    key="text_prompt",
                    height=600
                )
            else:
                st.text("No webpage URL has been provided in the Parameters tab!")

                
    # experimental
    with st.container(border=False):
        
        if st.session_state.text_url != "":
            # st.write("Sleeping...")
            # time.sleep(20)
            
            graph="""
            flowchart LR
                A[Use Case?] --> B{Built-in algorithm?}
                B --> |Yes| C[Use pre-built]
                B --> |No| D[Custom model?]
                D --> |Yes| E{Need custom<br/>packages?}
                E --> |No| F[Use pre-built]
                E --> |Yes| G{Pre-built supports<br/>requirements.txt?}
                G --> |Yes| H[Use requirements.txt]
                G --> |No| I[Extend pre-built]
                D --> |No| J[Build custom container]
            """
            
#             graph="""
#             flowchart LR 

#             subgraph "Google Cloud" 
#                 direction TB 
#                 A["Training Data Indemnity"] 
#                 B["Generated Output Indemnity"] 
#             end

#             subgraph "Covers"
#                 direction TB 
#                 C["Claims related to<br>Google's use of<br>training data"]
#                 D["Claims related to<br>content generated<br>by customers"]
#             end

#             A --> C
#             B --> D
#             """
            graph = linearize_graph(graph)
            return_value = check_graph_validity(graph)   
            # return_value = check_graph_validity2(graph)   
            st.markdown(f"Valid graph: {return_value}")

        
#         if st.session_state.text_url != "":
            
#             st.write("Generating....")

#             dc_diagram = generate_diagram_simple(
#                 url=st.session_state.text_url,
#                 prompt=st.session_state.text_prompt,
#                 kind=st.session_state.selectbox_kind,
#                 orientation=st.session_state.selectbox_orientation,
#                 mermaid_context=st.session_state.checkbox_mermaid_context,
#                 max_tokens_to_sample=st.session_state.slider_max_tokens,
#                 temperature=st.session_state.slider_temperature,
#                 top_k=st.session_state.slider_top_k,
#                 top_p=st.session_state.slider_top_p,
#             )
#             st.write(dc_diagram["graph"])
#             graph = linearize_graph(dc_diagram["graph"])
#             st.write("evaluating")
#             return_value = check_graph_validity(graph)
#             st.markdown(f"Valid graph: {return_value}")
                
                
                
#------------- COL2

with col2:
    
    # # experimental 
    # with st.container(border=True):
    #     components.html(
    #         str(st.session_state.test_html),
    #         height=400,
    #         scrolling=True
    #     )
    
    
    with st.container(border=True):
        st.subheader("Visual gist")

        if st.session_state.text_url == "":
            button_disabled = True
        else:
            button_disabled = False

        if st.button(
                label='Generate visual gist',
                key='button_generate',
                disabled=button_disabled,
            ):
            
            st.session_state.button_pressed = True
            
#             ls_diagrams = generate_diagram(
#                 url=st.session_state.text_url,
#                 prompt=st.session_state.text_prompt,
#                 number_of_diagrams=st.session_state.input_number_of_diagrams,
#                 kind=st.session_state.selectbox_kind,
#                 orientation=st.session_state.selectbox_orientation,
#                 repeat_on_error=st.session_state.checkbox_repeat,
#                 mermaid_context=st.session_state.checkbox_mermaid_context,
#                 max_tokens_to_sample=st.session_state.slider_max_tokens,
#                 temperature=st.session_state.slider_temperature,
#                 top_k=st.session_state.slider_top_k,
#                 top_p=st.session_state.slider_top_p,
#             )
            
            
#             for i in range(len(ls_diagrams)):
                
#                 with st.container(border=True):
#                     st.markdown("##### Visual gist " + str(i+1))

#                     tab_image, tab_st_graph, tab_graph, tab_raw = st.tabs(
#                         [
#                             "Image", 
#                             "Postprocessed", 
#                             "Original", 
#                             "Raw LLM output"
#                         ]
#                     )

#                     with tab_image:
#                         # if ls_diagrams[i]["valid"] is True:
#                         st.markdown("**" + st.session_state.webpage_title + "**")
                        
#                         html_code = f"""
#                                     <html>
#                                       <body>
#                                         <pre class="mermaid">
#                                         {ls_diagrams[i]["graph"]}
#                                         </pre>
#                                         <script type="module">
#                                           import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
#                                           mermaid.initialize({{ startOnLoad: true }});
#                                         </script>
#                                       </body>
#                                     </html>
#                                     """
                        
#                         html_code = html_code.replace("{{", "{")
#                         html_code = html_code.replace("}}", "}")
#                         components.html(
#                             html_code,
#                             height=400,
#                             scrolling=True
#                         )
                            
#                     with tab_st_graph:
#                         st.markdown("```" + ls_diagrams[i]["standardized_graph"] + "```")
#                     with tab_graph:
#                         st.markdown("```" + ls_diagrams[i]["graph"] + "```")
#                     with tab_raw:
#                         st.markdown(ls_diagrams[i]["raw"])

        else:
            st.session_state.button_pressed = False