import streamlit as st
import streamlit.components.v1 as components
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
import base64
import bedrock
import time
import os
import json
import numpy as np
from IPython.display import Image



#----------------------------------------------------------- helper functions

# return the text from an html page
def get_html_text(url, postprocess=False, print_text=False):
    html = urlopen(url).read()
    soup = BeautifulSoup(html, features="html.parser")
    # kill all script and style elements
    for script in soup(["script", "style"]):
        script.extract()    # rip it out
    # get text
    text = soup.get_text()
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


    
    
def check_graph_validity(graph):
    graphbytes = graph.encode("utf8")
    base64_bytes = base64.b64encode(graphbytes)
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




def generate_diagram(
    url,
    number_of_diagrams=1,
    kind="flowchart", # "mindmap" or "flowchart"
    orientation="LR", # "LR" or "TD"
    repeat_on_error = True,
    mermaid_context=True,
    max_tokens_to_sample=500,
    temperature=0.9,
    top_k=250,
    top_p=1,
):
    
    
    with st.status("Generating visual gist...", expanded=True) as status:
        
        ls_diagrams=[]

        for d in range(number_of_diagrams):
            # Getting context
            html_text = context_mermaid_notation = get_html_text(
                url=url, 
                postprocess=False, 
                print_text=False
            )
            if mermaid_context is True:
                context_mermaid_notation = get_html_text(
                    url="https://mermaid.js.org/syntax/flowchart.html", 
                    postprocess=False, 
                    print_text=False
                )
            else:
                context_mermaid_notation = ""


            # Defining prompt
            prompt = f"""\n\nHuman: 
            Here is a text for you to reference for the following task:
            <text>
            {html_text}
            </text>

            Task: Summarize the given text and provide the summary inside <summary> tags. 
            Then convert the summary to a {kind} using Mermaid notation. 

            <mermaid_notation>
            {context_mermaid_notation}
            </mermaid_notation>

            The {kind} should capture the main gist of the summary, without too many low-level details. 
            Someone who would only view the Mermaid {kind}, should understand the gist of the summary. 
            The Mermaid {kind} should follow all the correct notation rules and should compile without any errors.
            Use the following specifications for the generated Mermaid {kind}:

            <specifications>
            1. Use different colors, shapes or groups to represent different concepts in the given text.
            2. The orientation of the Mermaid {kind} should be {orientation}.
            3. Any text inside parenthesis (), square brackets [], curly brackets {{}}, or bars ||, should be inside quotes "".
            4. Include the Mermaid {kind} inside <mermaid> tags.
            5. Do not write anything after the </mermaid> tag.
            6. Use only information from within the given text. Don't make up new information.
            </specifications>

            \n\nAssistant:
            """
            prompt = prompt.replace("{{}}", "{}")

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
            modelId = "anthropic.claude-v2:1"  # change this to use a different version from the model provider
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
                    standardize_graph(str_mermaid_graph)
                )

                if repeat_on_error is True:
                    graph_error = not graph_validity
                    attempt += 1
                    if graph_error is True:
                        st.write("Graph has errors! Reattempting...")
                        # st.write(standardize_graph(str_mermaid_graph))
                    else:
                        st.write("Graph was successfully generated!")
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


#----------------------------------------------------------- setting up environment

if 'bedrock_runtime' not in st.session_state:
    st.session_state.bedrock_runtime = bedrock.get_bedrock_client(
        assumed_role = os.environ.get("BEDROCK_ASSUME_ROLE", None),
        region = os.environ.get("AWS_DEFAULT_REGION", None),
        runtime = True
    )
    


#----------------------------------------------------------- streamlit UI

