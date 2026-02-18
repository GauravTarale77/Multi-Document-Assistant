import os
import shutil
from typing import List
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from rag import process_files, process_website, ask_question, get_vectorstore

app = FastAPI(title="Multi-Document Research Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOADS_DIR = Path("./uploads")
UPLOADS_DIR.mkdir(exist_ok=True)

class URLRequest(BaseModel):
    url: str

class QuestionRequest(BaseModel):
    query: str

@app.get("/")
def root():
    return {"message": "✅ Multi-Document RAG Assistant Live!", "status": "ready"}

@app.get("/status")
def status():
    """Check if index exists"""
    if Path("./faiss_index").exists() and any(Path("./faiss_index").iterdir()):
        return {"status": "ready", "index_exists": True}
    return {"status": "no_documents", "index_exists": False}

@app.post("/upload/")
async def upload_files(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    allowed_extensions = (".pdf", ".txt", ".docx", ".csv")
    file_paths = []

    try:
        for file in files:
            if not file.filename.lower().endswith(allowed_extensions):
                raise HTTPException(
                    status_code=400,
                    detail=f"{file.filename} is not supported. Use PDF, TXT, DOCX, CSV"
                )

            filename = f"{Path(file.filename).stem}_{len(file_paths)}{Path(file.filename).suffix}"
            temp_path = UPLOADS_DIR / filename
            
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            file_paths.append(str(temp_path))
            print(f"📁 Saved: {temp_path}")

        vectorstore = process_files(file_paths)

        if vectorstore is None:
            print("❌ process_files returned None")
            raise HTTPException(
                status_code=500,
                detail="No documents could be processed from uploaded files"
            )

        print(f"✅ Indexed {vectorstore.index.ntotal} vectors. Persisted to ./faiss_index")
        return {"message": f"Files processed and indexed successfully! Total vectors: {vectorstore.index.ntotal}"}

    except HTTPException:
        raise
    except Exception as e:
        print("❌ Upload error:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-url/")
async def upload_url(request: URLRequest):
    if not request.url.strip():
        raise HTTPException(status_code=400, detail="URL is required")

    try:
        vectorstore = process_website(request.url)

        if vectorstore is None:
            print("❌ process_website returned None")
            raise HTTPException(
                status_code=500,
                detail="Website processing failed"
            )

        print(f"✅ Website indexed with {vectorstore.index.ntotal} vectors")
        return {"message": f"Website processed successfully! Total vectors: {vectorstore.index.ntotal}"}

    except HTTPException:
        raise
    except Exception as e:
        print("❌ URL error:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ask/")
async def ask(request: QuestionRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        print("🔍 Query received:", request.query[:50] + "...")
        answer = ask_question(request.query) 
        return {
            "answer": answer,
            "sources": [] 
        }

    except ValueError as e:
        if "No documents uploaded yet" in str(e):
            raise HTTPException(status_code=400, detail="No documents indexed. Upload files/website first.")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print("❌ Ask error:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/clear/")
async def clear_index():
    """Clear all indexed documents"""
    if Path("./faiss_index").exists():
        shutil.rmtree("./faiss_index")
    if UPLOADS_DIR.exists():
        shutil.rmtree(UPLOADS_DIR)
        UPLOADS_DIR.mkdir(exist_ok=True)
    return {"message": "Index and uploads cleared successfully"}

@app.on_event("startup")
async def startup_event():
    port = os.getenv("PORT", "8000")
    print(f"🚀 Server starting on 0.0.0.0:{port}")
    print("✅ Ready for Render port detection!")
