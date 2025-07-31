# --- Standard Library Imports ---
import shutil
import os
import re
import tempfile
import traceback
from typing import List
from datetime import timedelta

# --- Third-Party Imports ---
import boto3
import chromadb
from botocore.exceptions import ClientError
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# --- LangChain Imports ---
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate

# --- Local Application Imports ---
# These import the database models, Pydantic schemas, CRUD functions, and authentication logic
import crud, models, schemas, auth
from database import SessionLocal

# ==============================================================================
# INITIAL SETUP & CONFIGURATION
# ==============================================================================

# Load environment variables from the .env file at the very start
load_dotenv()

# --- Environment Configuration ---
# Determines if the app runs in 'production' (using S3) or 'development' (using local files)
APP_ENV = os.getenv("APP_ENV", "development")
# The name of the S3 bucket to use for file storage in production
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

# --- Sanity Checks for Production ---
# If the app is in production mode, it MUST have an S3 bucket name configured.
if APP_ENV == "production" and not S3_BUCKET_NAME:
    raise RuntimeError("S3_BUCKET_NAME environment variable must be set in production.")

# --- App Setup ---
# Define directories for local file storage and the vector database
PROJECTS_DIRECTORY = "./rfp_projects"  # Used for local development file storage
DB_DIRECTORY = "/tmp/chroma_db" if APP_ENV == "production" else "./chroma_db"
os.makedirs(PROJECTS_DIRECTORY, exist_ok=True)
os.makedirs(DB_DIRECTORY, exist_ok=True)

# --- FastAPI App Initialization ---
app = FastAPI(title="RFP RAG System Backend - S3 Integrated")

# --- CORS (Cross-Origin Resource Sharing) Configuration ---
# This list defines which frontend URLs are allowed to make API calls to this backend.
origins = [
    "http://localhost:3000",
    "https://courageous-rabanadas-930011.netlify.app",
    "https://ai.avatar-computing.com"
]

# Add the CORS middleware to the FastAPI application
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all HTTP headers
)

# ==============================================================================
# HELPER FUNCTIONS & DEPENDENCIES
# ==============================================================================

def get_db():
    """
    FastAPI dependency that creates and yields a new database session for each
    API request, and ensures it's closed afterward.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def sanitize_name_for_directory(name: str) -> str:
    """
    Takes a string and sanitizes it to be a safe name for a directory or a
    ChromaDB collection by making it lowercase and replacing special characters.
    """
    s = name.lower().strip()
    s = re.sub(r'[\s\W-]+', '_', s)
    return s

def process_document(file_path: str, collection_name: str, original_s3_key: str = None):
    """
    The core RAG processing function. It takes a file path, loads the PDF,
    splits it into chunks, generates embeddings, and stores them in a
    specific ChromaDB collection.
    """
    print(f"--- [5] Starting LangChain PDFLoader for file: {file_path}")
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    print(f"--- [6] PDF loaded successfully. Found {len(documents)} pages.")

    # If the file came from S3, embed its path into the metadata of each chunk
    if original_s3_key:
        for doc in documents:
            doc.metadata['source'] = original_s3_key

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

# --- Authentication Endpoints ---

@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Handles user login and returns a JWT access token."""
    user = crud.get_user_by_username(db, username=form_data.username)
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password", headers={"WWW-Authenticate": "Bearer"})
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Handles new user registration."""
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return crud.create_user(db=db, user=user)

@app.get("/users/me/", response_model=schemas.User)
async def read_users_me(current_user: models.User = Depends(auth.get_current_active_user)):
    """Returns the currently authenticated user's information."""
    return current_user

# --- Project and Document Management Endpoints ---