st.set_page_config(layout="wide")
st.header('Automatic generation of Visual Gist using GenAI')
st.markdown("This app will understand the content of a webpage, and it will generate a graph representing the summary of this content. This graph is the a visual representation of the gist of the webpage.")

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
                        value=True,
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
                        options=('LR', 'TD'),
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
                html_text = get_html_text(
                    st.session_state.text_url, 
                    postprocess=False, 
                    print_text=False
                )
                st.text(html_text)
            else:
                st.text("No webpage URL has been provided in the Parameters tab!") 
        
        with tab_prompt_template:
            prompt_template = f"""\n\nHuman: 
            Here is a text for you to reference for the following task:
            <text>
            {{html_text}}
            </text>

            Task: Summarize the given text and provide the summary inside <summary> tags. 
            Then convert the summary to a {{kind}} using Mermaid notation. 

            <mermaid_notation>
            {{context_mermaid_notation}}
            </mermaid_notation>

            The {{kind}} should capture the main gist of the summary, without too many low-level details. 
            Someone who would only view the Mermaid {{kind}}, should understand the gist of the summary. 
            The Mermaid {{kind}} should follow all the correct notation rules and should compile without any errors.
            Use the following specifications for the generated Mermaid {{kind}}:

            <specifications>
            1. Use different colors, shapes or groups to represent different concepts in the given text.
            2. The orientation of the Mermaid {{kind}} should be {{orientation}}.
            3. Any text inside parenthesis (), square brackets [], curly brackets {{}}, or bars ||, should be inside quotes "".
            4. Include the Mermaid {{kind}} inside <mermaid> tags.
            5. Do not write anything after the </mermaid> tag.
            6. Use only information from within the given text. Don't make up new information.
            </specifications>
            \n\nAssistant:
            """
            st.text(prompt_template)


        with tab_prompt:

            if st.session_state.text_url != "":

                kind = st.session_state.selectbox_kind
                orientation = st.session_state.selectbox_orientation

                html_text = get_html_text(
                    url=st.session_state.text_url, 
                    postprocess=False, 
                    print_text=False
                )
                
                if st.session_state.checkbox_mermaid_context is True:
                    context_mermaid_notation = get_html_text(
                        url="https://mermaid.js.org/syntax/flowchart.html", 
                        postprocess=False, 
                        print_text=False
                    )
                else:
                    context_mermaid_notation = ""
                

                # prompt 
                prompt = f"""\n\nHuman: 
                Here is a text for you to reference for the following task:
                <text>
                {html_text}
                </text>

                Task: Summarize the given text and provide the summary inside <summary> tags. 
                Then convert the summary to a {kind} using Mermaid notation. 

                <mermaid_notation>
                {context_mermaid_notation}
                </mermaid_notation>

                The {kind} should capture the main gist of the summary, without too many low-level details. 
                Someone who would only view the Mermaid {kind}, should understand the gist of the summary. 
                The Mermaid {kind} should follow all the correct notation rules and should compile without any errors.
                Use the following specifications for the generated Mermaid {kind}:

                <specifications>
                1. Use different colors, shapes or groups to represent different concepts in the given text.
                2. The orientation of the Mermaid {kind} should be {orientation}.
                3. Any text inside parenthesis (), square brackets [], curly brackets {{}}, or bars ||, should be inside quotes "".
                4. Include the Mermaid {kind} inside <mermaid> tags.
                5. Do not write anything after the </mermaid> tag.
                6. Use only information from within the given text. Don't make up new information.
                </specifications>
                \n\nAssistant:
                """

                st.text_area(
                    label="Customize the prompt as needed:",
                    value=prompt,
                    key="text_prompt",
                    height=600
                )
            else:
                st.text("No webpage URL has been provided in the Parameters tab!")

                
                
                
#------------- COL2

with col2:
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
            
            
            
            ls_diagrams = generate_diagram(
                url=st.session_state.text_url,
                number_of_diagrams=st.session_state.input_number_of_diagrams,
                kind=st.session_state.selectbox_kind,
                orientation=st.session_state.selectbox_orientation,
                repeat_on_error=st.session_state.checkbox_repeat,
                mermaid_context=st.session_state.checkbox_mermaid_context,
                max_tokens_to_sample=st.session_state.slider_max_tokens,
                temperature=st.session_state.slider_temperature,
                top_k=st.session_state.slider_top_k,
                top_p=st.session_state.slider_top_p,
            )
            
            
            for i in range(len(ls_diagrams)):
                
                with st.container(border=True):
                    st.markdown("##### Visual gist " + str(i+1))

                    tab_image, tab_st_graph, tab_graph, tab_raw = st.tabs(
                        [
                            "Image", 
                            "Postprocessed", 
                            "Original", 
                            "Raw LLM output"
                        ]
                    )

                    with tab_image:
                        if ls_diagrams[i]["valid"] is True:
                            html_code = f"""
                                        <html>
                                          <body>
                                            <pre class="mermaid">
                                            {ls_diagrams[i]["standardized_graph"]}
                                            </pre>
                                            <script type="module">
                                              import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
                                              mermaid.initialize({{ startOnLoad: true }});
                                            </script>
                                          </body>
                                        </html>
                                        """

                            components.html(
                                html_code,
                                height=400,
                                scrolling=True
                            )
                            
                    with tab_st_graph:
                        st.markdown("```" + ls_diagrams[i]["standardized_graph"] + "```")
                    with tab_graph:
                        st.markdown("```" + ls_diagrams[i]["graph"] + "```")
                    with tab_raw:
                        st.write(ls_diagrams[i]["raw"])