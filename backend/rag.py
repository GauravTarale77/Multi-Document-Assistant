import os
from pathlib import Path
from dotenv import load_dotenv

from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    CSVLoader,
    UnstructuredWordDocumentLoader,
    WebBaseLoader,
)

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found")

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

INDEX_DIR = Path("./faiss_index")
INDEX_DIR.mkdir(exist_ok=True)

def get_vectorstore():
    index_path = str(INDEX_DIR)
    if INDEX_DIR.exists() and any(INDEX_DIR.iterdir()):
        return FAISS.load_local(
            index_path, 
            embeddings, 
            allow_dangerous_deserialization=True
        )
    raise ValueError("No documents uploaded yet. Please upload files first.")

def load_documents(file_paths):
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

            documents.extend(loader.load())
            print(f"Loaded {len(loader.load())} pages from {path}")

        except Exception as e:
            print(f"Error loading {path}: {e}")

    return documents

def split_documents(docs):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    return splitter.split_documents(docs)

def process_files(file_paths):
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
    except Exception as e:
        print(f"No existing index or load failed ({e}), creating new...")
        vectorstore = FAISS.from_documents(splits, embeddings)
    
    vectorstore.save_local(index_path)
    print(f"Saved index with {vectorstore.index.ntotal} vectors")
    
    return vectorstore

def process_website(url):
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
        return vectorstore

    except Exception as e:
        print(f"Error processing website: {e}")
        return None

def ask_question(query):
    vectorstore = get_vectorstore()
    
    try:
        from langchain_groq import ChatGroq
        from langchain_core.prompts import ChatPromptTemplate
        
        llm = ChatGroq(
            groq_api_key=GROQ_API_KEY,
            model_name="llama-3.1-8b-instant",
            temperature=0
        )
        retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
        prompt = ChatPromptTemplate.from_template(
            "Answer based on context: {context}\n\nQuestion: {question}"
        )
        
        chain = create_retrieval_chain(retriever, prompt | llm)
        result = chain.invoke({"input": query})
        
        return result["answer"]

    except Exception as e:
        raise RuntimeError(f"Error during QA: {str(e)}")

