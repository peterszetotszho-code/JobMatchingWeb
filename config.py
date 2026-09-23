"""Central settings: model names, paths."""
import os


def _load_dotenv() -> None:
    """Load a .env file from the project root (does not override existing env vars)."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())


_load_dotenv()

# DeepSeek (OpenAI-compatible API)
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-flash"  # cheap & fast; switch to "deepseek-v4-pro" for stronger reasoning

# Local embeddings (multilingual: Traditional Chinese + English)
# MiniLM by default: small, CPU-friendly, much faster than BGE-M3;
# switch back to "BAAI/bge-m3" for higher retrieval quality (but ~5-10x slower on CPU)
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Number of resume chunks to retrieve per requirement (used as evidence for the LLM)
TOP_K = 3
