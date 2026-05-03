from __future__ import annotations

try:
    from openrouter import OpenRouter, errors
except ModuleNotFoundError:  # pragma: no cover - optional runtime dependency
    OpenRouter = None
    errors = None

from app.config import Settings


class ProviderConfigurationError(RuntimeError):
    pass


class OpenRouterEmbeddingsProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = (
            OpenRouter(
                api_key=settings.openrouter_api_key,
                http_referer=settings.openrouter_site_url,
                x_open_router_title=settings.openrouter_app_name,
                server_url=settings.openrouter_base_url,
                timeout_ms=60_000,
            )
            if OpenRouter is not None
            else None
        )

    def is_configured(self) -> bool:
        return bool(self._client and self._settings.openrouter_api_key and self._settings.openrouter_embedding_model)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not self.is_configured():
            raise ProviderConfigurationError("OpenRouter API key or embedding model is not configured")
        normalized = [self._normalize_text(text) for text in texts]
        return self._embed_batch(normalized)

    def embed_query(self, text: str) -> list[float]:
        if not self.is_configured():
            raise ProviderConfigurationError("OpenRouter API key or embedding model is not configured")
        return self._embed_batch([self._normalize_text(text)], input_type="query")[0]

    def _embed_batch(
        self,
        texts: list[str],
        input_type: str | None = None,
    ) -> list[list[float]]:
        if not texts:
            return []

        try:
            response = self._request_embeddings(texts, input_type=input_type)
            return self._extract_vectors(response, expected_count=len(texts))
        except Exception as exc:
            if self._should_split_batch(exc) and len(texts) > 1:
                middle = max(1, len(texts) // 2)
                return self._embed_batch(texts[:middle], input_type=input_type) + self._embed_batch(
                    texts[middle:],
                    input_type=input_type,
                )
            if self._should_truncate_single(exc) and len(texts) == 1:
                return [self._embed_single_with_truncation(texts[0], input_type=input_type)]
            raise

    def _embed_single_with_truncation(
        self,
        text: str,
        input_type: str | None = None,
    ) -> list[float]:
        candidate = text
        while True:
            try:
                response = self._request_embeddings([candidate], input_type=input_type)
                return self._extract_vectors(response, expected_count=1)[0]
            except Exception as exc:
                if not self._should_truncate_single(exc):
                    raise
                if len(candidate) <= 300:
                    raise
                candidate = candidate[: max(int(len(candidate) * 0.8), 300)].strip()
                if not candidate:
                    candidate = " "

    def _request_embeddings(self, texts: list[str], input_type: str | None = None):
        if self._client is None:
            raise ProviderConfigurationError("openrouter package is not installed")
        return self._client.embeddings.generate(
            input=texts,
            model=self._settings.openrouter_embedding_model,
            encoding_format="float",
            input_type=input_type,
        )

    @staticmethod
    def _extract_vectors(response, expected_count: int) -> list[list[float]]:
        data = getattr(response, "data", None)
        if not isinstance(data, list) or not data:
            raise RuntimeError("OpenRouter embeddings response does not contain vectors")
        ordered = sorted(
            data,
            key=lambda item: int(getattr(item, "index", 0) or 0),
        )
        vectors = [list(item.embedding) for item in ordered]
        if len(vectors) != expected_count:
            raise RuntimeError(
                f"OpenRouter embeddings response size mismatch: expected {expected_count}, got {len(vectors)}"
            )
        return vectors

    @staticmethod
    def _normalize_text(text: str) -> str:
        candidate = text.strip()
        return candidate if candidate else " "

    @staticmethod
    def _should_split_batch(exc: Exception) -> bool:
        if errors is None:
            return False
        return isinstance(
            exc,
            (
                errors.BadRequestResponseError,
                errors.PayloadTooLargeResponseError,
            ),
        )

    @staticmethod
    def _should_truncate_single(exc: Exception) -> bool:
        if errors is None:
            return False
        return isinstance(
            exc,
            (
                errors.BadRequestResponseError,
                errors.PayloadTooLargeResponseError,
            ),
        )
