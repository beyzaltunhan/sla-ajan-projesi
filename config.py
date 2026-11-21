"""Proje yapılandırması. Ortam değişkeniyle değiştirilebilir değerler büyük harfli adlarla okunur."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"
DB_DIR = ROOT / "chroma_db"
COLLECTION = os.getenv("SLA_COLLECTION", "sla_belgeleri_v1")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "embeddinggemma")
CHAT_MODEL = os.getenv("CHAT_MODEL", "qwen3.5:4b")

# embeddinggemma önerilen önekleri (model kartı). Kullanım kararı önek denemesine göre verilir.
SORGU_ONEKI = "task: search result | query: "
DOKUMAN_ONEKI = "title: none | text: "
ONEK_KULLAN = os.getenv("EMBED_ONEK", "1") == "1"
