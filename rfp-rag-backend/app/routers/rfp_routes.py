# Auto-generated (restored behavior + improved RAG + model registry + safe caps + outline/section + save/load)
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Body, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Set, Dict, Any
import os, shutil, json, time, traceback
import crud, models, schemas, auth
from app.deps import get_db
from app.core.config import PROJECTS_DIRECTORY, DB_DIRECTORY
from app.services.document_service import (
    process_document,
    sanitize_name_for_directory,
    num_tokens_from_string,
)

# Retrieval / LLM deps
from sentence_transformers import CrossEncoder
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.messages import HumanMessage
import chromadb

router = APIRouter()

# ------------------------
# Curated model registry
# ------------------------
MODEL_REGISTRY = {
    "fast": {
        "id": "fast",
        "label": "Fast (cheap)",
        "model_name": "gpt-4o-mini",
        "context_tokens": 128000,
        "max_completion_tokens": 4096,
    },
    "balanced": {
        "id": "balanced",
        "label": "Balanced",
        "model_name": "gpt-4o",
        "context_tokens": 128000,
        "max_completion_tokens": 8192,
    },
    "verbose": {
        "id": "verbose",
        "label": "Verbose",
        "model_name": "gpt-4.1",
        "context_tokens": 128000,
        "max_completion_tokens": 8192,
    },
}

def _caps_for_model(model_name: str):
    for m in MODEL_REGISTRY.values():
        if m["model_name"] == model_name:
            return m
    return MODEL_REGISTRY["fast"]

@router.get("/models")
def list_models():
    return list(MODEL_REGISTRY.values())

# --- Cross-encoder reranker ---
rerank_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

def calc_max_output_tokens(prompt_text: str, model_name: str, safety_margin: int = 2000, target_min: int = 3000) -> int:
    caps = _caps_for_model(model_name)
    ctx = caps["context_tokens"]
    max_out_cap = caps["max_completion_tokens"]
    prompt_tokens = num_tokens_from_string(prompt_text, "cl100k_base")
    available = max(1024, ctx - prompt_tokens - safety_margin)
    return min(max(target_min, min(available, max_out_cap)), max_out_cap)

def build_retriever(collection_name: str, embeddings, k: int = 50, use_mmr: bool = True):
    vectordb = Chroma(
        persist_directory=DB_DIRECTORY,
        embedding_function=embeddings,
        collection_name=collection_name,
    )
    if use_mmr:
        return vectordb.as_retriever(search_type="mmr", search_kwargs={"k": k, "lambda_mult": 0.5})
    return vectordb.as_retriever(search_kwargs={"k": k})

def expand_queries(base_query: str, llm: ChatOpenAI, n: int = 3) -> List[str]:
    prompt = f"""You are assisting with information retrieval.
Create {n} diverse paraphrases of the following query to improve document recall.
Return each paraphrase on its own line, no numbering, no extra text.

Query:
{base_query}
"""
    resp = llm.invoke([HumanMessage(content=prompt)])
    text = resp.content if hasattr(resp, "content") else str(resp)
    variants = [line.strip() for line in text.splitlines() if line.strip()]
    uniq: List[str] = []
    seen: Set[str] = set()
    for q in [base_query] + variants:
        if q not in seen:
            uniq.append(q)
            seen.add(q)
    return uniq[: n + 1]

# ------------------------
# RFP project + document endpoints (legacy behavior preserved)
# ------------------------

