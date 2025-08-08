# Auto-generated during refactor (complete blocks)
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os, shutil, tempfile, traceback, re
import crud, models, schemas, auth
from app.deps import get_db
from app.core.config import PROJECTS_DIRECTORY, DB_DIRECTORY, KNOWLEDGE_BASE_DIRECTORY, APP_ENV
from app.services.document_service import process_document, sanitize_name_for_directory, num_tokens_from_string

router = APIRouter()

@router.post("/knowledge-base/upload/")
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


@router.get("/knowledge-base/documents/", response_model=List[schemas.KnowledgeBaseDocument])
def get_knowledge_base_documents(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    return crud.get_knowledge_base_documents(db)

# FIX: Corrected the download endpoint path


@router.get("/knowledge-base/{document_name}")
async def download_knowledge_base_document(document_name: str, current_user: models.User = Depends(auth.get_current_active_user)):
    file_path = os.path.join(KNOWLEDGE_BASE_DIRECTORY, document_name)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Document not found")
    return FileResponse(path=file_path, filename=document_name)

# FIX: Corrected the delete endpoint path


@router.delete("/knowledge-base/{document_name}", status_code=204)
async def delete_knowledge_base_document(document_name: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    clean_document_name = document_name.strip()
    
    file_path_to_delete = os.path.join(KNOWLEDGE_BASE_DIRECTORY, clean_document_name)

    try:
        client = chromadb.PersistentClient(path=DB_DIRECTORY)
        collection = client.get_collection(name="knowledge_base")
        collection.delete(where={"source": os.path.join(KNOWLEDGE_BASE_DIRECTORY, document_name)})
        print(f"Deleted vectors for source: {document_name}")
    except Exception as e:
        print(f"Could not delete vectors for {document_name}: {e}")

    if os.path.isfile(file_path_to_delete):
        os.remove(file_path_to_delete)
        crud.delete_knowledge_base_document(db, clean_document_name)
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
