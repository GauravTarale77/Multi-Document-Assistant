import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
os.environ['USER_AGENT'] = 'MultiDocResearchAssistant/1.0'

from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    CSVLoader,
    UnstructuredWordDocumentLoader,
    WebBaseLoader,
)

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings 
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in environment")

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

INDEX_DIR = Path("./faiss_index")
INDEX_DIR.mkdir(exist_ok=True)

def get_vectorstore():
    """Load existing FAISS index securely."""
    if not INDEX_DIR.exists() or not any(INDEX_DIR.iterdir()):
        raise ValueError("No documents indexed. Upload files first via process_files() or process_website().")
    
    return FAISS.load_local(
        str(INDEX_DIR), 
        embeddings, 
        allow_dangerous_deserialization=True
    )

def load_documents(file_paths):
    """Load multiple document types."""
    documents = []
    for path in file_paths:
        try:
            if path.endswith(".pdf"):
                loader = PyPDFLoader(path)
            elif path.endswith(".txt"):
                loader = TextLoader(path)
            elif path.endswith(".csv"):
                loader = CSVLoader(path)
            elif path.endswith(".docx"):
                loader = UnstructuredWordDocumentLoader(path)
            else:
                print(f"Unsupported file type: {path}")
                continue

            docs = loader.load()
            documents.extend(docs)
            print(f"Loaded {len(docs)} pages from {path}")

        except Exception as e:
            print(f"Error loading {path}: {e}")
    return documents

def split_documents(docs):
    """Split documents into overlapping chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    return splitter.split_documents(docs)

def process_files(file_paths):
    """Process and index local files."""
    docs = load_documents(file_paths)
    if not docs:
        print("No documents loaded")
        return None

    splits = split_documents(docs)
    print(f"Split into {len(splits)} chunks")

    index_path = str(INDEX_DIR)
    
    try:
        vectorstore = FAISS.load_local(
            index_path, 
            embeddings, 
            allow_dangerous_deserialization=True
        )
        print("Loaded existing index, adding new documents...")
        vectorstore.add_documents(splits)
    except:
        print("Creating new index...")
        vectorstore = FAISS.from_documents(splits, embeddings)
    
    vectorstore.save_local(index_path)
    print(f"Saved index with {vectorstore.index.ntotal} vectors")
    return vectorstore

def process_website(url):
    """Process and index website content."""
    try:
        loader = WebBaseLoader(url)
        docs = loader.load()

        if not docs:
            return None

        splits = split_documents(docs)

        index_path = str(INDEX_DIR)
        try:
            vectorstore = FAISS.load_local(
                index_path, 
                embeddings, 
                allow_dangerous_deserialization=True
            )
            vectorstore.add_documents(splits)
        except:
            vectorstore = FAISS.from_documents(splits, embeddings)
        
        vectorstore.save_local(index_path)
        print(f"Indexed website with {vectorstore.index.ntotal} vectors")
        return vectorstore

    except Exception as e:
        print(f"Error processing website: {e}")
        return None

def ask_question(query):
    """Answer questions using modern LCEL RAG chain (v1.2 compatible)."""
    vectorstore = get_vectorstore()
    
    llm = ChatGroq(
        groq_api_key=GROQ_API_KEY,
        model_name="llama-3.1-8b-instant",
        temperature=0
    )

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)
    
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    
    template = """Answer the question based only on the following context:
{context}
    
Question: {question}
Answer:"""
    
    prompt = ChatPromptTemplate.from_template(template)
    
    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    
    return chain.invoke(query)
