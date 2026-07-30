from functools import cached_property
from importlib import import_module
from typing import Any


class SemanticDependencyError(RuntimeError):
    pass


class SentenceTransformerScorer:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    @cached_property
    def model(self) -> Any:
        try:
            module = import_module("sentence_transformers")
        except ImportError as error:
            raise SemanticDependencyError(
                "Semantic matching requires the semantic dependency group."
            ) from error
        return module.SentenceTransformer(self.model_name)

    def similarity(self, left: str, right: str) -> float:
        vectors = self.model.encode([left, right], normalize_embeddings=True)
        value = float(vectors[0] @ vectors[1])
        return (value + 1.0) / 2.0
