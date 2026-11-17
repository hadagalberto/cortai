"""Roteador de LLM: OpenRouter -> OpenAI -> Anthropic, com cooldown por provider."""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any

import requests

from pipeline.util import log


@dataclass
class Provider:
    name: str
    kind: str  # "openai" | "anthropic"
    base_url: str
    model: str
    key_env: str
    timeout: int = 120

    @property
    def key(self) -> str | None:
        return os.environ.get(self.key_env) or None

    @property
    def configured(self) -> bool:
        return bool(self.key)


class LLMRouter:
    def __init__(self, providers: list[Provider], cooldown_s: int = 180):
        self.providers = [p for p in providers if p.configured]
        self.cooldown_s = cooldown_s
        self._down_until: dict[str, float] = {}
        if self.providers:
            log(
                "[llm] providers: "
                + ", ".join(f"{p.name}({p.model})" for p in self.providers)
            )
        else:
            log("[llm] nenhum provider configurado -> classificacao heuristica")

    def __bool__(self) -> bool:
        return bool(self.providers)

    def _order(self) -> list[Provider]:
        now = time.time()
        ready = [p for p in self.providers if self._down_until.get(p.name, 0) <= now]
        return ready or self.providers

    def chat_json(
        self,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = 900,
    ) -> dict[str, Any]:
        return self._run(system, user, temperature, max_tokens, images=None)

    def chat_json_with_images(
        self,
        system: str,
        user: str,
        images: list[str],
        temperature: float = 0.3,
        max_tokens: int = 900,
    ) -> dict[str, Any]:
        return self._run(system, user, temperature, max_tokens, images=images)

    def _run(
        self,
        system: str,
        user: str,
        temperature: float,
        max_tokens: int,
        images: list[str] | None,
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        for prov in self._order():
            try:
                if prov.kind == "anthropic":
                    raw, usage = self._call_anthropic(
                        prov, system, user, temperature, max_tokens, images
                    )
                else:
                    raw, usage = self._call_openai(
                        prov, system, user, temperature, max_tokens, images
                    )
                data = _parse_json(raw)
                data["_provider"] = prov.name
                data["_model"] = prov.model
                data["_usage"] = usage
                return data
            except Exception as exc:
                last_error = exc
                self._down_until[prov.name] = time.time() + self.cooldown_s
                log(f"[llm] {prov.name} falhou ({exc}) -> proximo provider")
        raise RuntimeError(f"todos os providers falharam: {last_error}")

    # -- implementacoes ------------------------------------------------
    def _call_openai(
        self,
        prov: Provider,
        system: str,
        user: str,
        temperature: float,
        max_tokens: int,
        images: list[str] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        content: Any = user
        if images:
            content = [{"type": "text", "text": user}]
            content += [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                for b64 in images
            ]
        resp = requests.post(
            prov.base_url.rstrip("/") + "/chat/completions",
            headers={
                "Authorization": f"Bearer {prov.key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost",
                "X-Title": "cortai",
            },
            json={
                "model": prov.model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": content},
                ],
            },
            timeout=prov.timeout,
        )
        if resp.status_code >= 300:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        usage = data.get("usage") or {}
        return (
            data["choices"][0]["message"]["content"],
            {
                "in": int(usage.get("prompt_tokens") or 0),
                "out": int(usage.get("completion_tokens") or 0),
                # custo real cobrado pelo provedor (imagens tem preco proprio)
                "cost": float(usage.get("cost") or 0.0),
            },
        )

    def _call_anthropic(
        self,
        prov: Provider,
        system: str,
        user: str,
        temperature: float,
        max_tokens: int,
        images: list[str] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        content: Any = user
        if images:
            content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": b64,
                    },
                }
                for b64 in images
            ] + [{"type": "text", "text": user}]
        resp = requests.post(
            prov.base_url.rstrip("/") + "/messages",
            headers={
                "x-api-key": prov.key or "",
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": prov.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "system": system + "\nResponda somente JSON valido.",
                "messages": [{"role": "user", "content": content}],
            },
            timeout=prov.timeout,
        )
        if resp.status_code >= 300:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        blocks = data.get("content") or []
        usage = data.get("usage") or {}
        return (
            "".join(b.get("text", "") for b in blocks if b.get("type") == "text"),
            {
                "in": int(usage.get("input_tokens") or 0),
                "out": int(usage.get("output_tokens") or 0),
                "cost": float((data.get("usage") or {}).get("cost") or 0.0),
            },
        )


def _parse_json(raw: str) -> dict[str, Any]:
    txt = (raw or "").strip()
    if txt.startswith("```"):
        txt = re.sub(r"^```[a-zA-Z]*\s*", "", txt)
        txt = re.sub(r"\s*```$", "", txt)
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", txt, re.DOTALL)
        if not m:
            raise
        return json.loads(m.group(0))


def router_from_config(cfg: dict[str, Any]) -> LLMRouter:
    providers = [Provider(**p) for p in cfg.get("providers", [])]
    return LLMRouter(providers, cooldown_s=int(cfg.get("cooldown_s", 180)))
