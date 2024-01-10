__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA
#from utils.ui import message_func, user_message_func
from ui import message_func, user_message_func
import streamlit as st
import tempfile
import os

# Title
st.title("💬 Genieverse Agent")
st.caption("🚀 If you ask anything about the education stuff, AI agent would answer your question")
# st.image("ui/genieverse_title.png")    # GIF format is available

INITIAL_MESSAGE = [
    {
        "role": "assistant",
        "content": "How can I help you?"
    }
]

# Sidebar
with st.sidebar:
    # Input OpenAI key
    openai_key = st.text_input('OpenAI API Key', type="password")
    # Upload PDF
    uploaded_file = st.file_uploader("Upload PDF", type=['pdf'])

# Add a reset button in sidebar
if st.sidebar.button("Reset Chat"):
    for key in st.session_state.keys():
        del st.session_state[key]
    st.session_state["messages"] = INITIAL_MESSAGE
    st.session_state["history"] = []

# Define style
with open("ui/styles.md", "r") as styles_file:
    styles_content = styles_file.read()
st.write(styles_content, unsafe_allow_html=True)
    
def pdf_to_document(uploaded_file):
    temp_dir = tempfile.TemporaryDirectory()
    temp_filepath = os.path.join(temp_dir.name, uploaded_file.name)
    with open(temp_filepath, "wb") as f:
        f.write(uploaded_file.getvalue())
    loader = PyPDFLoader(temp_filepath)
    pages = loader.load_and_split()
    return pages

# 업로드 되면 동작하는 코드
if uploaded_file is not None:
    pages = pdf_to_document(uploaded_file)

    # Split
    text_splitter = RecursiveCharacterTextSplitter(
        # Set a really small chunk size, just to show.
        chunk_size = 300,
        chunk_overlap  = 20,
        length_function = len,
        is_separator_regex = False,
    )
    texts = text_splitter.split_documents(pages)

    # Embedding
    embeddings_model = OpenAIEmbeddings(openai_api_key=openai_key)

    # load it into Chroma
    db = Chroma.from_documents(texts, embeddings_model)

    # Initialize the chat messages history
    if "messages" not in st.session_state.keys():
        st.session_state["messages"] = INITIAL_MESSAGE
    if "history" not in st.session_state:
        st.session_state["history"] = []

    for message in st.session_state.messages:
        message_func(
            message["content"],
            True if message["role"] == "user" else False
        )

    rule = '''
    모르는 것은 모른다고 해. 
    '''
    if prompt := st.chat_input():
        st.session_state.messages.append({"role": "user", "content": rule+prompt})
        message_func(
            prompt, True
        )

        llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0, openai_api_key=openai_key)
        qa_chain = RetrievalQA.from_chain_type(llm, retriever=db.as_retriever())
        result = qa_chain({"query": rule+prompt})
        st.session_state.messages.append({"role": "assistant", "content": result['result']})
        message_func(
            result['result'],
            False
        )
