# AI-Powered Enterprise Management Platform

A compact full-stack AI enterprise operations platform demonstrating authentication, RBAC, CRUD APIs, relational persistence, and an LLM-powered operations copilot.

## Architecture

React dashboard → FastAPI REST API → SQLAlchemy ORM → SQLite. The copilot endpoint gathers application context and sends it to an OpenAI-compatible API when configured.

## Stack

Python, FastAPI, SQLAlchemy, SQLite, Pydantic, PyJWT, bcrypt, React, JavaScript, CSS, OpenAI-compatible API.

## Features

- JWT bearer authentication with 12-hour expiration
- bcrypt password hashing
- Reusable role authorization
- User, project and task APIs
- Automatic schema creation and demo seeding
- AI copilot with demo fallback
- React dashboard
- Automated API tests

## Run

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Environment

Copy `.env.example` into your environment. `SECRET_KEY` signs JWTs. `OPENAI_API_KEY` is optional; without it the copilot runs in transparent demo mode.

## Demo accounts

- admin@example.com / admin123
- manager@example.com / manager123
- employee@example.com / employee123

These credentials are for local demonstration only.

## Testing

```bash
cd backend
pytest -q
```
