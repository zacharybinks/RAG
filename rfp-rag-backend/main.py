# rfp-rag-backend/main.py

# --- Standard Library Imports ---
import shutil, os, re, tempfile, traceback
from typing import List
from datetime import timedelta

# --- Third-Party Imports ---
import chromadb
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status, Form
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from sqlalchemy.exc import OperationalError
from sentence_transformers import CrossEncoder
import tiktoken

# --- LangChain Imports ---
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, AIMessage

# --- Local Application Imports ---
import crud, models, schemas, auth
from database import SessionLocal

# ==============================================================================
# INITIAL SETUP & CONFIGURATION
# ==============================================================================
load_dotenv()

# --- Environment Configuration ---
APP_ENV = os.getenv("APP_ENV", "development")

# --- App Setup ---
PROJECTS_DIRECTORY = os.getenv("PROJECTS_DIRECTORY", "./rfp_projects")
DB_DIRECTORY = os.getenv("DB_DIRECTORY", "./chroma_db")
KNOWLEDGE_BASE_DIRECTORY = os.getenv("KNOWLEDGE_BASE_DIRECTORY", "./knowledge_base")

print(f"--- [Startup] Running in {APP_ENV} mode.")
print(f"--- [Startup] Using PROJECTS_DIRECTORY: {PROJECTS_DIRECTORY}")
print(f"--- [Startup] Using DB_DIRECTORY: {DB_DIRECTORY}")
print(f"--- [Startup] Using KNOWLEDGE_BASE_DIRECTORY: {KNOWLEDGE_BASE_DIRECTORY}")
os.makedirs(PROJECTS_DIRECTORY, exist_ok=True)
os.makedirs(DB_DIRECTORY, exist_ok=True)
os.makedirs(KNOWLEDGE_BASE_DIRECTORY, exist_ok=True)


api_root_path = "/api" if APP_ENV == "production" else ""

app = FastAPI(title="RFP RAG System Backend", root_path=api_root_path)


