# Auto-generated (improved chunking for better RAG + token helper)
import os
from typing import List
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from app.core.config import DB_DIRECTORY
import tiktoken
import re
import unicodedata

def sanitize_name_for_directory(name: str) -> str:
    # Keep legacy behavior but make it robust
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = name.strip().lower()
    name = re.sub(r"[^\w\-]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name or "project"

def num_tokens_from_string(string: str, encoding_name: str = "cl100k_base") -> int:
    try:
        encoding = tiktoken.get_encoding(encoding_name)
    except Exception:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(string or ""))

def _split_documents(pages) -> List:
    """
    Split pages using a larger chunk size and smart separators so long-form
    generations have cohesive context blocks.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1400,
        chunk_overlap=200,
        separators=["\n## ", "\n# ", "\n\n", "\n", " "],
    )
    return splitter.split_documents(pages)

def process_document(file_path: str, collection_name: str) -> None:
    """
    Load a PDF, split into chunks, and add to (or create) a Chroma collection.
    Persist to disk so future runs can retrieve.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # Load pages with metadata (source, page)
    loader = PyPDFLoader(file_path)
    pages = loader.load()  # returns Documents with metadata

    # Split into chunks
    splits = _split_documents(pages)

    # Ensure source is the absolute path for consistent deletions later
    abs_src = os.path.abspath(file_path)
    for d in splits:
        d.metadata = d.metadata or {}
        d.metadata["source"] = os.path.abspath(d.metadata.get("source") or abs_src)

    embeddings = OpenAIEmbeddings()
    vectordb = Chroma(
        persist_directory=DB_DIRECTORY,
        embedding_function=embeddings,
        collection_name=collection_name,
    )
    vectordb.add_documents(splits)
    vectordb.persist()
