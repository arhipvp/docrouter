import os
import asyncio
from typing import Optional

import aiohttp


class LLMClient:
    """Asynchronous client for interacting with an LLM service.

    Parameters
    ----------
    api_key: str
        API key for authentication.
    model: str
        Name of the model to use.
    max_concurrent_requests: int
        Maximum number of parallel requests allowed.
    """

    def __init__(self, api_key: str, model: str, max_concurrent_requests: int = 5):
        self.api_key = api_key
        self.model = model
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

    async def _post(self, session: aiohttp.ClientSession, prompt: str) -> aiohttp.ClientResponse:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"model": self.model, "messages": [{"role": "user", "content": prompt}]}
        async with self.semaphore:
            return await session.post(self.base_url, headers=headers, json=payload)

    async def generate(self, prompt: str, *, max_retries: int = 3, retry_delay: float = 1.0) -> str:
        """Send a prompt to the LLM with retry on rate limit.

        Retries are attempted when the API returns HTTP 429. The delay between
        retries grows linearly with the attempt count.
        """
        for attempt in range(max_retries):
            async with aiohttp.ClientSession() as session:
                response = await self._post(session, prompt)
                if response.status == 429:  # Rate limit exceeded
                    await asyncio.sleep(retry_delay * (attempt + 1))
                    continue
                response.raise_for_status()
                data = await response.json()
                return data["choices"][0]["message"]["content"]
        raise RuntimeError("Maximum retries exceeded for LLM request")

    def generate_sync(self, prompt: str, **kwargs) -> str:
        """Synchronous wrapper around the asynchronous generate method."""
        return asyncio.run(self.generate(prompt, **kwargs))
