from __future__ import annotations

from sentence_transformers import CrossEncoder

from app.config import Settings


class Reranker:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model: CrossEncoder | None = None

    def rerank(self, query: str, documents: list[str]) -> list[float]:
        if not documents:
            return []
        if self._model is None:
            self._model = CrossEncoder(self._settings.reranker_model)
        results = self._model.rank(query, documents)
        scores = [0.0] * len(documents)
        for item in results:
            corpus_id = item.get("corpus_id")
            if corpus_id is None:
                continue
            if 0 <= corpus_id < len(documents):
                scores[corpus_id] = float(item["score"])
        return scores