@app.post("/rfps/{project_id}/upload/")
async def upload_to_project(project_id: str, file: UploadFile = File(...), db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    """
    Handles file uploads. In production, it uploads to S3. In development,
    it saves to a local folder. It then triggers the document processing.
    """
    print(f"--- [1] Upload endpoint initiated for project: {project_id}")
    db_project = crud.get_project_by_project_id(db, project_id)
    if not db_project or db_project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="RFP project not found.")
    
    try:
        if APP_ENV == "production":
            s3_client_instance = boto3.client("s3")
            s3_key = f"{project_id}/{file.filename}"
            print(f"--- [2] Uploading {file.filename} to s3://{S3_BUCKET_NAME}/{s3_key}")
            s3_client_instance.upload_fileobj(file.file, S3_BUCKET_NAME, s3_key)
            print("--- [3] S3 upload successful.")
            
            with tempfile.NamedTemporaryFile(dir="/tmp", delete=False, suffix=".pdf") as tmp:
                try:
                    print(f"--- [4] Downloading from S3 to temp file {tmp.name} for processing...")
                    s3_client_instance.download_fileobj(S3_BUCKET_NAME, s3_key, tmp)
                    process_document(tmp.name, collection_name=project_id, original_s3_key=s3_key)
                finally:
                    os.unlink(tmp.name)
        else: # Development environment
            project_path = os.path.join(PROJECTS_DIRECTORY, project_id)
            os.makedirs(project_path, exist_ok=True)
            file_location = os.path.join(project_path, file.filename)
            print(f"--- [2] Saving {file.filename} to local path: {file_location}")
            with open(file_location, "wb+") as file_object:
                shutil.copyfileobj(file.file, file_object)
            print("--- [3] Local save successful.")
            process_document(file_location, collection_name=project_id, original_s3_key=file_location)

        print("--- [11] Entire upload and process workflow completed successfully.")
        return {"info": f"File '{file.filename}' uploaded and processed."}
    except Exception as e:
        print(f"!!! [FATAL ERROR] An exception occurred during the upload/process workflow. !!!")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.get("/rfps/{project_id}/documents/")
async def get_project_documents(project_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    """Lists all documents associated with a specific project."""
    db_project = crud.get_project_by_project_id(db, project_id)
    if not db_project or db_project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="RFP project not found.")
    
    documents = []
    if APP_ENV == "production":
        try:
            s3_client_instance = boto3.client("s3")
            response = s3_client_instance.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=f"{project_id}/")
            documents = [{"name": os.path.basename(obj['Key']), "status": "Processed"} for obj in response.get('Contents', []) if not obj['Key'].endswith('/')]
        except ClientError as e:
            print(f"S3 List Error: {e}")
    else:
        project_path = os.path.join(PROJECTS_DIRECTORY, project_id)
        if os.path.isdir(project_path):
            files = os.listdir(project_path)
            documents = [{"name": f, "status": "Processed"} for f in files if os.path.isfile(os.path.join(project_path, f))]

    return documents

