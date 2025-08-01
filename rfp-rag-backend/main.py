# --- Standard Library Imports ---
import shutil, os, re, tempfile, traceback
from typing import List
from datetime import timedelta

# --- Third-Party Imports ---
import chromadb
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from sqlalchemy.exc import OperationalError

# --- LangChain Imports ---
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate

# --- Local Application Imports ---
import crud, models, schemas, auth
from database import SessionLocal

# ==============================================================================
# INITIAL SETUP & CONFIGURATION
# ==============================================================================
load_dotenv()

# --- App Setup ---
# **CRITICAL FIX**: Use the /tmp directory which is always writable in a container environment
PROJECTS_DIRECTORY = "/app/data/rfp_projects"
DB_DIRECTORY = "/app/data/chroma_db"
os.makedirs(PROJECTS_DIRECTORY, exist_ok=True)
os.makedirs(DB_DIRECTORY, exist_ok=True)

app = FastAPI(title="RFP RAG System Backend - Simplified", root_path="/api")

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
    max_age=3600,
)

# Add this to increase FastAPI's upload limit
@app.middleware("http")
async def add_upload_size_limit(request, call_next):
    request.scope["upload_max_size"] = 20 * 1024 * 1024  # 20MB
    response = await call_next(request)
    return response

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
    
    print("--- [9] Initializing embeddings and ChromaDB...")
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
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
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
        print(f"--- [2] Saving {file.filename} to temp path: {file_location}")
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
        print("--- [3] Local save successful.")
        
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
    return schemas.Settings(system_prompt=db_project.system_prompt)

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

@app.post("/rfps/{project_id}/query/")
async def query_project(project_id: str, request: schemas.QueryRequest, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    db_project = crud.get_project_by_project_id(db, project_id)
    if not db_project or db_project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="RFP project not found.")

    prompt_template = ""
    query_text = ""
    user_message_text = ""
    retriever_k = 15

    if request.prompt_function_id:
        prompt_function = crud.get_prompt_function(db, function_id=request.prompt_function_id)
        if not prompt_function:
            raise HTTPException(status_code=404, detail="Prompt function not found.")
        query_text = prompt_function.prompt_text
        user_message_text = f"Executing function: {prompt_function.button_label}"
        retriever_k = 30
        prompt_template = f"""{db_project.system_prompt}

You are an expert analyst working with document content. Based on the following context from the uploaded documents, provide a comprehensive and detailed response to the user's request.

**DOCUMENT CONTEXT:**
{{context}}

**USER REQUEST:**
{{question}}

**INSTRUCTIONS:**
- Provide a thorough, detailed analysis
- Use proper Markdown formatting with headers, bullet points, and emphasis
- Include specific details and examples from the documents
- Structure your response with clear sections
- Be comprehensive but well-organized
- Use tables, lists, and formatting to enhance readability

**COMPREHENSIVE RESPONSE:**"""
    elif request.query:
        query_text = request.query
        user_message_text = request.query
        prompt_template = f"""{db_project.system_prompt}

You are a knowledgeable assistant with access to document content. Use the provided context to give a detailed, well-formatted response.

**DOCUMENT CONTEXT:**
{{context}}

**QUESTION:**
{{question}}

**INSTRUCTIONS:**
- Provide a comprehensive answer with specific details from the documents
- Format your response using Markdown (headers, lists, emphasis, tables where appropriate)
- If you don't know something, clearly state what information is missing
- Structure your answer logically with clear sections
- Include relevant examples and specifics from the context
- Make your response detailed and informative

**DETAILED ANSWER:**"""
    else:
        raise HTTPException(status_code=400, detail="Request must include either a 'query' or a 'prompt_function_id'.")

    try:
        crud.create_chat_message(db, message=schemas.ChatMessageCreate(message_type="query", text=user_message_text), project_id=db_project.id)
        chat_history_for_model = crud.get_chat_history_for_model(db, project_id=db_project.id)
        QA_CHAIN_PROMPT = PromptTemplate.from_template(prompt_template)
        embeddings = OpenAIEmbeddings()
        vectordb = Chroma(persist_directory=DB_DIRECTORY, embedding_function=embeddings, collection_name=project_id)
        retriever = vectordb.as_retriever(search_kwargs={"k": retriever_k})
        qa = ConversationalRetrievalChain.from_llm(
            llm=ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.3), 
            retriever=retriever, 
            combine_docs_chain_kwargs={"prompt": QA_CHAIN_PROMPT}, 
            return_source_documents=True
        )
        result = qa.invoke({"question": query_text, "chat_history": chat_history_for_model})
        crud.create_chat_message(db, message=schemas.ChatMessageCreate(message_type="answer", text=result["answer"]), project_id=db_project.id)
        source_docs = [{"source": os.path.basename(doc.metadata.get("source", "N/A")), "page": doc.metadata.get("page", "N/A")} for doc in result["source_documents"]]
        return {"answer": result["answer"], "sources": list({f"Page {s['page']} of {s['source']}" for s in source_docs})}
    except Exception as e:
        if "does not exist" in str(e):
             raise HTTPException(status_code=404, detail=f"No documents have been uploaded to '{project_id}' yet.")
        raise HTTPException(status_code=500, detail=f"An error occurred during query: {str(e)}")

@app.get("/db-test")
def test_db_connection(db: Session = Depends(get_db)):
    print("--- [DB TEST] Received request for database connection test. ---")
    try:
        db.execute('SELECT 1')
        print("--- [DB TEST] Successfully executed 'SELECT 1'. Connection is OK. ---")
        return {"status": "success", "message": "Database connection successful!"}
    except OperationalError as e:
        print(f"!!! [FATAL DB ERROR] Could not connect to the database. !!!")
        print(f"Error Details: {e}")
        raise HTTPException(status_code=500, detail=f"Database connection failed: {e}")
    except Exception as e:
        print(f"!!! [FATAL UNKNOWN ERROR] An unexpected error occurred during DB test. !!!")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unknown error occurred: {e}")
