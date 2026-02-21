import os
import shutil
from typing import List
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Request 
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rag import process_files, process_website, ask_question

app = FastAPI(title="Multi-Document Research Assistant", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(500)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=500,
        content={"detail": "Processing timeout - try smaller file (under 10MB)"},
        headers={"Access-Control-Allow-Origin": "*"}
    )

UPLOADS_DIR = Path("./uploads")
UPLOADS_DIR.mkdir(exist_ok=True)
INDEX_DIR = Path("./faiss_index")
INDEX_DIR.mkdir(exist_ok=True)

class URLRequest(BaseModel):
    url: str

class QuestionRequest(BaseModel):
    query: str

@app.get("/")
async def root():
    port = os.getenv("PORT", "8000")
    print(f"🚀 Server LIVE on 0.0.0.0:{port} ✅ Render port ready!")
    return {"message": "✅ Multi-Document RAG Assistant Live!", "status": "ready"}

@app.get("/health")
async def health():
    return {"status": "healthy"}  

@app.get("/status")
async def status():
    """Check if index exists AND vectorstore loads."""
    index_exists = INDEX_DIR.exists() and any(INDEX_DIR.iterdir())
    
    if not index_exists:
        return {"status": "no_documents", "index_exists": False}

    try:
        from rag import get_vectorstore
        vectorstore = get_vectorstore()
        total_vectors = vectorstore.index.ntotal
        return {"status": "ready", "index_exists": True, "vectors": total_vectors}
    except:
        return {"status": "corrupted", "index_exists": True, "error": "Index corrupted"}


@app.post("/upload/")
async def upload_files(files: List[UploadFile] = File(...)):
    for old_file in UPLOADS_DIR.glob("*"):
        old_file.unlink()
    
    file_paths = []
    allowed_extensions = (".pdf", ".txt", ".docx", ".csv")
    
    for i, file in enumerate(files):
        if not file.filename.lower().endswith(allowed_extensions):
            raise HTTPException(status_code=400, detail=f"Only PDF/TXT/DOCX/CSV allowed")
        
        filename = f"{Path(file.filename).stem}_{i:03d}{Path(file.filename).suffix}"
        temp_path = UPLOADS_DIR / filename
        
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_paths.append(str(temp_path))
    
    vectorstore = process_files(file_paths)
    if vectorstore is None:
        raise HTTPException(status_code=500, detail="Failed to process files")
    
    return {"message": f"✅ Indexed {vectorstore.index.ntotal} vectors"}

@app.post("/upload-url/")
async def upload_url(request: URLRequest):
    print(f"🌐 Processing URL: {request.url}")
    
    vectorstore = process_website(request.url)
    
    if vectorstore is None:
        raise HTTPException(status_code=500, detail="Website failed to process - check URL or try PDF")
    
    print(f"✅ Website indexed with {vectorstore.index.ntotal} vectors")
    return {"message": f"✅ Website processed! Total vectors: {vectorstore.index.ntotal}"}


@app.post("/ask/")
async def ask(request: QuestionRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query required")
    
    answer = ask_question(request.query)
    return {
        "question": request.query,
        "answer": answer,
        "sources": []
    }

@app.delete("/clear/")
async def clear_index():
    if INDEX_DIR.exists():
        shutil.rmtree(INDEX_DIR)
    if UPLOADS_DIR.exists():
        for f in UPLOADS_DIR.glob("*"):
            f.unlink()
    return {"message": "✅ Cleared"}