@app.get("/rfps/{project_id}/documents/{document_name}")
async def download_document(project_id: str, document_name: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    """Provides a way to download a specific document."""
    db_project = crud.get_project_by_project_id(db, project_id)
    if not db_project or db_project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if APP_ENV == "production":
        s3_client_instance = boto3.client("s3")
        s3_key = f"{project_id}/{document_name}"
        try:
            url = s3_client_instance.generate_presigned_url('get_object', Params={'Bucket': S3_BUCKET_NAME, 'Key': s3_key}, ExpiresIn=300)
            return RedirectResponse(url=url)
        except ClientError as e:
            print(f"S3 Download Error: {e}")
            raise HTTPException(status_code=404, detail="Document not found in storage.")
    else:
        file_path = os.path.join(PROJECTS_DIRECTORY, project_id, document_name)
        if not os.path.isfile(file_path):
            raise HTTPException(status_code=404, detail="Document not found")
        return FileResponse(path=file_path, filename=document_name)

@app.delete("/rfps/{project_id}/documents/{document_name}", status_code=204)
async def delete_document(project_id: str, document_name: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    """Deletes a document and its associated vectors."""
    db_project = crud.get_project_by_project_id(db, project_id)
    if not db_project or db_project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    source_path_to_delete = f"{project_id}/{document_name}" if APP_ENV == "production" else os.path.join(PROJECTS_DIRECTORY, project_id, document_name)

    try:
        client = chromadb.PersistentClient(path=DB_DIRECTORY)
        collection = client.get_collection(name=project_id)
        collection.delete(where={"source": source_path_to_delete})
        print(f"Deleted vectors for source: {source_path_to_delete}")
    except Exception as e:
        print(f"Could not delete vectors for {document_name}: {e}")

    if APP_ENV == "production":
        s3_client_instance = boto3.client("s3")
        try:
            s3_client_instance.delete_object(Bucket=S3_BUCKET_NAME, Key=source_path_to_delete)
        except ClientError as e:
            print(f"S3 Delete Error: {e}")
            raise HTTPException(status_code=404, detail="Document file not found in storage")
    else:
        if os.path.isfile(source_path_to_delete):
            os.remove(source_path_to_delete)
        else:
            raise HTTPException(status_code=404, detail="Document file not found")
    return

@app.post("/rfps/", response_model=schemas.RfpProject, status_code=201)
def create_rfp_project(project: schemas.RfpProjectBase, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    """Creates a new RFP project record in the database."""
    project_id = sanitize_name_for_directory(f"{current_user.username}_{project.name}")
    db_project = crud.get_project_by_project_id(db, project_id=project_id)
    if db_project:
        raise HTTPException(status_code=400, detail=f"Project '{project.name}' already exists for this user.")
    
    if APP_ENV == "development":
        project_path = os.path.join(PROJECTS_DIRECTORY, project_id)
        os.makedirs(project_path, exist_ok=True)
        
    project_create = schemas.RfpProjectCreate(name=project.name, project_id=project_id)
    return crud.create_rfp_project(db=db, project=project_create, user_id=current_user.id)

@app.delete("/rfps/{project_id}", status_code=204)
def delete_project(project_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    """Deletes a project, its documents, and its vector collection."""
    deleted = crud.delete_project(db, project_id, user_id=current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        client = chromadb.PersistentClient(path=DB_DIRECTORY)
        client.delete_collection(name=project_id)
    except Exception as e:
        print(f"Could not delete Chroma collection for {project_id}: {e}")
    
    if APP_ENV == "development":
        project_path = os.path.join(PROJECTS_DIRECTORY, project_id)
        if os.path.isdir(project_path):
            shutil.rmtree(project_path)
    return

@app.get("/rfps/", response_model=List[schemas.RfpProject])
def get_rfp_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    """Lists all projects for the current user."""
    return crud.get_projects_by_user(db, user_id=current_user.id, skip=skip, limit=limit)

@app.put("/rfps/{project_id}", response_model=schemas.RfpProject)
def update_project(project_id: str, project_update: schemas.RfpProjectUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    """Updates a project's name."""
    db_project = crud.update_project(db, project_id, project_update, user_id=current_user.id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    return db_project

@app.get("/rfps/{project_id}/settings", response_model=schemas.Settings)
def get_settings(project_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    """Gets the settings (system prompt) for a project."""
    db_project = crud.get_project_by_project_id(db, project_id)
    if not db_project or db_project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return schemas.Settings(system_prompt=db_project.system_prompt)

@app.post("/rfps/{project_id}/settings", response_model=schemas.RfpProject)
def update_settings(project_id: str, settings: schemas.Settings, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    """Updates the settings for a project."""
    db_project = crud.update_settings(db, project_id, settings, user_id=current_user.id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    return db_project

@app.get("/prompt-functions/", response_model=List[schemas.PromptFunction])
def get_prompt_functions(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    """Gets all available prompt functions."""
    return crud.get_prompt_functions(db=db)

@app.post("/prompt-functions/", response_model=schemas.PromptFunction, status_code=201)
def create_prompt_function(function_data: schemas.PromptFunctionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    """Creates a new prompt function."""
    existing = crud.get_prompt_function_by_name(db, function_name=function_data.function_name)
    if existing:
        raise HTTPException(status_code=400, detail="A function with this name already exists.")
    return crud.create_prompt_function(db, function=function_data)

@app.put("/prompt-functions/{function_id}", response_model=schemas.PromptFunction)
def update_prompt_function(function_id: int, function_update: schemas.PromptFunctionUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    """Updates an existing prompt function."""
    db_function = crud.update_prompt_function(db, function_id, function_update)
    if not db_function:
        raise HTTPException(status_code=404, detail="Prompt function not found")
    return db_function

@app.post("/rfps/{project_id}/query/")
async def query_project(project_id: str, request: schemas.QueryRequest, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    """The main RAG query endpoint. Handles both chat messages and function calls."""
    db_project = crud.get_project_by_project_id(db, project_id)
    if not db_project or db_project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="RFP project not found.")

    prompt_template = ""
    query_text = ""
    user_message_text = ""
    retriever_k = 3

    if request.prompt_function_id:
        prompt_function = crud.get_prompt_function(db, function_id=request.prompt_function_id)
        if not prompt_function:
            raise HTTPException(status_code=404, detail="Prompt function not found.")
        query_text = prompt_function.prompt_text
        user_message_text = f"Executing function: {prompt_function.button_label}"
        retriever_k = 20
        prompt_template = f"""{db_project.system_prompt}\n\nBased on the following context from a document, please fulfill the user's request.\n**CONTEXT:**\n{{context}}\n\n**REQUEST:**\n{{question}}\n\n**Comprehensive Answer (formatted in Markdown):**"""
    elif request.query:
        query_text = request.query
        user_message_text = request.query
        prompt_template = f"""{db_project.system_prompt}\n\nUse the following pieces of context to answer the question at the end. If you don't know the answer, just say that you don't know, don't try to make up an answer.\n**Format your answer using Markdown...**\n\nContext: {{context}}\n\nQuestion: {{question}}\nHelpful Answer:"""
    else:
        raise HTTPException(status_code=400, detail="Request must include either a 'query' or a 'prompt_function_id'.")

    try:
        crud.create_chat_message(db, message=schemas.ChatMessageCreate(message_type="query", text=user_message_text), project_id=db_project.id)
        chat_history_for_model = crud.get_chat_history_for_model(db, project_id=db_project.id)
        QA_CHAIN_PROMPT = PromptTemplate.from_template(prompt_template)
        embeddings = OpenAIEmbeddings()
        vectordb = Chroma(persist_directory=DB_DIRECTORY, embedding_function=embeddings, collection_name=project_id)
        retriever = vectordb.as_retriever(search_kwargs={"k": retriever_k})
        qa = ConversationalRetrievalChain.from_llm(llm=ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.2), retriever=retriever, combine_docs_chain_kwargs={"prompt": QA_CHAIN_PROMPT}, return_source_documents=True)
        result = qa.invoke({"question": query_text, "chat_history": chat_history_for_model})
        crud.create_chat_message(db, message=schemas.ChatMessageCreate(message_type="answer", text=result["answer"]), project_id=db_project.id)
        source_docs = [{"source": os.path.basename(doc.metadata.get("source", "N/A")), "page": doc.metadata.get("page", "N/A")} for doc in result["source_documents"]]
        return {"answer": result["answer"], "sources": list({f"Page {s['page']} of {s['source']}" for s in source_docs})}
    except Exception as e:
        if "does not exist" in str(e):
             raise HTTPException(status_code=404, detail=f"No documents have been uploaded to '{project_id}' yet.")
        raise HTTPException(status_code=500, detail=f"An error occurred during query: {str(e)}")