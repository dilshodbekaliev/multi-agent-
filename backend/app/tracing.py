from app.config import settings

_langfuse_client = None


def get_langfuse_callbacks() -> list:
    global _langfuse_client

    if not (settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY):
        return []

    try:
        from langfuse import Langfuse
        from langfuse.langchain import CallbackHandler

        if _langfuse_client is None:
            _langfuse_client = Langfuse(
                public_key=settings.LANGFUSE_PUBLIC_KEY,
                secret_key=settings.LANGFUSE_SECRET_KEY,
                host=settings.LANGFUSE_HOST,
            )

        return [CallbackHandler()]
    except Exception:
        return []
