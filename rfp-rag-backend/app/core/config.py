# Auto-generated during refactor
import os
from dotenv import load_dotenv
load_dotenv()

APP_ENV = os.getenv("APP_ENV", "development")
PROJECTS_DIRECTORY = os.getenv("PROJECTS_DIRECTORY", "./rfp_projects")
DB_DIRECTORY = os.getenv("DB_DIRECTORY", "./chroma_db")
KNOWLEDGE_BASE_DIRECTORY = os.getenv("KNOWLEDGE_BASE_DIRECTORY", "./knowledge_base")
EXAMPLES_DIRECTORY = os.getenv("EXAMPLES_DIRECTORY", "./proposal_examples/")
EXAMPLES_COLLECTION = os.getenv("EXAMPLES_COLLECTION", "examples")

# Reuse existing
db_dir = DB_DIRECTORY  # already defined elsewhere in your config

# New (examples library)
EXAMPLES_DIRECTORY = os.getenv("EXAMPLES_DIRECTORY", "./proposal_examples/")
EXAMPLES_COLLECTION = os.getenv("EXAMPLES_COLLECTION", "examples")

# CORS
origins = [
    "http://localhost:3000",
    "https://rfp-rag-app.azurewebsites.net",
    "https://ai.avatar-computing.com",
    "https://rfp-rag-app-fgguhaezgmekczgg.eastus2-01.azurewebsites.net"
]
