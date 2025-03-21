# GameFriend

An AI-powered gaming companion that helps you navigate through game guides using natural language. Built with Next.js and FastAPI.

## Features

- **Guide Management**: Download and organize game guides from GameFAQs
- **AI Chat Interface**: Interact with guides using natural language
- **Modern Web Interface**: Clean, responsive UI built with Next.js
- **Real-time Updates**: Instant feedback and chat responses

## Prerequisites

- Python 3.10 or higher
- Node.js 18 or higher
- Mistral API key

## Installation

### Backend Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/gamefriend.git
   cd gamefriend
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install poetry
   poetry install
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your Mistral API key
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   pnpm install
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env.local
   # Edit .env.local with your backend API URL
   ```

## Running the Application

1. Start the backend server:
   ```bash
   # From the project root
   poetry run uvicorn gamefriend.main:app --reload
   ```

2. Start the frontend development server:
   ```bash
   # From the frontend directory
   pnpm dev
   ```

3. Open your browser and navigate to `http://localhost:3000`

## Development

### Backend (FastAPI)

- Run tests:
  ```bash
  poetry run pytest
  ```

- Type checking:
  ```bash
  poetry run mypy .
  ```

- Linting:
  ```bash
  poetry run flake8
  ```

### Frontend (Next.js)

- Run tests:
  ```bash
  pnpm test
  ```

- Type checking:
  ```bash
  pnpm type-check
  ```

- Linting:
  ```bash
  pnpm lint
  ```

## Project Structure

```
gamefriend/
├── frontend/           # Next.js frontend application
│   ├── src/
│   │   ├── components/  # Reusable UI components
│   │   ├── pages/      # Next.js pages
│   │   ├── api/        # API client code
│   │   └── styles/     # CSS and styling
│   └── public/         # Static assets
│
├── gamefriend/         # FastAPI backend application
│   ├── api/           # API endpoints
│   ├── chat/          # Chat functionality
│   ├── guide/         # Guide management
│   ├── models/        # Data models
│   └── utils/         # Utility functions
│
└── tests/             # Test files
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 