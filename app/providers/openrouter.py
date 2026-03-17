from __future__ import annotations

import json

from openrouter import OpenRouter

from app.config import Settings
from app.providers.gigachat import ProviderConfigurationError


class OpenRouterProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = OpenRouter(
            api_key=settings.openrouter_api_key,
            http_referer=settings.openrouter_site_url,
            x_title=settings.openrouter_app_name,
            server_url=settings.openrouter_base_url,
            timeout_ms=60_000,
        )

    def is_configured(self) -> bool:
        return bool(self._settings.openrouter_api_key and self._settings.openrouter_model)

    def complete(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
        if not self.is_configured():
            raise ProviderConfigurationError("OpenRouter API key or model is not configured")
        response = self._client.chat.send(
            model=self._settings.openrouter_model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or ""

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict:
        if not self.is_configured():
            raise ProviderConfigurationError("OpenRouter API key or model is not configured")

        response = self._client.chat.send(
            model=self._settings.openrouter_model,
            temperature=0.0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        raw = response.choices[0].message.content or "{}"
        return json.loads(raw)
