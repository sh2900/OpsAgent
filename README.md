

\# OpsAgent – Multi-Agent IT Helpdesk Automation



OpsAgent is an AI-powered IT helpdesk automation system that uses multiple AI agents to classify IT issues, diagnose problems, recommend fixes, execute permitted actions, verify results, and escalate unresolved tickets.



\## Features



\- \*\*AI Triage:\*\* Classifies tickets by category and urgency.

\- \*\*AI Diagnosis:\*\* Identifies possible causes using service status and ticket evidence.

\- \*\*AI Resolution:\*\* Executes permitted automated actions and verifies outcomes.

\- \*\*Human Escalation:\*\* Escalates issues that cannot be safely resolved.

\- \*\*Authentication:\*\* JWT-based authentication with Admin and Employee roles.

\- \*\*Employee Portal:\*\* Submit and track IT support tickets.

\- \*\*Admin Dashboard:\*\* Monitor tickets, agent activity, statistics and escalations.

\- \*\*Ticket Storage:\*\* MongoDB persistence.



\## Technology Stack



| Component | Technology |

|---|---|

| Backend API | FastAPI |

| Frontend | Streamlit |

| AI Agents | LangChain |

| Local LLM | Ollama – Qwen3 4B |

| Database | MongoDB |

| Authentication | JWT, Argon2 |

| Testing | Pytest |



\## Prerequisites



\- Windows 10 or 11

\- Python 3.12 or newer (64-bit)

\- Git

\- Ollama (for local LLM execution)

\- MongoDB Atlas account or an accessible MongoDB instance



A dedicated GPU is not required. Ollama can run using CPU, although inference may be slower.



\## Installation



\### 1. Clone the repository



```cmd

git clone <YOUR\_GITHUB\_REPOSITORY\_URL>

cd opsagent

```



\### 2. Run setup



Install Ollama first if you intend to use it.



Run:



```cmd

setup.bat

```



This script creates the Python virtual environment, installs dependencies, prepares the environment file and attempts to download Qwen3 4B when Ollama is installed.



\### 3. Configure environment variables



Open `.env` in a text editor:



```cmd

notepad .env

```



Configure the following:



\- `LLM\_PROVIDER`: gemini, groq or ollama.

\- `LLM\_MODEL`: model name.

\- `MONGO\_URI`: your MongoDB connection string.

\- `MONGO\_DB`: database name.

\- `JWT\_SECRET\_KEY`: generate your own secure secret.

\- `ADMIN\_USERNAME`: initial administrator username.

\- `ADMIN\_PASSWORD`: initial administrator password.



For Ollama:



```env

LLM\_PROVIDER=ollama

LLM\_MODEL=qwen3:4b

```



For Gemini or Groq, configure the corresponding API key.



Generate a JWT secret using:



```cmd

python -c "import secrets; print(secrets.token\_urlsafe(48))"

```



Never commit your `.env` file or share your credentials.



\### 4. Start OpsAgent



Run:



```cmd

start.bat

```



The script starts the simulator, FastAPI backend and Streamlit dashboard.



\## Access the Application



| Service | URL |

|---|---|

| Streamlit Dashboard | http://localhost:8501 |

| FastAPI Documentation | http://localhost:8000/docs |

| Simulator Documentation | http://localhost:8001/docs |



Log in using the administrator credentials configured in `.env`.



Administrators can create employee accounts through the application API.



\## Running Tests



From the project directory:



```cmd

.venv\\Scripts\\python.exe -m pytest -v

```



\## Project Structure



```text

opsagent/

├── agents/

│   ├── diagnostic.py

│   ├── llm.py

│   ├── resolution.py

│   ├── tools.py

│   └── triage.py

├── backend/

│   ├── auth.py

│   ├── config.py

│   ├── db.py

│   ├── main.py

│   ├── models.py

│   └── orchestrator.py

├── dashboard/

├── sim\_backend/

├── tests/

├── data/

├── requirements.txt

├── .env.example

├── .gitignore

├── setup.bat

└── start.bat

```



\## Security Notes



\- Never commit `.env` or API credentials.

\- Each developer should generate their own JWT secret.

\- Use strong administrator passwords.

\- Configure MongoDB network access appropriately.

\- Do not expose development servers publicly.



\---



Developed as a multi-agent AI IT helpdesk automation project.