# --- CORS Configuration ---
origins = [
    "http://localhost:3000",
    "https://rfp-rag-app.azurewebsites.net",
    "https://ai.avatar-computing.com",
    "https://rfp-rag-app-fgguhaezgmekczgg.eastus2-01.azurewebsites.net"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================================================
# HELPER FUNCTIONS & DEPENDENCIES
# ==============================================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def sanitize_name_for_directory(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r'[\s\W-]+', '_', s)
    return s

def process_document(file_path: str, collection_name: str):
    print(f"--- [5] Starting LangChain PDFLoader for file: {file_path}")
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    print(f"--- [6] PDF loaded successfully. Found {len(documents)} pages.")

    for doc in documents:
        doc.metadata['source'] = file_path

    print("--- [7] Splitting document into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    texts = text_splitter.split_documents(documents)
    print(f"--- [8] Document split into {len(texts)} chunks.")
    
    print(f"--- [9] Initializing embeddings and ChromaDB at: {DB_DIRECTORY}")
    embeddings = OpenAIEmbeddings()
    vectordb = Chroma.from_documents(
        documents=texts, 
        embedding=embeddings, 
        collection_name=collection_name, 
        persist_directory=DB_DIRECTORY
    )
    vectordb.persist()
    print(f"--- [10] Finished processing and storing vectors for collection '{collection_name}'")
    return True

def num_tokens_from_string(string: str, encoding_name: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens

# ==============================================================================
# API ENDPOINTS
# ==============================================================================

@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db, username=form_data.username)
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password", headers={"WWW-Authenticate": "Bearer"})
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # --- Domain validation for user registration ---
    domain = user.username.split('@')[1]
    allowed_domains = ["avatar-computing.com", "sossecinc.com"]
    if domain.lower() not in allowed_domains:
        raise HTTPException(status_code=400, detail="Registration is restricted.")

    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)

@app.get("/users/me/", response_model=schemas.User)
async def read_users_me(current_user: models.User = Depends(auth.get_current_active_user)):
    return current_user

@app.post("/rfps/", response_model=schemas.RfpProject, status_code=201)
def create_rfp_project(project: schemas.RfpProjectBase, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    project_id = sanitize_name_for_directory(f"{current_user.username}_{project.name}")
    db_project = crud.get_project_by_project_id(db, project_id=project_id)
    if db_project:
        raise HTTPException(status_code=400, detail=f"Project '{project.name}' already exists for this user.")
    
    project_path = os.path.join(PROJECTS_DIRECTORY, project_id)
    os.makedirs(project_path, exist_ok=True)
        
    project_create = schemas.RfpProjectCreate(name=project.name, project_id=project_id)
    return crud.create_rfp_project(db=db, project=project_create, user_id=current_user.id)

@app.get("/rfps/", response_model=List[schemas.RfpProject])
def get_rfp_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    return crud.get_projects_by_user(db, user_id=current_user.id, skip=skip, limit=limit)

@app.post("/rfps/{project_id}/upload/")
async def upload_to_project(project_id: str, file: UploadFile = File(...), db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    print(f"--- [1] Upload endpoint initiated for project: {project_id}")
    db_project = crud.get_project_by_project_id(db, project_id)
    if not db_project or db_project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="RFP project not found.")
    
    project_path = os.path.join(PROJECTS_DIRECTORY, project_id)
    os.makedirs(project_path, exist_ok=True)
    file_location = os.path.join(project_path, file.filename)
    
    try:
        print(f"--- [2] Saving {file.filename} to path: {file_location}")
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
        print("--- [3] File save successful.")
        
        process_document(file_location, collection_name=project_id)

        print("--- [11] Entire upload and process workflow completed successfully.")
        return {"info": f"File '{file.filename}' uploaded and processed."}
    except Exception as e:
        print(f"!!! [FATAL ERROR] An exception occurred during the upload/process workflow. !!!")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.get("/rfps/{project_id}/documents/")
async def get_project_documents(project_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    db_project = crud.get_project_by_project_id(db, project_id)
    if not db_project or db_project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="RFP project not found.")
    
    project_path = os.path.join(PROJECTS_DIRECTORY, project_id)
    documents = []
    if os.path.isdir(project_path):
        files = os.listdir(project_path)
        documents = [{"name": f, "status": "Processed"} for f in files if os.path.isfile(os.path.join(project_path, f))]
    return documents

@app.get("/rfps/{project_id}/documents/{document_name}")
async def download_document(project_id: str, document_name: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    db_project = crud.get_project_by_project_id(db, project_id)
    if not db_project or db_project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    file_path = os.path.join(PROJECTS_DIRECTORY, project_id, document_name)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Document not found")
    return FileResponse(path=file_path, filename=document_name)

@app.delete("/rfps/{project_id}/documents/{document_name}", status_code=204)
async def delete_document(project_id: str, document_name: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    db_project = crud.get_project_by_project_id(db, project_id)
    if not db_project or db_project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    file_path_to_delete = os.path.join(PROJECTS_DIRECTORY, project_id, document_name)

    try:
        client = chromadb.PersistentClient(path=DB_DIRECTORY)
        collection = client.get_collection(name=project_id)
        collection.delete(where={"source": file_path_to_delete})
        print(f"Deleted vectors for source: {file_path_to_delete}")
    except Exception as e:
        print(f"Could not delete vectors for {document_name}: {e}")

    if os.path.isfile(file_path_to_delete):
        os.remove(file_path_to_delete)
    else:
        raise HTTPException(status_code=404, detail="Document file not found")
    return

@app.delete("/rfps/{project_id}", status_code=204)
def delete_project(project_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    deleted = crud.delete_project(db, project_id, user_id=current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        client = chromadb.PersistentClient(path=DB_DIRECTORY)
        client.delete_collection(name=project_id)
    except Exception as e:
        print(f"Could not delete Chroma collection for {project_id}: {e}")
    
    project_path = os.path.join(PROJECTS_DIRECTORY, project_id)
    if os.path.isdir(project_path):
        shutil.rmtree(project_path)
    return

@app.put("/rfps/{project_id}", response_model=schemas.RfpProject)
def update_project(project_id: str, project_update: schemas.RfpProjectUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    db_project = crud.update_project(db, project_id, project_update, user_id=current_user.id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    return db_project

@app.get("/rfps/{project_id}/settings", response_model=schemas.Settings)
def get_settings(project_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    db_project = crud.get_project_by_project_id(db, project_id)
    if not db_project or db_project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return schemas.Settings(
        system_prompt=db_project.system_prompt,
        model_name=db_project.model_name,
        temperature=db_project.temperature,
        # context_amount=db_project.context_amount, # <-- This line is removed
        context_size=db_project.context_size,
    )

@app.post("/rfps/{project_id}/settings", response_model=schemas.RfpProject)
def update_settings(project_id: str, settings: schemas.Settings, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    db_project = crud.update_settings(db, project_id, settings, user_id=current_user.id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    return db_project

@app.get("/prompt-functions/", response_model=List[schemas.PromptFunction])
def get_prompt_functions(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    return crud.get_prompt_functions(db=db)

@app.post("/prompt-functions/", response_model=schemas.PromptFunction, status_code=201)
def create_prompt_function(function_data: schemas.PromptFunctionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    existing = crud.get_prompt_function_by_name(db, function_name=function_data.function_name)
    if existing:
        raise HTTPException(status_code=400, detail="A function with this name already exists.")
    return crud.create_prompt_function(db, function=function_data)

@app.put("/prompt-functions/{function_id}", response_model=schemas.PromptFunction)
def update_prompt_function(function_id: int, function_update: schemas.PromptFunctionUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    db_function = crud.update_prompt_function(db, function_id, function_update)
    if not db_function:
        raise HTTPException(status_code=404, detail="Prompt function not found")
    return db_function

@app.delete("/rfps/{project_id}/chat-history", status_code=204)
def clear_project_chat_history(project_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    """Deletes all chat messages for a specific project."""
    db_project = crud.get_project_by_project_id(db, project_id)
    if not db_project or db_project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="RFP project not found.")
    
    crud.delete_chat_history(db, project_id=db_project.id)
    return

# --- Initialize the CrossEncoder model ---
rerank_model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

@app.post("/rfps/{project_id}/query/")
async def query_project(project_id: str, request: schemas.QueryRequest, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    db_project = crud.get_project_by_project_id(db, project_id)
    if not db_project or db_project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="RFP project not found.")

    query_text = ""
    user_message_text = ""

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
        
        project_vectordb = Chroma(persist_directory=DB_DIRECTORY, embedding_function=embeddings, collection_name=project_id)
        project_retriever = project_vectordb.as_retriever(search_kwargs={"k": 20})
        project_docs = project_retriever.get_relevant_documents(query_text)

        all_docs = list(project_docs) # Use a copy
        kb_docs = []

        if request.use_knowledge_base:
            try:
                kb_vectordb = Chroma(persist_directory=DB_DIRECTORY, embedding_function=embeddings, collection_name="knowledge_base")
                kb_retriever = kb_vectordb.as_retriever(search_kwargs={"k": 20})
                kb_docs = kb_retriever.get_relevant_documents(query_text)
                all_docs.extend(kb_docs)
            except Exception as e:
                print(f"Could not retrieve from knowledge base: {e}")
                pass

        if all_docs:
            rerank_pairs = [[query_text, doc.page_content] for doc in all_docs]
            scores = rerank_model.predict(rerank_pairs)
            reranked_docs = [doc for _, doc in sorted(zip(scores, all_docs), key=lambda x: x[0], reverse=True)]
        else:
            reranked_docs = []

        context_size_map = {'low': 5, 'medium': 10, 'high': 15}
        top_k = context_size_map.get(db_project.context_size, 10)
        
        # Build the context strings and final doc list together
        final_docs_for_sources = []
        project_context_list = []
        kb_context_list = []

        for doc in reranked_docs[:top_k]:
            final_docs_for_sources.append(doc)
            if doc in kb_docs:
                kb_context_list.append(doc.page_content)
            else: # Assumes if not in kb_docs, it must be in project_docs
                project_context_list.append(doc.page_content)
        
        project_context = "\n".join(project_context_list)
        knowledge_base_context = "\n".join(kb_context_list)

        # --- Intelligent, Token-Aware Prompt Construction ---
        max_tokens = 16385
        buffer = 1500  # Increased buffer for more complex answers
        token_budget = max_tokens - buffer
        
        chat_history_tuples = crud.get_chat_history_for_model(db, project_id=db_project.id)
        
        # --- Conditionally build the prompt template ---
        if request.use_knowledge_base:
            prompt_template_text = f"""{db_project.system_prompt}

You have been provided with context from two sources: project-specific documents and a general knowledge base.
**CONTEXT FROM PROJECT DOCUMENTS:**
{{context}}
**CONTEXT FROM KNOWLEDGE BASE:**
{{knowledge_base_context}}
**PREVIOUS CONVERSATION:**
{chat_history_tuples}
**CURRENT QUESTION:**
{query_text}
**INSTRUCTIONS:**
- Provide a thorough, detailed analysis
- Use proper Markdown formatting with headers, bullet points, and emphasis
- Include specific details and examples from the documents
- Structure your response with clear sections
- Be comprehensive but well-organized
- Use tables, lists, and formatting to enhance readability
**DETAILED RESPONSE:**
"""
        else:
            prompt_template_text = f"""{db_project.system_prompt}

**CONTEXT FROM DOCUMENTS:**
{{context}}
**PREVIOUS CONVERSATION:**
{chat_history_tuples}
**CURRENT QUESTION:**
{query_text}
**INSTRUCTIONS:**
- Provide a thorough, detailed analysis
- Use proper Markdown formatting with headers, bullet points, and emphasis
- Include specific details and examples from the documents
- Structure your response with clear sections
- Be comprehensive but well-organized
- Use tables, lists, and formatting to enhance readability
**DETAILED RESPONSE:**
"""
        
        # --- Build final context with token budget ---
        final_context_parts = []
        current_context_tokens = 0
        
        # Calculate tokens for the template without the document context
        if request.use_knowledge_base:
            fixed_parts_tokens = num_tokens_from_string(prompt_template_text.format(context="", knowledge_base_context=""), "cl100k_base")
        else:
            fixed_parts_tokens = num_tokens_from_string(prompt_template_text.format(context=""), "cl100k_base")

        context_token_budget = token_budget - fixed_parts_tokens

        # Add context documents one by one until the budget is filled
        for doc in final_docs_for_sources:
            doc_content = doc.page_content + "\n---\n"
            doc_tokens = num_tokens_from_string(doc_content, "cl100k_base")
            if current_context_tokens + doc_tokens <= context_token_budget:
                final_context_parts.append(doc_content)
                current_context_tokens += doc_tokens
            else:
                break
        
        final_context = "".join(final_context_parts)
        
        # Construct the final prompt
        if request.use_knowledge_base:
            final_prompt = prompt_template_text.format(
                context=project_context,
                knowledge_base_context=knowledge_base_context
            )
        else:
            final_prompt = prompt_template_text.format(context=final_context)

        if APP_ENV == "development":
            print("===================== PROMPT TO LLM =====================")
            print(f"--- Token Count: {num_tokens_from_string(final_prompt, 'cl100k_base')} ---")
            print(final_prompt)
            print("=========================================================")

        llm = ChatOpenAI(model_name=db_project.model_name, temperature=db_project.temperature, max_tokens=buffer)
        
        messages = [HumanMessage(content=final_prompt)]
        result = llm.invoke(messages)
        answer = result.content
        crud.create_chat_message(db, message=schemas.ChatMessageCreate(message_type="answer", text=answer), project_id=db_project.id)
        source_docs = [{"source": os.path.basename(doc.metadata.get("source", "N/A")), "page": doc.metadata.get("page", "N/A")} for doc in final_docs_for_sources]
        return {"answer": answer, "sources": list({f"Page {s['page']} of {s['source']}" for s in source_docs})}

    except Exception as e:
        if "does not exist" in str(e) and "knowledge_base" not in str(e):
             raise HTTPException(status_code=404, detail=f"No documents have been uploaded to '{project_id}' yet.")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An error occurred during query: {str(e)}")


# ==============================================================================
# KNOWLEDGE BASE ENDPOINTS
# ==============================================================================

@app.post("/knowledge-base/upload/")
async def upload_to_knowledge_base(
    file: UploadFile = File(...),
    description: str = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    file_location = os.path.join(KNOWLEDGE_BASE_DIRECTORY, file.filename)
    
    try:
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
        
        process_document(file_location, collection_name="knowledge_base")

        doc_create = schemas.KnowledgeBaseDocumentCreate(document_name=file.filename, description=description)
        crud.create_knowledge_base_document(db, doc_create)

        return {"info": f"File '{file.filename}' uploaded to the knowledge base."}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.get("/knowledge-base/documents/", response_model=List[schemas.KnowledgeBaseDocument])
def get_knowledge_base_documents(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    return crud.get_knowledge_base_documents(db)

@app.get("/knowledge-base/documents/{document_name}")
async def download_knowledge_base_document(document_name: str, current_user: models.User = Depends(auth.get_current_active_user)):
    file_path = os.path.join(KNOWLEDGE_BASE_DIRECTORY, document_name)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Document not found")
    return FileResponse(path=file_path, filename=document_name)

@app.delete("/knowledge-base/documents/{document_name}", status_code=204)
async def delete_knowledge_base_document(document_name: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    file_path_to_delete = os.path.join(KNOWLEDGE_BASE_DIRECTORY, document_name)

    try:
        client = chromadb.PersistentClient(path=DB_DIRECTORY)
        collection = client.get_collection(name="knowledge_base")
        collection.delete(where={"source": file_path_to_delete})
        print(f"Deleted vectors for source: {file_path_to_delete}")
    except Exception as e:
        print(f"Could not delete vectors for {document_name}: {e}")

    if os.path.isfile(file_path_to_delete):
        os.remove(file_path_to_delete)
        crud.delete_knowledge_base_document(db, document_name)
    else:
        raise HTTPException(status_code=404, detail="Document file not found")
    return

# ==============================================================================
# APPLICATION STARTUP EVENT
# ==============================================================================

def _seed_prompt_functions_logic(db: Session):
    function_name = "Generate Requirements"
    existing_function = crud.get_prompt_function_by_name(db, function_name=function_name)
    if existing_function:
        print(f"--- [Startup] '{function_name}' function already exists. Skipping seed.")
        return

    print(f"--- [Startup] Seeding '{function_name}' function... ---")
    prompt_text = """User wants a comprehensive list of all the requirements for their proposal.
Requirements should include the following categories and the response should be structured with a response for each category.

 Category 1: Performance & Operational Requirements (The "What")
 Category 2: Proposal Submission & Formatting Requirements (The "How to Submit")
 Category 3: Evaluation Criteria & Award Factors (The "How You'll Be Judged")
 Category 4: Key Personnel & Staffing Requirements (The "Who")
 Category 5: Cost & Pricing Requirements (The "How Much")
 Category 6: Contractual & Legal Requirements (The "Fine Print")
 Category 7: Other

Category Definitions:
Category 1: Performance & Operational Requirements (“The What”)
Definition: These requirements define the actual scope of work the offeror is being asked to perform—usually pulled from the Statement of Work (SOW), Performance Work Statement (PWS), or Statement of Objectives (SOO). These describe what must be delivered, what standards must be met, and how success will be measured.
AI Parsing Notes: Start with any “The contractor shall…” or “The CMF is responsible for…” phrasing. Look for functionally grouped tasks — e.g., “administering,” “facilitating,” “reporting,” or “evaluating.” Use structure or headers like: Task Areas, Work Breakdown, or Performance Objectives.
Common Sub-Categories (Specific to CMFs): Consortium Administration & Governance, Member Management & Growth, Solicitation & Project Lifecycle Management, Financial & Transactional Management, Marketing, Communications & Collaboration, Reporting & Data Management.

Category 2: Proposal Submission & Formatting Requirements (“The How to Submit”)
Definition: These requirements dictate how the offeror must structure, format, and deliver their proposal. Failure to comply with these often results in automatic disqualification, regardless of technical merit.
AI Parsing Notes: Look for specifics around font size, margins, volume structure, and delivery method. These will nearly always be found in Section L, or in attachments labeled “Instructions to Offerors” or “Submission Guidelines.”
Includes: Formatting Requirements, Content & Structure Requirements, Submission Logistics, Administrative Submissions.

Category 3: Evaluation Criteria & Award Factors (“The How You’ll Be Judged”)
Definition: The government’s “grading rubric.” These criteria determine how proposals are scored, and ultimately, who is awarded the project. These are typically located in Section M, or in a stand-alone Evaluation Criteria section.
AI Parsing Notes: Look for verbs like “will be evaluated based on…” or “the government will assess…” These may also appear as subfactors within larger volumes, such as Technical Volume instructions.
Includes: Technical/Management Approach, Key Personnel Qualifications, Past Performance, Organizational Conflict of Interest (OCI), Cost/Price Reasonableness.

Category 4: Key Personnel & Staffing Requirements (“The Who”)
Definition: Defines who must be on the project team, their qualifications, and how that information must be presented. These are often separate from evaluation criteria because they’re baseline eligibility requirements—you must meet them to be considered.
AI Parsing Notes: Look for “must include a Program Manager who…” or “key personnel shall have…” type statements. Section L typically has Resume/Staffing Plan requirements. SOW/PWS may define essential roles.
Includes: Required Positions, Experience & Qualification Mandates, Resume Requirements.

Category 5: Cost & Pricing Requirements (“The How Much”)
Definition: This category captures how cost and pricing data must be presented, what information must be justified, and the acceptable formats for doing so. While often flexible under OTA, these requirements must still be met with precision.
AI Parsing Notes: Pull from any cost model, pricing template, or Volume II (Cost Volume) instructions. Look for language like “Submit a Basis of Estimate…” or “Include direct and indirect labor rates…”
Includes: Fee Structure & Model, Cost Breakdown & Detail, Financial Narrative.

Category 6: Contractual & Legal Requirements (“The Fine Print”)
Definition: These are the non-negotiable terms and conditions that the performer must accept to enter into an OTA agreement. Often found in the base OTA, Model Agreement, or Sections H & I, they include compliance terms and legal obligations.
AI Parsing Notes: Use cues like “the contractor agrees to…,” “in accordance with FAR/DFARS…,” or “terms and conditions of this agreement include…”
Includes: Period of Performance, Data & Intellectual Property Rights, Governance Clauses, Security Requirements.

Category 7: Other
Definition: Catch-all category for items that don't directly fall into Categories 1–6. Includes general background, definitions, references, or administrative material not requiring proposal response unless cited.
AI Parsing Notes: Commonly drawn from the cover letter, background sections, and Q&A clarifications. Flag items here only if no action is required or if the language is purely contextual.
Includes: Background/introduction language, Glossaries, acronyms, or boilerplate, References to documents not included in the package, Questions/answers that clarify but do not introduce new requirements."""
    
    function_data = schemas.PromptFunctionCreate(
        module_name="Write",
        function_name=function_name,
        button_label="Generate Requirements",
        description="Extracts and categorizes all proposal requirements from the uploaded documents into seven key areas.",
        prompt_text=prompt_text
    )
    crud.create_prompt_function(db, function=function_data)

@app.post("/seed-prompt-functions/", status_code=201)
def seed_prompt_functions_endpoint(db: Session = Depends(get_db)):
    _seed_prompt_functions_logic(db=db)
    return {"message": "Seeding of prompt functions complete."}

@app.on_event("startup")
async def startup_event():
    print("--- [Startup] Application is starting up. ---")
    db = SessionLocal()
    try:
        print("--- [Startup] Seeding default prompt functions... ---")
        _seed_prompt_functions_logic(db=db)
    finally:
        db.close()
        print("--- [Startup] Database session closed. ---")