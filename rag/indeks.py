"""Chroma indeksi (kalıcı, kosinüs mesafesi). Skor = kosinüs MESAFESİ: küçük = daha benzer."""
from __future__ import annotations

import shutil
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_ollama import OllamaEmbeddings

import config
from rag.parcala import dokumanlari_parcala


class OnekliEmbedding(Embeddings):
    """OllamaEmbeddings'i sarar; embeddinggemma için sorgu/doküman önekleri ekler."""

    def __init__(self, onek: bool | None = None):
        self.onek = config.ONEK_KULLAN if onek is None else onek
        self._e = OllamaEmbeddings(model=config.EMBED_MODEL, base_url=config.OLLAMA_URL)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self.onek:
            texts = [config.DOKUMAN_ONEKI + t for t in texts]
        return self._e.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._e.embed_query((config.SORGU_ONEKI if self.onek else "") + text)


def vektor_deposu(db_dir: Path | None = None, koleksiyon: str | None = None,
                  onek: bool | None = None) -> Chroma:
    return Chroma(
        collection_name=koleksiyon or config.COLLECTION,
        embedding_function=OnekliEmbedding(onek),
        persist_directory=str(db_dir or config.DB_DIR),
        collection_metadata={"hnsw:space": "cosine"},
    )


def indeksi_sifirla(db_dir: Path | None = None) -> None:
    """Yalnızca config.DB_DIR silinebilir; başka bir yol verilirse reddedilir."""
    hedef = Path(db_dir or config.DB_DIR).resolve()
    if hedef != config.DB_DIR.resolve():
        raise ValueError(f"Reddedildi: silinecek yol DB_DIR değil: {hedef}")
    if hedef.exists():
        shutil.rmtree(hedef)


def indeks_olustur(db_dir: Path | None = None, koleksiyon: str | None = None,
                   onek: bool | None = None, sifirla: bool = True) -> Chroma:
    if sifirla:
        indeksi_sifirla(db_dir)
    parcalar = dokumanlari_parcala()
    belgeler = [Document(page_content=p["metin"],
                         metadata={"dokuman": p["dokuman"], "madde": p["madde"]}) for p in parcalar]
    ids = [f'{p["dokuman"]}:{p["madde"]}' for p in parcalar]
    depo = vektor_deposu(db_dir, koleksiyon, onek)
    depo.add_documents(belgeler, ids=ids)
    return depo
