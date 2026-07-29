import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    LANGFUSE_PUBLIC_KEY: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    LANGFUSE_SECRET_KEY: str = os.getenv("LANGFUSE_SECRET_KEY", "")
    LANGFUSE_HOST: str = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    QDRANT_URL: str = os.getenv("QDRANT_URL", "")
    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")
    QDRANT_COLLECTION: str = "documents"

    LLM_MODEL: str = "gemini-flash-latest"
    EMBEDDING_MODEL: str = "models/gemini-embedding-001"
    EMBEDDING_DIM: int = 3072

    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "./data/company.db")

    MEMORY_DB_PATH: str = os.getenv("MEMORY_DB_PATH", "./data/memory.db")
    MEMORY_MAX_RAW_TURNS: int = 3

    # --- Deployment (F14) ---
    # Comma-separated list of allowed frontend origins for CORS.
    # Locally this is just localhost:3000; on Render, set FRONTEND_URL
    # to your Vercel URL (e.g. https://your-app.vercel.app).
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "")

    def allowed_origins(self) -> list[str]:
        origins = ["http://localhost:3000"]
        if self.FRONTEND_URL:
            origins.append(self.FRONTEND_URL)
        return origins

    def validate(self) -> list[str]:
        problems = []
        if not self.GOOGLE_API_KEY:
            problems.append("GOOGLE_API_KEY is missing — required (get one free at aistudio.google.com/apikey)")
        if not self.TAVILY_API_KEY:
            problems.append("TAVILY_API_KEY missing — web agent (F4) will skip gracefully")
        if not (self.LANGFUSE_PUBLIC_KEY and self.LANGFUSE_SECRET_KEY):
            problems.append("Langfuse keys missing — tracing (F12) will be disabled")
        return problems


settings = Settings()

if __name__ == "__main__":
    issues = settings.validate()
    print("Config loaded. LLM:", settings.LLM_MODEL)
    if issues:
        print("Notes:")
        for p in issues:
            print(" -", p)
    else:
        print("All keys present.")
