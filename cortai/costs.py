"""Custo real por chamada: ASR usa segundos de audio, LLM usa tokens da resposta."""

from __future__ import annotations

from typing import Any


def asr_cost(cfg: dict[str, Any], backend: str | None, seconds: float,
             api_cost: float | None = None) -> float:
    if api_cost:
        return round(float(api_cost), 6)
    if not backend or seconds <= 0:
        return 0.0
    per_min = float((cfg.get("asr") or {}).get(backend, 0.0) or 0.0)
    return round(seconds / 60.0 * per_min, 6)


def llm_cost(cfg: dict[str, Any], model: str | None, usage: dict[str, Any] | None) -> float:
    if not usage:
        return 0.0
    # o provedor devolve o custo exato (inclui preco de imagem); a tabela e fallback
    if float(usage.get("cost") or 0) > 0:
        return round(float(usage["cost"]), 6)
    if not model:
        return 0.0
    table = cfg.get("llm") or {}
    price = table.get(model) or table.get("default") or {"in": 0.5, "out": 2.0}
    return round(
        int(usage.get("in", 0)) / 1e6 * float(price.get("in", 0.0))
        + int(usage.get("out", 0)) / 1e6 * float(price.get("out", 0.0)),
        6,
    )


def brl(cfg: dict[str, Any], usd: float) -> float:
    return round(usd * float(cfg.get("brl_per_usd", 5.4)), 2)
