from __future__ import annotations

from gigachat import GigaChat
from gigachat.exceptions import RequestEntityTooLargeError

from app.config import Settings


class ProviderConfigurationError(RuntimeError):
    pass


class GigaChatEmbeddingsProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: GigaChat | None = None

    def is_configured(self) -> bool:
        return bool(self._settings.gigachat_auth_key)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not self._settings.gigachat_auth_key:
            raise ProviderConfigurationError("GigaChat auth key is not configured")

        return [self._embed_single(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]

    def _get_client(self) -> GigaChat:
        if self._client is None:
            self._client = GigaChat(
                credentials=self._settings.gigachat_auth_key,
                scope=self._settings.gigachat_scope,
                base_url=self._settings.gigachat_base_url,
                auth_url=self._settings.gigachat_auth_url,
                verify_ssl_certs=self._settings.gigachat_verify_ssl,
                timeout=60.0,
            )
        return self._client

    def _embed_single(self, text: str) -> list[float]:
        client = self._get_client()
        candidate = text.strip()
        if not candidate:
            candidate = " "

        while True:
            try:
                response = client.embeddings(
                    texts=[candidate],
                    model=self._settings.gigachat_embedding_model,
                )
                return response.data[0].embedding
            except RequestEntityTooLargeError:
                if len(candidate) <= 300:
                    raise
                candidate = candidate[: max(int(len(candidate) * 0.8), 300)].strip()
