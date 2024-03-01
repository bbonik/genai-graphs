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
        ls_valid_diagrams,
        indx_best_diagram,
        raw_selection_output,
        webpage_title, 
        window_hight=500
    ):

    ls_other_variants = [ls_valid_diagrams[i] for i in range(len(ls_valid_diagrams)) if i != indx_best_diagram]  # without best digram

    with st.container(border=True):

        ls_tabs = [
                "Visual gist", 
                "Mermaid code", 
                "Raw variants",
                "Raw selection",
            ]
        for i in range(len(ls_valid_diagrams) - 1):
            ls_tabs.append("Variant " + str(i+1))
            
        
        for i,current_tab in enumerate(st.tabs(ls_tabs)):
            with current_tab:
                
                if i == 0:  # display selected variant
                    st.markdown("**" + webpage_title + "**")
                    html_code = f"""
                                <html>
                                  <body>
                                    <pre class="mermaid">
                                    {ls_valid_diagrams[indx_best_diagram]["processed_graph"]}
                                    </pre>
                                    <script type="module">
                                      import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
                                      mermaid.initialize({{ startOnLoad: true }});
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
                    
                if i == 1:  # mermaid code
                    st.markdown("```" + ls_valid_diagrams[indx_best_diagram]["processed_graph"] + "```")
                    
                if i == 2:  # raw llm variant outputs
                    st.markdown(ls_valid_diagrams[indx_best_diagram]["raw"])
                    
                if i == 3:  # raw llm selection output
                    st.markdown(raw_selection_output)
                
                if i > 3:  # raw llm selection output
                    html_code = f"""
                                <html>
                                  <body>
                                    <pre class="mermaid">
                                    {ls_other_variants[0]["processed_graph"]}
                                    </pre>
                                    <script type="module">
                                      import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
                                      mermaid.initialize({{ startOnLoad: true }});
                                    </script>
                                  </body>
                                </html>
                                """
                    html_code = html_code.replace("{{", "{")
                    html_code = html_code.replace("}}", "}")
                    components.html(
                        html_code,
                        height=window_hight,
                        scrolling=True,
                    )
                    # st.write(ls_other_variants[0]["processed_graph"])
                    del ls_other_variants[0]




def display_diagram(dc_diagram, webpage_title, iteration, window_hight=500):
    
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
                              mermaid.initialize({{ startOnLoad: true }});
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
    

    
    
def select_diagram(   
    ls_diagrams
):
    
    num_of_diagrams = len(ls_diagrams)
    html_text = st.session_state.text_content
    
    prompt = f"""
    \n\nHuman:              
    Here is a webpage text for you to reference for the following task. Read it carefully because it is necessary for the task that you will have to solve. 

    <text>
    {html_text}
    </text>

    <task>
    Select the most informative Mermaid diagram among the following {num_of_diagrams}.
    The candidate Mermaid diagrams are included inside XML tags, along with their corresponding index number. 
    The most informative Mermaid diagram should capture the main gist of the text. 
    Someone who would only view the Mermaid diagram, should understand the main concepts of the text, without having to read it.
    Select the index of the most informative Mermaid diagram and provide it inside <selected_index></selected_index> XML tags.
    """
    
    for i,diagram in enumerate(ls_diagrams):
        prompt += ("\n\n<diagram " + str(i) + ">\n")
        prompt += diagram["processed_graph"]
        prompt += ("\n</diagram " + str(i) + ">\n")  
    prompt += "\n\nAssistant: The most informative diagram is "

    
    # setting parameters 
    body = json.dumps(
        {
            "prompt": prompt, 
            "max_tokens_to_sample": 512,
            "temperature": 0.1,
            "top_k": 250,
            "top_p": 1,
            "stop_sequences": ["\n\nHuman:"]
        }
    )
    modelId = "anthropic.claude-v2:1"  # "anthropic.claude-instant-v1", "anthropic.claude-v2:1"
    accept = "application/json"
    contentType = "application/json"

    # generate graph

    response = st.session_state.bedrock_runtime.invoke_model(
        body=body, 
        modelId=modelId, 
        accept=accept, 
        contentType=contentType
    )
    response_body = json.loads(response.get("body").read())
    
    indx_selected = re.findall(
        r"<selected_index>(.*?)</selected_index>", 
        response_body.get("completion"), 
        re.DOTALL
    )
    indx_selected = int(indx_selected[0])

    
    
    dc_output = {'indx_selected': indx_selected, 'raw_output': response_body.get("completion")}

    return dc_output

    
    
    


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
    
    start_time = time.time()
    
    with st.status("Generating " + str(number_of_diagrams) + " visual gist variants...", expanded=True) as status:
        
        ls_diagrams = []
        ls_valid_indx = []
        key_count = 0


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
        modelId = "anthropic.claude-v2:1"  # "anthropic.claude-instant-v1", "anthropic.claude-v2:1"
        accept = "application/json"
        contentType = "application/json"

        # generate graphs
        response = st.session_state.bedrock_runtime.invoke_model(
            body=body, 
            modelId=modelId, 
            accept=accept, 
            contentType=contentType
        )
        response_body = json.loads(response.get("body").read())

        ls_str_mermaid_graph = find_between(
            response_body.get("completion"), 
            "<mermaid>", 
            "</mermaid>"
        )

        for d,str_mermaid_graph in enumerate(ls_str_mermaid_graph):
            
            graph_validity = check_graph_validity(
                    standardize_graph(str_mermaid_graph),
                )
            if graph_validity is True:
                ls_valid_indx.append(d)
                
            # log outputs
            dc_output = {}
            dc_output["raw"] = response_body.get("completion")
            dc_output["graph"] = str_mermaid_graph
            dc_output["processed_graph"] = standardize_graph(str_mermaid_graph)
            dc_output["valid"] = graph_validity
            ls_diagrams.append(dc_output)

            # display_diagram(
            #     dc_diagram=dc_output, 
            #     webpage_title=st.session_state.webpage_title, 
            #     iteration=d+1
            # )
        
        status.update(label="Selecting the best among " + str(str(len(ls_valid_indx))) + " valid variants...", expanded=True)
        
        ls_valid_diagrams = [ls_diagrams[i] for i in ls_valid_indx]
        dc_selection = select_diagram(ls_valid_diagrams)
        
        
        display_variants(
            ls_valid_diagrams = ls_valid_diagrams,
            indx_best_diagram = dc_selection["indx_selected"],
            raw_selection_output = dc_selection["raw_output"],
            webpage_title=st.session_state.webpage_title, 
        )
        
        duration = time.time() - start_time
        status.update(label="Visual gist completed! (in " + str(round(duration,1)) + " sec)", state="complete", expanded=True)
    return ls_diagrams


def text_url_changed():
    if st.session_state.text_url != "":
        try:
            html_text = get_html_text(
                st.session_state.text_url, 
                postprocess=False, 
                print_text=False
            )
        except Exception as e:
            st.write(str(e))
            html_text = ""
        st.session_state.text_content = html_text
        
    else:
        st.session_state.text_content = None


#----------------------------------------------------------- setting up environment

if 'bedrock_runtime' not in st.session_state:
    st.session_state.bedrock_runtime = bedrock.get_bedrock_client(
        assumed_role = os.environ.get("BEDROCK_ASSUME_ROLE", None),
        region = os.environ.get("AWS_DEFAULT_REGION", None),
        runtime = True
    )
if 'webpage_title' not in st.session_state:
    st.session_state.webpage_title = ""
    
if 'text_content' not in st.session_state:
    st.session_state.text_content = None    
    
if 'prompt_template' not in st.session_state:
    st.session_state.prompt_template = """\n\nHuman:              
    You are an amazing professor who can read any webpage, break it down to its essentials, and explain it visually to anyone, using Mermaid graphs. 
                
    Here is a revision of the Mermaid notation and a given webpage text for you to reference for the following task. Read both of them carefully because they are necessary for the task that you will have to solve. 
                
    <mermaid_notation>
    {context_mermaid_notation}
    </mermaid_notation>

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
    \n\nAssistant:
    """
    

    
    
if 'mermaid_context' not in st.session_state:
    st.session_state.mermaid_context = """
    Flowcharts Syntax | Mermaid

    SECTION: Basic Syntax ​

    Flowcharts are composed of nodes (geometric shapes) and edges (arrows or lines). The Mermaid code defines how nodes and edges are made and accommodates different arrow types, multi-directional arrows, and any linking to and from subgraphs. 
    If you are using the word "end" in a Flowchart node, capitalize the entire word or any of the letters (e.g., "End" or "END"), or apply this workaround. 
    Typing "end" in all lowercase letters will break the Flowchart. 

    If you are using the letter "o" or "x" as the first letter in a connecting Flowchart node, add a space before the letter or capitalize the letter (e.g., "dev--- ops", "dev---Ops").Typing "A---oB" will create a circle edge.Typing "A---xB" will create a cross edge.

    A node (default) ​
    Example Mermaid code:
    flowchart LR
        id

    A node with text ​
    It is also possible to set text in the box that differs from the id. If this is done several times, it is the last text found for the node that will be used. Also if you define edges for the node later on, you can omit text definitions. The one previously defined will be used when rendering the box.
    Example Mermaid code:
    flowchart LR
        id1[This is the text in the box]

    Unicode text ​
    Use " to enclose the unicode text.
    Example Mermaid code:
    flowchart LR
        id["This ❤ Unicode"]

    Markdown formatting ​
    Use double quotes and backticks "` text `" to enclose the markdown text.
    Example Mermaid code:
    %%{init: {"flowchart": {"htmlLabels": false}} }%%
    flowchart LR
        markdown["`This **is** _Markdown_`"]
        newLines["`Line1
        Line 2
        Line 3`"]
        markdown --> newLines

    Direction ​
    This statement declares the direction of the Flowchart.This declares the flowchart is oriented from top to bottom (TD or TB).
    Example Mermaid code:
    flowchart TD
        Start --> Stop

    This declares the flowchart is oriented from left to right (LR).
    Example Mermaid code:
    flowchart LR
        Start --> Stop

    Possible FlowChart orientations are:
    TB - Top to bottom
    TD - Top-down/ same as top to bottom
    BT - Bottom to top
    RL - Right to left
    LR - Left to right


    SECTION: Node shapes ​

    A node with round edges ​
    Example Mermaid code:
    flowchart LR
        id1(This is the text in the box)

    A stadium-shaped node ​
    Example Mermaid code:
    flowchart LR
        id1([This is the text in the box])

    A node in a subroutine shape ​
    Example Mermaid code:
    flowchart LR
        id1[[This is the text in the box]]

    A node in a cylindrical shape ​
    Example Mermaid code:
    flowchart LR
        id1[(Database)]

    A node in the form of a circle ​
    Example Mermaid code:
    flowchart LR
        id1((This is the text in the circle))

    A node in an asymmetric shape ​
    Example Mermaid code:
    flowchart LR
        id1>This is the text in the box]

    A node (rhombus) ​
    Example Mermaid code:
    flowchart LR
        id1{This is the text in the box}

    A hexagon node ​
    Example Mermaid code:
    flowchart LR
        id1{{This is the text in the box}}

    Parallelogram ​
    Example Mermaid code:
    flowchart TD
        id1[/This is the text in the box/]

    Parallelogram alt ​
    Example Mermaid code:
    flowchart TD
        id1[\This is the text in the box\]

    Trapezoid ​
    Example Mermaid code:
    flowchart TD
        A[/Christmas\]

    Trapezoid alt ​
    Example Mermaid code:
    flowchart TD
        B[\Go shopping/]

    Double circle ​
    Example Mermaid code:
    flowchart TD
        id1(((This is the text in the circle)))

    SECTION: Links between nodes ​
    Nodes can be connected with links/edges. It is possible to have different types of links or attach a text string to a link.

    A link with arrow head ​
    Example Mermaid code:
    flowchart LR
        A-->B

    An open link ​
    Example Mermaid code:
    flowchart LR
        A --- B

    Text on links ​
    Example Mermaid code:
    flowchart LR
        A-- This is the text! ---B

    or

    Example Mermaid code:
    flowchart LR
        A---|This is the text|B

    A link with arrow head and text ​
    Example Mermaid code:
    flowchart LR
        A-->|text|B

    or

    Example Mermaid code:
    flowchart LR
        A-- text -->B

    Dotted link ​
    Example Mermaid code:
    flowchart LR
       A-.->B;

    Dotted link with text ​
    Example Mermaid code:
    flowchart LR
       A-. text .-> B

    Thick link ​
    Example Mermaid code:
    flowchart LR
       A ==> B

    Thick link with text ​
    Example Mermaid code:
    flowchart LR
       A == text ==> B

    An invisible link ​
    This can be a useful tool in some instances where you want to alter the default positioning of a node.
    Example Mermaid code:
    flowchart LR
        A ~~~ B

    Chaining of links ​
    It is possible declare many links in the same line as per below:
    Example Mermaid code:
    flowchart LR
       A -- text --> B -- text2 --> C

    It is also possible to declare multiple nodes links in the same line as per below:

    Example Mermaid code:
    flowchart LR
       a --> b & c--> d

    You can then describe dependencies in a very expressive way. Like the one-liner below:

    Example Mermaid code:
    flowchart TB
        A & B--> C & D

    If you describe the same diagram using the basic syntax, it will take four lines. A word of warning, one could go overboard with this making the flowchart harder to read in markdown form. The Swedish word lagom comes to mind. It means, not too much and not too little. This goes for expressive syntaxes as well.

    Example Mermaid code:
    flowchart TB
        A --> C
        A --> D
        B --> C
        B --> D


    SECTION: New arrow types ​

    There are new types of arrows supported:
    - circle edge
    - cross edge

    Circle edge example ​
    Example Mermaid code:
    flowchart LR
        A --o B

    Cross edge example ​
    Example Mermaid code:
    flowchart LR
        A --x B


    SECTION: Multi directional arrows ​

    There is the possibility to use multidirectional arrows.

    Example Mermaid code:
    flowchart LR
        A o--o B
        B <--> C
        C x--x D

    Minimum length of a link ​
    Each node in the flowchart is ultimately assigned to a rank in the rendered graph, i.e. to a vertical or horizontal level (depending on the flowchart orientation), based on the nodes to which it is linked. By default, links can span any number of ranks, but you can ask for any link to be longer than the others by adding extra dashes in the link definition.In the following example, two extra dashes are added in the link from node B to node E, so that it spans two more ranks than regular links:

    Example Mermaid code:
    flowchart TD
        A[Start] --> B{Is it?}
        B -->|Yes| C[OK]
        C --> D[Rethink]
        D --> B
        B ---->|No| E[End]

    Note Links may still be made longer than the requested number of ranks by the rendering engine to accommodate other requests.

    When the link label is written in the middle of the link, the extra dashes must be added on the right side of the link. The following example is equivalent to the previous one:

    Example Mermaid code:
    flowchart TD
        A[Start] --> B{Is it?}
        B -- Yes --> C[OK]
        C --> D[Rethink]
        D --> B
        B -- No ----> E[End]


    SECTION: Special characters that break syntax ​

    It is possible to put text within quotes in order to render more troublesome characters. As in the example below:
    Example Mermaid code:
    flowchart LR
        id1["This is the (text) in the box"]

    Entity codes to escape characters ​
    It is possible to escape characters using the syntax exemplified here.
    Example Mermaid code:
    flowchart LR
        A["A double quote:#quot;"] --> B["A dec char:#9829;"]

    Numbers given are base 10, so # can be encoded as #35;. It is also supported to use HTML character names.


    SECTION: Subgraphs ​

    subgraph title
        graph definition
    end

    An example below:

    Example Mermaid code:
    flowchart TB
        c1-->a2
        subgraph one
        a1-->a2
        end
        subgraph two
        b1-->b2
        end
        subgraph three
        c1-->c2
        end

    You can also set an explicit id for the subgraph.
    Example Mermaid code:
    flowchart TB
        c1-->a2
        subgraph ide1 [one]
        a1-->a2
        end

    flowcharts ​
    With the graphtype flowchart it is also possible to set edges to and from subgraphs as in the flowchart below.
    Example Mermaid code:
    flowchart TB
        c1-->a2
        subgraph one
        a1-->a2
        end
        subgraph two
        b1-->b2
        end
        subgraph three
        c1-->c2
        end
        one --> two
        three --> two
        two --> c2

    Direction in subgraphs ​
    With the graphtype flowcharts you can use the direction statement to set the direction which the subgraph will render like in this example.
    Example Mermaid code:
    flowchart LR
      subgraph TOP
        direction TB
        subgraph B1
            direction RL
            i1 -->f1
        end
        subgraph B2
            direction BT
            i2 -->f2
        end
      end
      A --> TOP --> B
      B1 --> B2

    Limitation ​
    If any of a subgraph's nodes are linked to the outside, subgraph direction will be ignored. Instead the subgraph will inherit the direction of the parent graph:
    Example Mermaid code:
    flowchart LR
        subgraph subgraph1
            direction TB
            top1[top] --> bottom1[bottom]
        end
        subgraph subgraph2
            direction TB
            top2[top] --> bottom2[bottom]
        end
        %% ^ These subgraphs are identical, except for the links to them:

        %% Link *to* subgraph1: subgraph1 direction is maintained
        outside --> subgraph1
        %% Link *within* subgraph2:
        %% subgraph2 inherits the direction of the top-level graph (LR)
        outside ---> top2


    SECTION: Markdown Strings ​

    The "Markdown Strings" feature enhances flowcharts and mind maps by offering a more versatile string type, which supports text formatting options such as bold and italics, and automatically wraps text within labels.

    Example Mermaid code:%%{init: {"flowchart": {"htmlLabels": false}} }%%
    flowchart LR
    subgraph "One"
      a("`The **cat**
      in the hat`") -- "edge label" --> b{{"`The **dog** in the hog`"}}
    end
    subgraph "`**Two**`"
      c("`The **cat**
      in the hat`") -- "`Bold **edge label**`" --> d("The dog in the hog")
    end

    Formatting:
    For bold text, use double asterisks (**) before and after the text.
    For italics, use single asterisks (*) before and after the text.
    With traditional strings, you needed to add <br> tags for text to wrap in nodes. However, markdown strings automatically wrap text when it becomes too long and allows you to start a new line by simply using a newline character instead of a <br> tag.

    This feature is applicable to node labels, edge labels, and subgraph labels.


    SECTION: Comments ​

    Comments can be entered within a flow diagram, which will be ignored by the parser. Comments need to be on their own line, and must be prefaced with %% (double percent signs). Any text after the start of the comment to the next newline will be treated as a comment, including any flow syntax

    Example Mermaid code:
    flowchart LR
    %% this is a comment A -- text --> B{node}
       A -- text --> B -- text2 --> C


    SECTION: Styling and classes ​

    Styling links ​
    It is possible to style links. For instance, you might want to style a link that is going backwards in the flow. As links have no ids in the same way as nodes, some other way of deciding what style the links should be attached to is required. Instead of ids, the order number of when the link was defined in the graph is used, or use default to apply to all links. In the example below the style defined in the linkStyle statement will belong to the fourth link in the graph:

    linkStyle 3 stroke:#ff3,stroke-width:4px,color:red;

    It is also possible to add style to multiple links in a single statement, by separating link numbers with commas:

    linkStyle 1,2,7 color:blue;

    Styling line curves ​
    It is possible to style the type of curve used for lines between items, if the default method does not meet your needs. Available curve styles include basis, bumpX, bumpY, cardinal, catmullRom, linear, monotoneX, monotoneY, natural, step, stepAfter, and stepBefore.
    In this example, a left-to-right graph uses the stepBefore curve style:

    %%{ init: { 'flowchart': { 'curve': 'stepBefore' } } }%%
    graph LR

    Styling a node ​
    It is possible to apply specific styles such as a thicker border or a different background color to a node.
    Example Mermaid code:
    flowchart LR
        id1(Start)-->id2(Stop)
        style id1 fill:#f9f,stroke:#333,stroke-width:4px
        style id2 fill:#bbf,stroke:#f66,stroke-width:2px,color:#fff,stroke-dasharray: 5 5

    Classes ​
    More convenient than defining the style every time is to define a class of styles and attach this class to the nodes that should have a different look.
    A class definition looks like the example below:    
    classDef className fill:#f9f,stroke:#333,stroke-width:4px;

    Also, it is possible to define style to multiple classes in one statement:    
    classDef firstClassName,secondClassName font-size:12pt;

    Attachment of a class to a node is done as per below:    
    class nodeId1 className;

    It is also possible to attach a class to a list of nodes in one statement:    
    class nodeId1,nodeId2 className;

    A shorter form of adding a class is to attach the classname to the node using the :::operator as per below:
    Example Mermaid code:
    flowchart LR
        A:::someclass --> B
        classDef someclass fill:#f96

    This form can be used when declaring multiple links between nodes:
    Example Mermaid code:
    flowchart LR
        A:::foo & B:::bar --> C:::foobar
        classDef foo stroke:#f00
        classDef bar stroke:#0f0
        classDef foobar stroke:#00f

    Default class ​
    If a class is named default it will be assigned to all classes without specific class definitions.    
    classDef default fill:#f9f,stroke:#333,stroke-width:4px;


    SECTION: Basic support for fontawesome ​

    It is possible to add icons from fontawesome.

    The icons are accessed via the syntax fa:#icon class name#.
    Example Mermaid code:
    flowchart TD
        B["fa:fa-twitter for peace"]
        B-->C[fa:fa-ban forbidden]
        B-->D(fa:fa-spinner)
        B-->E(A fa:fa-camera-retro perhaps?)

    Mermaid supports Font Awesome if the CSS is included on the website. Mermaid does not have any restriction on the version of Font Awesome that can be used.


    SECTION: Graph declarations with spaces between vertices and link and without semicolon ​

    In graph declarations, the statements also can now end without a semicolon. After release 0.2.16, ending a graph statement with semicolon is just optional. So the below graph declaration is also valid along with the old declarations of the graph.

    A single space is allowed between vertices and the link. However there should not be any space between a vertex and its text and a link and its text. The old syntax of graph declaration will also work and hence this new feature is optional and is introduced to improve readability.

    Below is the new declaration of the graph edges which is also valid along with the old declaration of the graph edges.
    Example Mermaid code:
    flowchart LR
        A[Hard edge] -->|Link text| B(Round edge)
        B --> C{Decision}
        C -->|One| D[Result one]
        C -->|Two| E[Result two]
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
                placeholder='Paste the URL of a webpage which you want to generate a visual gist diagram',
                on_change=text_url_changed
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
                        value=False,
                        key='checkbox_mermaid_context',
                    )
                
                with col1:
                    st.selectbox(
                        label='Technique', 
                        key='selectbox_kind',
                        options=('Generate variants & select', 'Generate only'),
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
                    value=1024,
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
            if st.session_state.text_content is None:
                st.markdown("No webpage URL has been provided in the Parameters tab!") 
            elif st.session_state.text_content == "":
                st.markdown("There was a problem extracting text from the webpage!")
            else:
                st.markdown(st.session_state.text_content)                
        
        with tab_prompt_template:
            st.text(st.session_state.prompt_template)

        with tab_prompt:
            if st.session_state.text_content is None:
                st.markdown("No webpage URL has been provided in the Parameters tab!") 
            elif st.session_state.text_content == "":
                st.markdown("There was a problem extracting text from the webpage!")
            else:
                orientation = st.session_state.selectbox_orientation
                number_of_diagrams = st.session_state.input_number_of_diagrams
                
                if st.session_state.checkbox_mermaid_context is True:
                    # context_mermaid_notation = get_html_text(
                    #     url="https://mermaid.js.org/syntax/flowchart.html", 
                    #     postprocess=False, 
                    #     print_text=False
                    # )
                    context_mermaid_notation = st.session_state.mermaid_context
                else:
                    context_mermaid_notation = ""

                # preparing prompt
                prompt = st.session_state.prompt_template  # start from prompt template
                if st.session_state.checkbox_mermaid_context is False:
                    prompt = prompt.replace(
                        prompt[prompt.find("<mermaid_notation>"):prompt.find("</mermaid_notation>")+21], 
                        ""
                    )
                prompt = prompt.replace("{context_mermaid_notation}", context_mermaid_notation)
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
            
            ls_diagrams = generate_diagram(
                url=st.session_state.text_url,
                prompt=st.session_state.text_prompt,
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
            

                
            
