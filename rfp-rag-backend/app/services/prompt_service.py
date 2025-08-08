# Auto-generated during refactor (corrected)
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
import models
import auth
from app.deps import get_db
import crud, schemas

def get_prompt_functions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    return crud.get_prompt_functions(db=db)

def create_prompt_function(
    function_data: schemas.PromptFunctionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    existing = crud.get_prompt_function_by_name(db, function_name=function_data.function_name)
    if existing:
        raise HTTPException(status_code=400, detail="A function with this name already exists.")
    return crud.create_prompt_function(db, function=function_data)

def update_prompt_function(
    function_id: int,
    function_update: schemas.PromptFunctionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    db_function = crud.update_prompt_function(db, function_id, function_update)
    if not db_function:
        raise HTTPException(status_code=404, detail="Prompt function not found.")
    return db_function

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
