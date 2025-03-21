from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from gamefriend.api import router as api_router

app = FastAPI(title="GameFriend API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Welcome to GameFriend API"} 