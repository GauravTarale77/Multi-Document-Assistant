"use client";

import { useState, useRef, useEffect } from "react";
import { X, Info, Upload, Loader2, Trash2 } from "lucide-react";

const getAPI_BASE = () => {
  if (typeof window !== "undefined") {
    return process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
  }
  return process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
};

export default function App() {
  const [mode, setMode] = useState("file");
  const [files, setFiles] = useState([]);
  const [url, setUrl] = useState("");
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState("");
  const [showInfo, setShowInfo] = useState(false);
  const [status, setStatus] = useState(null);

  const fileInputRef = useRef(null);
  const API_BASE = getAPI_BASE();

  useEffect(() => {
    checkStatus();
    const interval = setInterval(checkStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const showToast = (message, type = "success") => {
    const className =
      type === "error"
        ? "bg-red-500"
        : type === "warning"
          ? "bg-yellow-500"
          : "bg-green-500";

    setToast({ message, className });
    setTimeout(() => setToast(""), 4000);
  };

  const checkStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/status`);
      const data = await res.json();
      setStatus(data);
    } catch (err) {
      console.error("Status check failed:", err);
    }
  };

  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files);
    setFiles(selectedFiles);
    checkStatus();
  };

  const removeFile = (index) => {
    const updated = files.filter((_, i) => i !== index);
    setFiles(updated);

    if (updated.length === 0 && fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const uploadFiles = async () => {
    if (!files.length) return showToast("Please select file(s)", "warning");

    setLoading(true);
    showToast("Uploading files...", "info");

    try {
      const formData = new FormData();
      files.forEach((file) => formData.append("files", file));

      const res = await fetch(`${API_BASE}/upload/`, {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Upload failed");
      }

      showToast(data.message || "Files uploaded successfully ✅", "success");
      setFiles([]);
      if (fileInputRef.current) fileInputRef.current.value = "";
      checkStatus();
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      setLoading(false);
    }
  };

  const uploadURL = async () => {
    if (!url.trim()) return showToast("Please enter URL", "warning");

    setLoading(true);
    showToast("Processing website...", "info");

    try {
      const res = await fetch(`${API_BASE}/upload-url/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "URL processing failed");
      }

      showToast(data.message || "Website processed successfully ✅", "success");
      setUrl("");
      checkStatus();
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      setLoading(false);
    }
  };

  const askQuestion = async () => {
    if (!query.trim()) return showToast("Please enter a question", "warning");

    const questionText = query.trim();
    setMessages((prev) => [...prev, { role: "user", text: questionText }]);
    setQuery("");
    setLoading(true);
    showToast("AI is thinking...", "info");

    try {
      const res = await fetch(`${API_BASE}/ask/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: questionText }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Error getting answer");
      }

      setMessages((prev) => [...prev, { role: "bot", text: data.answer }]);
      showToast("Answer generated! 🎉", "success");
    } catch (err) {
      showToast(err.message, "error");
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      askQuestion();
    }
  };

  const clearChat = () => {
    setMessages([]);
    showToast("Chat cleared", "info");
  };

  const clearIndex = async () => {
    if (!confirm("Clear all uploaded documents?")) return;

    try {
      const res = await fetch(`${API_BASE}/clear/`, { method: "DELETE" });
      const data = await res.json();
      showToast(data.message, "success");
      setStatus({ status: "no_documents", index_exists: false });
    } catch (err) {
      showToast("Failed to clear index", "error");
    }
  };

  return (
    <div className="min-h-screen bg-linear-to-br from-blue-50 to-indigo-100 p-6 relative">
      {toast && (
        <div
          className={`fixed top-5 right-5 px-4 py-2 rounded-lg shadow-lg z-50 text-white text-sm font-medium ${toast.className || "bg-emerald-500"}`}
        >
          {toast.message}
        </div>
      )}

      <div className="absolute top-5 right-5 flex gap-2">
        <button
          onClick={() => setShowInfo(true)}
          className="bg-white shadow-md p-2 rounded-full hover:bg-gray-200 transition-all cursor-pointer hover:scale-105 active:scale-95"
          title="About"
        >
          <Info size={20} className="transition-transform" />
        </button>
        <button
          onClick={clearChat}
          className="bg-white shadow-md p-2 rounded-full hover:bg-gray-200 transition-all cursor-pointer hover:scale-105 active:scale-95"
          title="Clear Chat"
        >
          <Trash2 size={20} className="transition-transform" />
        </button>
      </div>

      {showInfo && (
        <div
          className="fixed inset-0 bg-black/40 flex justify-center items-center z-50"
          onClick={() => setShowInfo(false)}
        >
          <div
            className="bg-white p-8 rounded-2xl w-96 shadow-2xl relative max-h-[80vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setShowInfo(false)}
              className="absolute top-4 right-4 text-gray-500 hover:text-black p-1 rounded-full cursor-pointer hover:bg-gray-100 transition-all"
            >
              <X size={20} />
            </button>
            <h2 className="text-2xl font-black mb-4 bg-linear-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent">
              Multi-Document Assistant
            </h2>
            <div className="space-y-3 text-sm">
              <p className="font-semibold text-gray-800">📚 Features:</p>
              <ul className="list-disc pl-5 space-y-1 text-sm">
                <li>Multi-file upload (PDF, TXT, DOCX, CSV)</li>
                <li>Website content processing</li>
                <li>Persistent RAG index (survives restarts)</li>
                <li>FastAPI + Next.js + Groq + LangChain</li>
              </ul>
              <p className="font-bold text-blue-600 cursor-pointer hover:underline">
                Contact: gauravtarale67@gmail.com
              </p>
              <p className="text-xs text-gray-500 mt-4 p-3 bg-gray-50 rounded-lg border">
                Built for portfolio. Tech stack: Next.js 14+, FastAPI, FAISS,
                llama-3.1-8b-instant (upgrading soon 🚀)
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="max-w-4xl mx-auto space-y-8">
        <div className="text-center">
          <h1 className="text-4xl font-black bg-linear-to-r from-red-500 via-pink-500 to-purple-500 bg-clip-text text-transparent mb-4 drop-shadow-lg">
            Multi-Document Assistant
          </h1>
          <div className="flex items-center justify-center gap-2 text-sm text-gray-600">
            <span>Status:</span>
            <span
              className={`px-2 py-1 rounded-full text-xs font-medium shadow-sm ${
                status?.status === "ready"
                  ? "bg-green-100 text-green-800 border border-green-200"
                  : status?.status === "no_documents"
                    ? "bg-yellow-100 text-yellow-800 border border-yellow-200"
                    : "bg-gray-100 text-gray-800 border border-gray-200"
              }`}
            >
              {status?.status === "ready"
                ? "✅ Ready"
                : status?.status === "no_documents"
                  ? "📤 Upload Docs"
                  : "🔄 Connecting..."}
            </span>
          </div>
        </div>

        <div className="flex bg-white/70 backdrop-blur-sm rounded-2xl p-1 shadow-lg w-96 mx-auto">
          <button
            onClick={() => setMode("file")}
            className={`flex-1 py-3 px-4 rounded-xl cursor-pointer font-medium transition-all hover:scale-[1.02] active:scale-[0.98] ${
              mode === "file"
                ? "bg-linear-to-r from-blue-500 to-blue-600 text-white shadow-lg shadow-blue-200"
                : "hover:bg-gray-100 text-gray-700"
            }`}
          >
            <Upload size={18} className="inline mr-2" />
            Upload Documents
          </button>
          <button
            onClick={() => setMode("url")}
            className={`flex-1 py-3 px-4 rounded-xl cursor-pointer font-medium transition-all hover:scale-[1.02] active:scale-[0.98] ${
              mode === "url"
                ? "bg-linear-to-r from-emerald-500 to-emerald-600 text-white shadow-lg shadow-emerald-200"
                : "hover:bg-gray-100 text-gray-700"
            }`}
          >
            🌐 Website URL
          </button>
        </div>

        {mode === "file" && (
          <div className="bg-white/70 backdrop-blur-sm p-8 rounded-3xl shadow-xl border border-white/50">
            <div className="mb-6">
              <label className="block text-sm font-medium mb-2 text-gray-700">
                Select files (PDF, TXT, DOCX, CSV)
              </label>
              <input
                type="file"
                multiple
                accept=".pdf,.txt,.docx,.csv"
                ref={fileInputRef}
                onChange={handleFileChange}
                className="w-full p-3 border-2 border-dashed border-gray-300 rounded-xl hover:border-blue-400 transition-all focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 cursor-pointer"
                disabled={loading}
              />
            </div>

            {files.length > 0 && (
              <div className="space-y-3 mb-6">
                <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
                  Selected files ({files.length}):
                </div>
                {files.map((file, index) => (
                  <div
                    key={index}
                    className="flex justify-between items-center bg-linear-to-r from-gray-50 to-gray-100 p-4 rounded-xl border-l-4 border-blue-400 hover:shadow-md transition-all hover:-translate-y-0.5 cursor-pointer group"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center group-hover:bg-blue-200 transition-all">
                        📄
                      </div>
                      <div>
                        <div className="font-medium text-sm">{file.name}</div>
                        <div className="text-xs text-gray-500">
                          {(file.size / 1024 / 1024).toFixed(2)} MB
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={() => removeFile(index)}
                      className="p-2 text-red-500 hover:bg-red-100 rounded-xl transition-all cursor-pointer hover:scale-110 active:scale-95"
                      title="Remove file"
                    >
                      <X size={18} />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <button
              onClick={uploadFiles}
              disabled={loading || !files.length}
              className="w-full bg-linear-to-r from-blue-500 to-blue-600 text-white py-4 px-8 cursor-pointer rounded-2xl font-semibold text-lg shadow-xl hover:shadow-2xl transform hover:-translate-y-1 active:translate-y-0 transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none group"
            >
              {loading ? (
                <div className="flex items-center justify-center gap-2">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Uploading...
                </div>
              ) : (
                <>
                  🚀 Upload & Index Files
                  <div className="" />
                </>
              )}
            </button>
          </div>
        )}

        {mode === "url" && (
          <div className="bg-white/70 backdrop-blur-sm p-8 rounded-3xl shadow-xl border border-white/50">
            <input
              type="url"
              placeholder="https://example.com"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="w-full p-5 border-2 border-gray-200 rounded-2xl text-lg focus:outline-none focus:border-emerald-400 focus:ring-4 focus:ring-emerald-100 transition-all resize-none hover:border-emerald-300 cursor-pointer"
              disabled={loading}
            />
            <button
              onClick={uploadURL}
              disabled={loading || !url.trim()}
              className="w-full mt-6 bg-linear-to-r from-emerald-500 to-emerald-600 text-white py-4 px-8 rounded-2xl font-semibold text-lg shadow-xl hover:shadow-2xl transform hover:-translate-y-1 active:translate-y-0 transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none cursor-pointer group"
            >
              {loading ? (
                <div className="flex items-center justify-center gap-2">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Processing...
                </div>
              ) : (
                "🌐 Process Website"
              )}
            </button>
          </div>
        )}

        <div className="bg-white/70 backdrop-blur-sm rounded-3xl shadow-2xl overflow-hidden border border-white/50">
          <div className="h-96 flex flex-col">
            <div className="flex-1 overflow-y-auto p-6 space-y-4 scrollbar-thin scrollbar-thumb-gray-300">
              {messages.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  {status?.status === "ready" ? (
                    <>
                      <div className="text-4xl mb-4 animate-bounce">💬</div>
                      <h3 className="text-xl font-semibold mb-2">
                        Ask anything about your documents!
                      </h3>
                      <p>Upload files or websites first, then ask questions.</p>
                    </>
                  ) : (
                    <>
                      <div className="text-4xl mb-4 animate-pulse">📤</div>
                      <h3 className="text-xl font-semibold mb-2">
                        Upload documents first
                      </h3>
                      <p>Files will be indexed and ready for Q&A.</p>
                    </>
                  )}
                </div>
              ) : (
                messages.map((msg, index) => (
                  <div
                    key={index}
                    className={`max-w-2xl p-6 rounded-2xl shadow-lg transition-all hover:shadow-xl ${
                      msg.role === "user"
                        ? "ml-auto bg-linear-to-r from-blue-500 to-blue-600 text-white translate-x-2 hover:translate-x-0"
                        : "bg-linear-to-r from-gray-100 to-gray-200 hover:-translate-y-0.5"
                    }`}
                  >
                    {msg.text}
                  </div>
                ))
              )}

              {loading && (
                <div className="bg-linear-to-r from-purple-100 to-purple-200 p-6 rounded-2xl w-fit ml-auto shadow-lg animate-pulse hover:shadow-xl">
                  <div className="flex items-center gap-2">
                    <Loader2 className="w-6 h-6 animate-spin" />
                    AI is thinking...
                  </div>
                </div>
              )}
            </div>

            <div className="border-t p-6 bg-white/50">
              <div className="flex gap-3">
                <input
                  type="text"
                  placeholder={
                    status?.status === "ready"
                      ? "Ask a question about your documents..."
                      : "Upload documents first..."
                  }
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={handleKeyPress}
                  className="flex-1 border-2 border-gray-200 rounded-2xl px-6 py-4 text-lg focus:outline-none focus:border-purple-400 focus:ring-4 focus:ring-purple-100 transition-all resize-none disabled:opacity-50 disabled:cursor-not-allowed hover:border-purple-300 cursor-pointer"
                  disabled={loading || status?.status !== "ready"}
                />
                <button
                  onClick={askQuestion}
                  disabled={
                    loading || !query.trim() || status?.status !== "ready"
                  }
                  className="bg-linear-to-r from-purple-500 to-purple-600 text-white px-8 py-4 rounded-2xl font-semibold text-lg shadow-xl hover:shadow-2xl transform hover:-translate-y-1 active:translate-y-0 transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none whitespace-nowrap cursor-pointer hover:scale-[1.02] group"
                >
                  Send
                </button>
              </div>
              {status?.status !== "ready" && (
                <p className="text-xs text-yellow-600 mt-2 text-center font-medium animate-pulse">
                  ⏳ Upload documents first to start chatting
                </p>
              )}
            </div>
          </div>
        </div>

        {status?.index_exists && (
          <div className="text-center">
            <button
              onClick={clearIndex}
              className="px-6 py-2 bg-red-100 text-red-700 rounded-xl hover:bg-red-200 font-medium transition-all cursor-pointer hover:shadow-md active:scale-95 border border-red-200 hover:scale-[1.02]"
            >
              🗑️ Clear All Documents
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
