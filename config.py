"""集中設定：模型名稱、閾值、路徑。"""
import os


def _load_dotenv() -> None:
    """若專案根目錄有 .env，載入其變數（不覆蓋已存在的環境變數）。"""
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

# DeepSeek（OpenAI 相容 API）
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-flash"  # 便宜、快；要更強可換 "deepseek-v4-pro"

# 本機 Embedding（多語言：繁體中文 + 英文）
# 預設用 MiniLM：體積小、CPU 友善、速度比 BGE-M3 快很多；
# 要更高檢索品質可換回 "BAAI/bge-m3"（但 CPU 會慢 5~10 倍）
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# 每個要求檢索前幾段履歷當證據（供 LLM 判斷 + 引用原文）
TOP_K = 3