@router.post("/rfps/", response_model=schemas.RfpProject, status_code=201)
def create_rfp_project(
    project: schemas.RfpProjectBase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    project_id = sanitize_name_for_directory(f"{current_user.username}_{project.name}")
    db_project = crud.get_project_by_project_id(db, project_id=project_id)
    if db_project:
        raise HTTPException(status_code=400, detail=f"Project '{project.name}' already exists for this user.")
    os.makedirs(os.path.join(PROJECTS_DIRECTORY, project_id), exist_ok=True)
    project_create = schemas.RfpProjectCreate(name=project.name, project_id=project_id)
    return crud.create_rfp_project(db=db, project=project_create, user_id=current_user.id)

@router.get("/rfps/", response_model=List[schemas.RfpProject])
def get_rfp_projects(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    return crud.get_projects_by_user(db, user_id=current_user.id, skip=skip, limit=limit)

@router.post("/rfps/{project_id}/upload/")
async def upload_to_project(
    project_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    db_project = crud.get_project_by_project_id(db, project_id)
    if not db_project or db_project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="RFP project not found.")
    project_path = os.path.join(PROJECTS_DIRECTORY, project_id)
    os.makedirs(project_path, exist_ok=True)
    file_location = os.path.join(project_path, file.filename)
    try:
        with open(file_location, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")
    try:
        process_document(file_location, collection_name=project_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {e}")
    return {"filename": file.filename, "status": "uploaded"}

@router.get("/rfps/{project_id}/documents/")
def list_project_documents(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    db_project = crud.get_project_by_project_id(db, project_id)
    if not db_project or db_project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="RFP project not found.")
    project_path = os.path.join(PROJECTS_DIRECTORY, project_id)
    documents = []
    if os.path.isdir(project_path):
        for fname in os.listdir(project_path):
            fpath = os.path.join(PROJECTS_DIRECTORY, project_id, fname)
            if os.path.isfile(fpath):
                documents.append({"name": fname, "status": "Processed"})
    return documents

@router.get("/rfps/{project_id}/documents/{document_name}")
def get_project_document(
    project_id: str,
    document_name: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    db_project = crud.get_project_by_project_id(db, project_id)
    if not db_project or db_project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="RFP project not found.")
    file_path = os.path.join(PROJECTS_DIRECTORY, project_id, document_name)
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Document not found.")
    # serve as generic file (pdf, md, etc.)
    return FileResponse(file_path)

@router.delete("/rfps/{project_id}/documents/{document_name}", status_code=204)
def delete_project_document(
    project_id: str,
    document_name: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    db_project = crud.get_project_by_project_id(db, project_id)
    if not db_project or db_project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="RFP project not found.")
    file_path_to_delete = os.path.join(PROJECTS_DIRECTORY, project_id, document_name)
    try:
        client = chromadb.PersistentClient(path=DB_DIRECTORY)
        collection = client.get_collection(name=project_id)
        collection.delete(where={"source": file_path_to_delete})
    except Exception:
        pass
    try:
        if os.path.isfile(file_path_to_delete):
            os.remove(file_path_to_delete)
    except Exception:
        pass
    return

# app/routers/rfp_routes.py
import os, shutil, stat, logging
from fastapi import HTTPException
import chromadb

logger = logging.getLogger("uvicorn.error")

def _handle_remove_readonly(func, path, excinfo):
    # Windows likes to mark files read-only; flip bit and retry
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        raise

@router.delete("/rfps/{project_id}")
def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    """
    Deletes a project by its string slug `project_id`.
    Cleans up Chroma collection, project folder, dependent rows, then DB row.
    Returns a 'steps' list for diagnostics if anything fails.
    """
    steps = []
    try:
        # Verify ownership & load project row
        db_project = crud.get_project_by_project_id(db, project_id)
        if not db_project or db_project.owner_id != current_user.id:
            raise HTTPException(status_code=404, detail="RFP project not found.")
        steps.append("project_loaded")

        # 1) Best-effort: remove Chroma collection
        try:
            client = chromadb.PersistentClient(path=DB_DIRECTORY)
            try:
                coll = client.get_collection(name=project_id)
                try:
                    coll.delete(where={})
                except Exception:
                    pass
                try:
                    client.delete_collection(name=project_id)
                except Exception:
                    pass
                steps.append("chroma_deleted")
            except Exception as e:
                steps.append(f"chroma_not_found_or_error:{e}")
        except Exception as e:
            steps.append(f"chroma_client_error:{e}")

        # 2) Best-effort: delete project folder (Windows-safe)
        project_path = os.path.join(PROJECTS_DIRECTORY, project_id)
        try:
            if os.path.exists(project_path):
                shutil.rmtree(project_path, onerror=_handle_remove_readonly)
            steps.append("fs_deleted")
        except Exception as e:
            steps.append(f"fs_error:{e}")

        # 3) Best-effort: clear dependent rows to avoid FK issues
        try:
            try:
                crud.delete_chat_history(db, project_id=db_project.id)
                steps.append("chat_history_deleted")
            except Exception as e:
                steps.append(f"chat_history_error:{e}")

            # If you maintain per-project prompt functions, clean them too
            try:
                if hasattr(crud, "delete_prompt_functions_for_project"):
                    crud.delete_prompt_functions_for_project(db, project_id=db_project.id)
                    steps.append("prompt_functions_deleted")
            except Exception as e:
                steps.append(f"prompt_functions_error:{e}")
        except Exception as e:
            steps.append(f"dependent_cleanup_error:{e}")

        # 4) Delete DB row — IMPORTANT: pass the STRING slug, not numeric id
        try:
            crud.delete_project(db, project_id=db_project.project_id, user_id=current_user.id)
            steps.append("db_project_deleted")
        except TypeError:
            # fallback if your CRUD doesn't require user_id
            crud.delete_project(db, project_id=db_project.project_id)
            steps.append("db_project_deleted_no_user")
        except Exception as e:
            logger.exception("DB delete failed")
            raise HTTPException(
                status_code=500,
                detail={"error": "DB delete failed", "steps": steps, "exception": str(e)},
            )

        return {"message": "Project deleted successfully.", "steps": steps}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Delete project failed")
        raise HTTPException(
            status_code=500,
            detail={"error": "Delete failed", "steps": steps, "exception": str(e)},
        )

@router.put("/rfps/{project_id}", response_model=schemas.RfpProject)
def update_project(
    project_id: str,
    update: schemas.RfpProjectUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    db_project = crud.get_project_by_project_id(db, project_id)
    if not db_project or db_project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="RFP project not found.")
    return crud.update_project(db, project_id=db_project.id, update=update)

@router.get("/rfps/{project_id}/settings", response_model=schemas.Settings)
def get_settings(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    db_project = crud.get_project_by_project_id(db, project_id)
    if not db_project or db_project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return schemas.Settings(
        system_prompt=db_project.system_prompt,
        model_name=db_project.model_name,
        temperature=db_project.temperature,
        context_size=db_project.context_size,
    )

@router.post("/rfps/{project_id}/settings", response_model=schemas.RfpProject)
def update_settings(
    project_id: str,
    settings: schemas.Settings,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    db_project = crud.update_settings(db, project_id, settings, user_id=current_user.id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    return db_project

@router.get("/rfps/{project_id}/chat-history")
def get_project_chat_history(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
) -> list[dict[str, Any]]:
    """
    Returns chat history for a project as a flat list of messages:
      [{ "message_type": "query"|"answer"|"error", "text": "...", "sources": [] }, ...]
    Tries to use crud.get_chat_messages if available; falls back to the tuple history used for prompts.
    """
    db_project = crud.get_project_by_project_id(db, project_id)
    if not db_project or db_project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="RFP project not found.")

    # Preferred: use a CRUD method that returns ORM ChatMessage rows, if present
    try:
        msgs = crud.get_chat_messages(db, project_id=db_project.id)  # may not exist in your CRUD
        out = []
        for m in msgs:
            # handle both ORM objects and plain dicts
            mt = getattr(m, "message_type", None) or (m.get("message_type") if isinstance(m, dict) else None) or "message"
            txt = getattr(m, "text", None) or (m.get("text") if isinstance(m, dict) else None) or ""
            src = getattr(m, "sources", None) or (m.get("sources") if isinstance(m, dict) else None) or []
            out.append({"message_type": mt, "text": txt, "sources": src})
        return out
    except AttributeError:
        # Fallback: rebuild from the (user, assistant) tuples used for prompt context
        pairs = crud.get_chat_history_for_model(db, project_id=db_project.id)
        out = []
        for (u, a) in pairs:
            if u:
                out.append({"message_type": "query", "text": u, "sources": []})
            if a:
                out.append({"message_type": "answer", "text": a, "sources": []})
        return out

@router.delete("/rfps/{project_id}/chat-history", status_code=204)
def clear_project_chat_history(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    db_project = crud.get_project_by_project_id(db, project_id)
    if not db_project or db_project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="RFP project not found.")
    crud.delete_chat_history(db, project_id=db_project.id)
    return

# ------------------------
# Improved /query (long-form answer with safe token caps)
# ------------------------
@router.post("/rfps/{project_id}/query/")
async def query_project(
    project_id: str,
    request: schemas.QueryRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    db_project = crud.get_project_by_project_id(db, project_id)
    if not db_project or db_project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="RFP project not found.")

    if request.prompt_function_id:
        prompt_function = crud.get_prompt_function(db, function_id=request.prompt_function_id)
        if not prompt_function:
            raise HTTPException(status_code=404, detail="Prompt function not found.")
        query_text = prompt_function.prompt_text
        user_message_text = f"Executing function: {prompt_function.button_label}"
    elif request.query:
        query_text = request.query
        user_message_text = request.query
    else:
        raise HTTPException(status_code=400, detail="Request must include either a 'query' or a 'prompt_function_id'.")

    try:
        crud.create_chat_message(db, message=schemas.ChatMessageCreate(message_type="query", text=user_message_text), project_id=db_project.id)

        embeddings = OpenAIEmbeddings()
        planner_llm = ChatOpenAI(model_name=db_project.model_name, temperature=0.1, max_tokens=400)

        queries = expand_queries(query_text, planner_llm, n=3)

        project_docs_all, kb_docs_all = [], []
        for q in queries:
            proj_ret = build_retriever(project_id, embeddings, k=50, use_mmr=True)
            project_docs_all.extend(proj_ret.get_relevant_documents(q))
            if request.use_knowledge_base:
                try:
                    kb_ret = build_retriever("knowledge_base", embeddings, k=50, use_mmr=True)
                    kb_docs_all.extend(kb_ret.get_relevant_documents(q))
                except Exception:
                    pass

        def unique_docs(docs):
            seen = set()
            uniq = []
            for d in docs:
                key = (d.page_content, d.metadata.get("source"), d.metadata.get("page"))
                if key not in seen:
                    uniq.append(d)
                    seen.add(key)
            return uniq

        project_docs = unique_docs(project_docs_all)
        kb_docs = unique_docs(kb_docs_all)

        all_docs = project_docs + kb_docs
        if all_docs:
            pairs = [[query_text, d.page_content] for d in all_docs]
            scores = rerank_model.predict(pairs)
            reranked_docs = [doc for _, doc in sorted(zip(scores, all_docs), key=lambda x: x[0], reverse=True)]
        else:
            reranked_docs = []

        context_size_map = {"low": 10, "medium": 15, "high": 20}
        top_k = context_size_map.get(db_project.context_size, 15)

        project_final, kb_final = [], []
        for doc in reranked_docs:
            (kb_final if doc in kb_docs else project_final).append(doc)
            if len(project_final) + len(kb_final) >= top_k:
                break
        min_rfp = max(3, top_k // 3)
        if len(project_final) < min_rfp and kb_final:
            needed = min_rfp - len(project_final)
            move = kb_final[:needed]
            project_final.extend(move)
            kb_final = kb_final[needed:]

        project_context = "\n".join(d.page_content for d in project_final)
        knowledge_base_context = "\n".join(d.page_content for d in kb_final)

        chat_pairs = crud.get_chat_history_for_model(db, project_id=db_project.id)
        chat_history_tuples = "\n".join([f"User: {u}\nAssistant: {a}" for (u, a) in chat_pairs])

        if request.use_knowledge_base:
            prompt_text = f"""{db_project.system_prompt}

**CONTEXT FROM RFP DOCUMENTS:**
{project_context}

**CONTEXT FROM KNOWLEDGE BASE:**
{knowledge_base_context}

**PREVIOUS CONVERSATION:**
{chat_history_tuples}

**CURRENT QUESTION:**
{query_text}

**INSTRUCTIONS:**
- Write a thorough, detailed answer with concrete references to the provided context.
- Use structured Markdown (headers, bullet lists, tables where useful).
- Include assumptions, dependencies, and risks when applicable.
- Provide explicit sectioned reasoning and avoid generic filler.
- Aim for at least 1,000–2,000 words if the question warrants it.
**RESPONSE:**"""
        else:
            prompt_text = f"""{db_project.system_prompt}

**CONTEXT FROM DOCUMENTS:**
{project_context}

**PREVIOUS CONVERSATION:**
{chat_history_tuples}

**CURRENT QUESTION:**
{query_text}

**INSTRUCTIONS:**
- Write a thorough, detailed answer with concrete references to the provided context.
- Use structured Markdown (headers, bullet lists, tables where useful).
- Include assumptions, dependencies, and risks when applicable.
- Provide explicit sectioned reasoning and avoid generic filler.
- Aim for at least 1,000–2,000 words if the question warrants it.
**RESPONSE:**"""

        max_out = calc_max_output_tokens(prompt_text, model_name=db_project.model_name, safety_margin=2000, target_min=3000)
        llm = ChatOpenAI(model_name=db_project.model_name, temperature=db_project.temperature, max_tokens=max_out)
        result = llm.invoke([HumanMessage(content=prompt_text)])
        answer_text = result.content if hasattr(result, "content") else str(result)

        crud.create_chat_message(db, message=schemas.ChatMessageCreate(message_type="answer", text=answer_text), project_id=db_project.id)
        return {"answer": answer_text}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")

# ------------------------
# Outline-only endpoint
# ------------------------
@router.post("/rfps/{project_id}/proposal-outline")
async def proposal_outline(
    project_id: str,
    request: schemas.QueryRequest,  # use query + use_knowledge_base
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    db_project = crud.get_project_by_project_id(db, project_id)
    if not db_project or db_project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="RFP project not found.")

    base_topic = request.query or "Draft a comprehensive proposal"
    embeddings = OpenAIEmbeddings()
    planner_llm = ChatOpenAI(model_name=db_project.model_name, temperature=0.1, max_tokens=800)

    proj_ret = build_retriever(project_id, embeddings, k=30, use_mmr=True)
    proj_docs = proj_ret.get_relevant_documents(base_topic)
    kb_docs = []
    if request.use_knowledge_base:
        try:
            kb_ret = build_retriever("knowledge_base", embeddings, k=30, use_mmr=True)
            kb_docs = kb_ret.get_relevant_documents(base_topic)
        except Exception:
            pass
    context_outline = "\n".join(d.page_content for d in (proj_docs + kb_docs)[:12])

    outline_prompt = f"""{db_project.system_prompt}

You are drafting a complete boilerplate proposal. Based on the context and topic, create an outline with 8–14 top-level sections suitable for a federal-style technical/management proposal. 
Use H2 headings (##) for top-level sections; add a short bullet list under each for subpoints.

**TOPIC:** {base_topic}

**CONTEXT (EXCERPT):**
{context_outline}

Return only the outline in Markdown (## headings + bullets)."""
    resp = planner_llm.invoke([HumanMessage(content=outline_prompt)])
    draft_outline = resp.content if hasattr(resp, "content") else str(resp)
    sections = [line[3:].strip() for line in draft_outline.splitlines() if line.strip().startswith("## ")]
    if not sections:
        sections = [
            "Executive Summary",
            "Technical Approach",
            "Management Approach",
            "Staffing & Key Personnel",
            "Schedule & Milestones",
            "Risk Management",
            "Quality Assurance",
            "Compliance & Certifications",
            "Cost & Pricing Approach",
            "Assumptions & Dependencies",
        ]
    return {"sections": sections}

# ------------------------
# Single-section generator (returns HTML)
# ------------------------
@router.post("/rfps/{project_id}/proposal-section")
async def proposal_section(
    project_id: str,
    section_title: str = Body(..., embed=True),
    query: Optional[str] = Body(default=None, embed=True),
    use_knowledge_base: bool = Body(default=False, embed=True),
    words_per_section: int = Body(default=1500, embed=True),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    db_project = crud.get_project_by_project_id(db, project_id)
    if not db_project or db_project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="RFP project not found.")

    topic = query or "Draft a comprehensive proposal"
    embeddings = OpenAIEmbeddings()
    planner_llm = ChatOpenAI(model_name=db_project.model_name, temperature=0.1, max_tokens=400)

    # Multi-query expansion around the section
    section_query_base = f"{topic} :: Section: {section_title}"
    q_variants = expand_queries(section_query_base, planner_llm, n=3)

    proj_cands, kb_cands = [], []
    for q in q_variants:
        proj_ret = build_retriever(project_id, embeddings, k=50, use_mmr=True)
        proj_cands.extend(proj_ret.get_relevant_documents(q))
        if use_knowledge_base:
            try:
                kb_ret = build_retriever("knowledge_base", embeddings, k=50, use_mmr=True)
                kb_cands.extend(kb_ret.get_relevant_documents(q))
            except Exception:
                pass

    def unique_docs(docs):
        seen = set()
        uniq = []
        for d in docs:
            key = (d.page_content, d.metadata.get("source"), d.metadata.get("page"))
            if key not in seen:
                uniq.append(d)
                seen.add(key)
        return uniq

    proj_docs = unique_docs(proj_cands)
    kb_docs = unique_docs(kb_cands)

    union_docs = proj_docs + kb_docs
    if union_docs:
        pairs = [[section_query_base, d.page_content] for d in union_docs]
        scores = rerank_model.predict(pairs)
        reranked = [doc for _, doc in sorted(zip(scores, union_docs), key=lambda x: x[0], reverse=True)]
    else:
        reranked = []

    context_size_map = {"low": 10, "medium": 15, "high": 20}
    top_k = context_size_map.get(db_project.context_size, 15)

    proj_final, kb_final = [], []
    for d in reranked:
        (kb_final if d in kb_docs else proj_final).append(d)
        if len(proj_final) + len(kb_final) >= top_k:
            break
    min_rfp = max(3, top_k // 3)
    if len(proj_final) < min_rfp and kb_final:
        needed = min_rfp - len(proj_final)
        move = kb_final[:needed]
        proj_final.extend(move)
        kb_final = kb_final[needed:]

    proj_ctx = "\n".join(d.page_content for d in proj_final)
    kb_ctx = "\n".join(d.page_content for d in kb_final)

    section_prompt = f"""{db_project.system_prompt}

## {section_title}

**CONTEXT FROM RFP DOCUMENTS:**
{proj_ctx}

{"**CONTEXT FROM KNOWLEDGE BASE:**\n" + kb_ctx if use_knowledge_base else ""}

**INSTRUCTIONS:**
- Write a substantial, high-quality draft for this section (target {words_per_section}–{words_per_section+700} words).
- Cite specific details from the provided context (filename/page if available).
- Use clear headings, bullet points, and tables where helpful.
- Include an **Assumptions & Dependencies** subsection for this section.
- Avoid generic filler; anchor content to the context.

**SECTION DRAFT (HTML)**:
Return valid HTML that can be displayed inside a rich text editor without additional post-processing.
Use <h3>, <h4>, <p>, <ul>, <ol>, <table>, <thead>, <tbody>, <tr>, <th>, <td> tags appropriately.
"""
    max_out = calc_max_output_tokens(section_prompt, model_name=db_project.model_name, safety_margin=2000, target_min=1200)
    section_llm = ChatOpenAI(model_name=db_project.model_name, temperature=db_project.temperature, max_tokens=max_out)
    res = section_llm.invoke([HumanMessage(content=section_prompt)])
    html = res.content if hasattr(res, "content") else str(res)

    return {"section": section_title, "content": html}

# ------------------------
# Save / Load proposal drafts (JSON + compiled HTML/MD)
# ------------------------
def _project_dir(project_id: str) -> str:
    return os.path.join(PROJECTS_DIRECTORY, project_id)

def _draft_dir(project_id: str) -> str:
    d = os.path.join(_project_dir(project_id), "proposal_drafts")
    os.makedirs(d, exist_ok=True)
    return d

def _compile_html(sections: List[Dict[str, Any]]) -> str:
    toc = "\n".join([f"<li>{s.get('title','Section')}</li>" for s in sections])
    body = "\n".join([f"<h2>{s.get('title','Section')}</h2>\n{(s.get('html') or '')}" for s in sections])
    return f"""<html>
<head>
<meta charset="utf-8" />
<style>
body {{ font-family: Arial, sans-serif; line-height: 1.4; }}
h1, h2, h3 {{ margin: 0.6em 0 0.3em; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: 6px; }}
ul, ol {{ padding-left: 1.2em; }}
.toc ul {{ list-style: disc; }}
</style>
</head>
<body>
<h1>Proposal Draft</h1>
<div class="toc">
  <h2>Table of Contents</h2>
  <ul>{toc}</ul>
</div>
{body}
</body>
</html>"""

def _compile_md(sections: List[Dict[str, Any]]) -> str:
    # naive HTML → MD: keep headings and strip the rest, since FE keeps HTML for editing
    lines = ["# Proposal Draft", "", "## Table of Contents"]
    for s in sections:
        lines.append(f"- {s.get('title','Section')}")
    lines.append("")
    for s in sections:
        lines.append(f"## {s.get('title','Section')}")
        lines.append("")
        # strip tags very naively
        import re as _re
        html = s.get("html") or ""
        text = _re.sub(r"<[^>]+>", "", html)
        lines.append(text.strip())
        lines.append("")
    return "\n".join(lines)

@router.post("/rfps/{project_id}/proposal-save")
async def proposal_save(
    project_id: str,
    title: Optional[str] = Body(default="Proposal Draft", embed=True),
    sections: List[Dict[str, Any]] = Body(..., embed=True),  # [{id,title,html}]
    versioned: bool = Body(default=True, embed=True),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    db_project = crud.get_project_by_project_id(db, project_id)
    if not db_project or db_project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="RFP project not found.")

    drafts_dir = _draft_dir(project_id)
    ts = int(time.time())
    stem = f"draft_{ts}" if versioned else "draft_latest"

    json_path = os.path.join(drafts_dir, f"{stem}.json")
    html_path = os.path.join(drafts_dir, f"{stem}.html")
    md_path   = os.path.join(_project_dir(project_id), "draft_proposal.md")  # maintain existing path for MD

    # Persist JSON (full fidelity)
    payload = {"title": title, "sections": sections, "timestamp": ts}
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # Persist compiled HTML (for optional server-side export if needed later)
    html = _compile_html(sections)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    # Maintain a markdown snapshot for your existing viewer
    md = _compile_md(sections)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)

    return {"status": "ok", "json": json_path, "html": html_path, "md": md_path, "timestamp": ts}

@router.get("/rfps/{project_id}/proposal-load")
async def proposal_load(
    project_id: str,
    version: Optional[str] = Query(default=None, description="Filename like draft_1712345678.json; if omitted, load latest"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    db_project = crud.get_project_by_project_id(db, project_id)
    if not db_project or db_project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="RFP project not found.")

    drafts_dir = _draft_dir(project_id)

    def _latest_json() -> Optional[str]:
        files = [f for f in os.listdir(drafts_dir) if f.endswith(".json")]
        if not files:
            return None
        files.sort(reverse=True)  # draft_1689012345.json → descending timestamp by name
        return os.path.join(drafts_dir, files[0])

    json_path = os.path.join(drafts_dir, version) if version else _latest_json()
    if not json_path or not os.path.isfile(json_path):
        raise HTTPException(status_code=404, detail="No draft found.")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

@router.get("/rfps/{project_id}/proposal-versions")
async def proposal_versions(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    db_project = crud.get_project_by_project_id(db, project_id)
    if not db_project or db_project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="RFP project not found.")

    drafts_dir = _draft_dir(project_id)
    files = [f for f in os.listdir(drafts_dir) if f.endswith(".json")]
    files.sort(reverse=True)
    return {"versions": files}
