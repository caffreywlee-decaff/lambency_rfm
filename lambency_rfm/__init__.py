"""lambency_rfm — 주문 CSV → 가중 RFM 등급 · 모양 · 전이표. 파라미터는 전부 열려 있다.

    from lambency_rfm import load_orders, score, summarize, migrate
"""
from .core import (DEFAULT_CUTS, DEFAULT_TIERS, DEFAULT_WEIGHTS, DORMANT, NEW, load_orders, migrate, parse_cuts, parse_weights,
                   score, shape, summarize)

__all__ = ["DEFAULT_CUTS", "DEFAULT_TIERS", "DEFAULT_WEIGHTS", "DORMANT", "NEW", "load_orders", "migrate", "parse_cuts",
           "parse_weights", "score", "shape", "summarize"]
__version__ = "0.1.0"
