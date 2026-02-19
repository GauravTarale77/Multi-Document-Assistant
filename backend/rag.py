import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

load_dotenv()
os.environ['USER_AGENT'] = 'MultiDocResearchAssistant/1.0'

def _lazy_import(module_name):
    """Import modules only when needed (Render memory fix)"""
    imports = {
        'loaders': lambda: __import__('langchain_community.document_loaders'),
        'text_splitters': lambda: __import__('langchain_text_splitters'),
        'faiss': lambda: __import__('langchain_community.vectorstores.faiss'),
        'embeddings': lambda: __import__('langchain_huggingface'),
        'groq': lambda: __import__('langchain_groq'),
        'prompts': lambda: __import__('langchain_core.prompts'),
        'runnables': lambda: __import__('langchain_core.runnables'),
        'parsers': lambda: __import__('langchain_core.output_parsers'),
    }
    return imports[module_name]()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in environment")

INDEX_DIR = Path("./faiss_index")
INDEX_DIR.mkdir(exist_ok=True)

_embeddings_cache = {}
_vectorstore_cache = {}

def get_embeddings():
    """Lazy load embeddings (90MB) on first use only."""
    if 'embeddings' not in _embeddings_cache:
        print("🔄 Loading embedding model (first time only)...")
        embeddings_mod = _lazy_import('embeddings')
        _embeddings_cache['embeddings'] = embeddings_mod.HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': False}
        )
        print("✅ Embedding model loaded and cached")
    return _embeddings_cache['embeddings']

def get_vectorstore():
    """Load FAISS index - BULLETPROOF VERSION."""
    from langchain_community.vectorstores import FAISS
    
    if not INDEX_DIR.exists() or not any(INDEX_DIR.iterdir()):
        print("❌ No index directory")
        raise ValueError("No documents indexed. Upload files first.")
    
    embeddings = get_embeddings()
    
    try:
        print(f"📂 Loading index from {INDEX_DIR}")
        vectorstore = FAISS.load_local(
            str(INDEX_DIR), 
            embeddings, 
            allow_dangerous_deserialization=True
        )
        print(f"✅ SUCCESS: {vectorstore.index.ntotal} vectors loaded!")
        return vectorstore
    except Exception as e:
        print(f"❌ FAISS load failed: {e}")
        print("🔄 Recreating index...")
        return None


def load_documents(file_paths: List[str]):
    """Load multiple document types - FIXED imports."""
    from langchain_community.document_loaders import (
        PyPDFLoader, TextLoader, CSVLoader
    )
    
    documents = []
    for path in file_paths:
        try:
            if path.endswith(".pdf"):
                loader = PyPDFLoader(path)
            elif path.endswith((".txt", ".md")):
                loader = TextLoader(path)
            elif path.endswith(".csv"):
                loader = CSVLoader(path)
            else:
                print(f"⚠️ Skipping unsupported: {path}")
                continue

            docs = loader.load()
            documents.extend(docs)
            print(f"📄 Loaded {len(docs)} pages from {path}")

        except Exception as e:
            print(f"❌ Error loading {path}: {e}")
    return documents


def split_documents(docs):
    """Split documents into overlapping chunks."""
    splitters_mod = _lazy_import('text_splitters')
    splitter = splitters_mod.RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    return splitter.split_documents(docs)

def process_files(file_paths: List[str]):
    """Process and index local files - DIRECT IMPORTS ONLY."""
    from langchain_community.vectorstores import FAISS
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    
    docs = load_documents(file_paths)
    if not docs:
        print("❌ No documents loaded")
        return None

    # Split documents
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    splits = splitter.split_documents(docs)
    print(f"✂️ Split into {len(splits)} chunks")

    # Get embeddings
    embeddings = get_embeddings()
    
    # Create or load FAISS index
    index_path = str(INDEX_DIR)
    try:
        print("🔄 Loading existing index...")
        vectorstore = FAISS.load_local(
            index_path, 
            embeddings, 
            allow_dangerous_deserialization=True
        )
        print("✅ Loaded existing index, adding new documents...")
        vectorstore.add_documents(splits)
    except:
        print("🆕 Creating new index...")
        vectorstore = FAISS.from_documents(splits, embeddings)
    
    # Save index
    vectorstore.save_local(index_path)
    print(f"💾 Saved index with {vectorstore.index.ntotal} vectors")
    return vectorstore

def process_website(url: str):
    """Process website - CORRECT WebBaseLoader params."""
    from langchain_community.document_loaders import WebBaseLoader
    from langchain_community.vectorstores import FAISS
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    import requests
    
    try:
        print(f"🌐 Fetching website: {url}")
        
        # Pre-check URL accessibility
        response = requests.get(
            url, 
            timeout=15, 
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        response.raise_for_status()
        print(f"✅ Website OK: {len(response.text)} chars")
        
        # ✅ FIXED: Use header_template (NOT headers)
        loader = WebBaseLoader(
            url,
            header_template={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            requests_per_second=0.5
        )
        docs = loader.load()

        if not docs or not docs[0].page_content.strip():
            print("❌ No content extracted")
            return None

        print(f"📄 Loaded: {len(docs)} docs")
        
        # Process chunks
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        splits = splitter.split_documents(docs)
        print(f"✂️ Split into {len(splits)} chunks")
        
        embeddings = get_embeddings()
        index_path = str(INDEX_DIR)
        
        try:
            vectorstore = FAISS.load_local(
                index_path, embeddings, allow_dangerous_deserialization=True
            )
            vectorstore.add_documents(splits)
            print("✅ Added to existing index")
        except:
            vectorstore = FAISS.from_documents(splits, embeddings)
            print("🆕 Created new index")
        
        vectorstore.save_local(index_path)
        print(f"🌐 TOTAL: {vectorstore.index.ntotal} vectors")
        return vectorstore

    except requests.exceptions.Timeout:
        print("⏰ Website timeout")
        return None
    except requests.exceptions.ConnectionError:
        print("🔌 Connection failed")
        return None
    except Exception as e:
        print(f"❌ Website failed: {str(e)[:100]}")
        return None



def ask_question(query: str) -> str:
    """Answer questions using modern LCEL RAG chain - DIRECT IMPORTS."""
    from langchain_groq import ChatGroq
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.runnables import RunnablePassthrough
    from langchain_core.output_parsers import StrOutputParser
    
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
