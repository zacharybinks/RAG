# Getting Started with Create React App

This project was bootstrapped with [Create React App](https://github.com/facebook/create-react-app).

## Available Scripts

In the project directory, you can run:

### `npm start`

Runs the app in the development mode.\
Open [http://localhost:3000](http://localhost:3000) to view it in your browser.

The page will reload when you make changes.\
You may also see any lint errors in the console.

### `npm test`

Launches the test runner in the interactive watch mode.\
See the section about [running tests](https://facebook.github.io/create-react-app/docs/running-tests) for more information.

### `npm run build`

Builds the app for production to the `build` folder.\
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.\
Your app is ready to be deployed!

See the section about [deployment](https://facebook.github.io/create-react-app/docs/deployment) for more information.

### `npm run eject`

**Note: this is a one-way operation. Once you `eject`, you can't go back!**

If you aren't satisfied with the build tool and configuration choices, you can `eject` at any time. This command will remove the single build dependency from your project.

Instead, it will copy all the configuration files and the transitive dependencies (webpack, Babel, ESLint, etc) right into your project so you have full control over them. All of the commands except `eject` will still work, but they will point to the copied scripts so you can tweak them. At this point you're on your own.

You don't have to ever use `eject`. The curated feature set is suitable for small and middle deployments, and you shouldn't feel obligated to use this feature. However we understand that this tool wouldn't be useful if you couldn't customize it when you are ready for it.

## Learn More

You can learn more in the [Create React App documentation](https://facebook.github.io/create-react-app/docs/getting-started).

To learn React, check out the [React documentation](https://reactjs.org/).

### Code Splitting

This section has moved here: [https://facebook.github.io/create-react-app/docs/code-splitting](https://facebook.github.io/create-react-app/docs/code-splitting)

### Analyzing the Bundle Size

This section has moved here: [https://facebook.github.io/create-react-app/docs/analyzing-the-bundle-size](https://facebook.github.io/create-react-app/docs/analyzing-the-bundle-size)

### Making a Progressive Web App

This section has moved here: [https://facebook.github.io/create-react-app/docs/making-a-progressive-web-app](https://facebook.github.io/create-react-app/docs/making-a-progressive-web-app)

### Advanced Configuration

This section has moved here: [https://facebook.github.io/create-react-app/docs/advanced-configuration](https://facebook.github.io/create-react-app/docs/advanced-configuration)

### Deployment

This section has moved here: [https://facebook.github.io/create-react-app/docs/deployment](https://facebook.github.io/create-react-app/docs/deployment)

### `npm run build` fails to minify

This section has moved here: [https://facebook.github.io/create-react-app/docs/troubleshooting#npm-run-build-fails-to-minify](https://facebook.github.io/create-react-app/docs/troubleshooting#npm-run-build-fails-to-minify)

1. Core Technology & Library Overview
This section details the key Python libraries that power the backend and their specific roles in the application.

Web & API Framework
FastAPI: A modern, high-performance web framework for building APIs. It's used to define all the endpoints (e.g., /users/, /rfps/{project_id}/query/) and handle incoming web requests. Its key features are speed and automatic interactive documentation.

Uvicorn: The ASGI (Asynchronous Server Gateway Interface) server that runs the FastAPI application. It's the production-grade server that listens for HTTP requests and passes them to FastAPI.

Database & ORM
PostgreSQL: A powerful, open-source object-relational database system. It's used as the primary database to store persistent data like users, projects, and chat history.

SQLAlchemy: The Python SQL toolkit and Object-Relational Mapper (ORM). It allows us to interact with the PostgreSQL database using Python classes and objects (models.py) instead of writing raw SQL queries.

Psycopg2-binary: The most popular PostgreSQL database adapter for Python. It's the low-level driver that allows SQLAlchemy to communicate with the PostgreSQL database.

Alembic: A lightweight database migration tool for SQLAlchemy. It allows us to manage changes to our database schema over time. When we change our models.py file (e.g., add a new table or column), Alembic can automatically generate and apply the necessary SQL commands to update the live database without losing data.

Authentication & Security
Passlib[bcrypt]: A comprehensive password hashing library. We use it to securely hash user passwords before storing them in the database, which is a critical security practice.

Python-jose: A library for encoding, decoding, and verifying JSON Web Tokens (JWTs). JWTs are used to manage user sessions. After a user logs in, the server issues a signed token, which the frontend then includes in the header of every subsequent request to prove the user is authenticated.

AI & LangChain Core
LangChain: The primary framework used to build the RAG application. It provides the "glue" to connect all the different AI components.

langchain_community.document_loaders (PyPDFLoader): Used to load and parse text content from uploaded PDF files.

langchain.text_splitter (RecursiveCharacterTextSplitter): Used to break down long documents into smaller, semantically related chunks.

langchain_openai (OpenAIEmbeddings, ChatOpenAI): Provides integrations with OpenAI's services. We use it to generate vector embeddings for our text chunks and to access the GPT model for generating answers.

langchain_community.vectorstores (Chroma): The interface to our vector database. It handles storing, managing, and searching through the document vectors.

langchain.chains (ConversationalRetrievalChain): The core LangChain "chain" that orchestrates the entire RAG process: taking a question and chat history, retrieving relevant documents, and generating a context-aware answer.

langchain.prompts (PromptTemplate): Allows us to create dynamic, reusable prompts to instruct the AI on how to behave, including setting its persona and telling it to use Markdown.

ChromaDB: An open-source vector database used to store the embeddings of the document chunks. It's highly efficient at finding the most relevant text chunks based on a user's query.

OpenAI: The official Python client for the OpenAI API. LangChain uses this library under the hood to make calls to the GPT models.

Tiktoken: The tokenizer used by OpenAI. LangChain uses it to accurately count tokens, which is important for managing context window limits and costs.

Utilities
Pydantic: A data validation and settings management library. We use it extensively in schemas.py to define the expected shape of our API request and response bodies, ensuring data integrity.

Python-dotenv: A simple library for managing environment variables. It loads sensitive information (like API keys and database URLs) from a .env file into the application's environment, so we don't have to hardcode them in our source code.

2. File-by-File Breakdown
The backend is structured with a clear separation of concerns, making it easier to maintain and scale.

main.py: This is the heart of the application. It initializes the FastAPI app, includes all the API endpoint definitions (the @app.post, @app.get functions), and ties together the logic from all the other files. It handles the web layer of the application.

database.py: This file is responsible for a single task: setting up the connection to the PostgreSQL database. It creates the SQLAlchemy engine and the SessionLocal class, which is used to create new database sessions for each API request.

models.py: This file defines the structure of our database tables using Python classes. Each class (e.g., User, RfpProject) maps to a table in the database, and its attributes (e.g., username, name) map to columns. This is the "M" in the Model-View-Controller pattern.

schemas.py: This file contains the Pydantic models that define the data shapes for our API. For example, UserCreate defines that a new user must have a username and a password. FastAPI uses these schemas to validate incoming request data and to format outgoing response data, ensuring a consistent and reliable API contract.

crud.py: This file contains all the functions that directly interact with the database to perform Create, Read, Update, and Delete operations. By centralizing all database logic here, we keep our API endpoints in main.py clean and focused on handling the request and response, rather than the details of database transactions.

auth.py: This file centralizes all logic related to security and authentication. It contains functions for hashing and verifying passwords, creating and decoding JWTs, and the critical get_current_user dependency that FastAPI uses to protect endpoints and identify which user is making a request.

.env: A configuration file that is not committed to source control. It holds all the secrets and environment-specific settings for the application, such as your OpenAI API key, database connection string, and JWT secret key.

alembic/ & alembic.ini: This directory and configuration file are managed by the Alembic library. The versions/ subdirectory contains the individual migration scripts that represent changes to your database schema over time. You should not edit these files manually; they are managed by the alembic command-line tool.

3. Architectural Notes & Data Flow
Dependency Injection: You'll notice db: Session = Depends(get_db) in many endpoint functions. This is a powerful feature of FastAPI called dependency injection. It automatically creates a new database session for each request, passes it to the function, and ensures it's closed afterward, which is a very efficient and safe way to handle database connections.

User-Scoped Data: All major resources (like RFP Projects) are tied to a owner_id. The API endpoints are designed to only ever fetch or modify data belonging to the currently authenticated user, ensuring that users cannot see or interact with each other's projects.

Stateless Authentication: The use of JWTs makes the API "stateless." The server doesn't need to keep track of who is logged in. Each request from the frontend is self-contained and proves its authenticity by including the JWT, which is a highly scalable authentication method.

Hybrid Storage: The application uses a hybrid storage model. Relational data (users, projects, settings, chat history) is stored in PostgreSQL for its structure and reliability. The AI-specific, high-dimensional vector data is stored in ChromaDB for its specialized search capabilities. The raw uploaded PDF files are stored on the file system.