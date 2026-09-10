"""Dataclasses Python pour manipulation en mémoire"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class Investment:
    """Classe mère générale pour les investissements"""
    symbol: str
    amount: Decimal
    entry_price: Decimal
    exit_price: Optional[Decimal] = None
    exit_price_2: Optional[Decimal] = None
    entry_date: datetime = field(default_factory=datetime.now)
    notes: str = ""


@dataclass
class SpotTrading(Investment):
    """Trading spot - achat/vente sur échange"""
    exchange: str = ""


@dataclass
class FuturesTrading(Investment):
    """Trading futures - avec effet de levier"""
    direction: str = "LONG"
    risk_reward_ratio: Optional[Decimal] = None
    feeling: str = ""
    why: str = ""
