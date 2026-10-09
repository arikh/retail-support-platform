"""Turns text into vectors, with a model that runs on this machine.

This module is the only one that knows which embedding library and model are
in use. The model is loaded on first use (downloaded once, then read from the
local cache) and kept for the life of the process.

A vector made by one model can only be compared with vectors made by the
same model. So the model name is stored with every passage, and changing
EMBEDDING_MODEL means running the ingest again.
"""

from functools import cache

from fastembed import TextEmbedding

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIMENSIONS = 384  # must match vector(384) in sql/007


@cache
def _model() -> TextEmbedding:
    return TextEmbedding(EMBEDDING_MODEL)


def embed_passages(texts: list[str]) -> list[list[float]]:
    """One vector for each text that will be stored and searched."""
    return [vector.tolist() for vector in _model().passage_embed(texts)]


def embed_query(text: str) -> list[float]:
    """The vector of one question, to compare with the stored passages."""
    return next(iter(_model().query_embed([text]))).tolist()


def vector_literal(vector: list[float]) -> str:
    """A vector in the text form pgvector reads: "[0.1,0.2,0.3]"."""
    return "[" + ",".join(str(number) for number in vector) + "]"
