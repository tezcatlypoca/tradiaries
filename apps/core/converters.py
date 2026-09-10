"""Conversion entre dataclasses et modèles Django"""
from .entities import Investment as InvestmentEntity, SpotTrading as SpotTradingEntity, FuturesTrading as FuturesTradingEntity
from .models import SpotTrading, FuturesTrading


def spot_entity_to_model(entity: SpotTradingEntity) -> SpotTrading:
    """Convertir une dataclass SpotTrading en modèle Django"""
    return SpotTrading(
        symbol=entity.symbol,
        amount=entity.amount,
        entry_price=entity.entry_price,
        exit_price=entity.exit_price,
        exit_price_2=entity.exit_price_2,
        entry_date=entity.entry_date,
        notes=entity.notes,
        exchange=entity.exchange,
    )


def spot_model_to_entity(model: SpotTrading) -> SpotTradingEntity:
    """Convertir un modèle Django SpotTrading en dataclass"""
    return SpotTradingEntity(
        symbol=model.symbol,
        amount=model.amount,
        entry_price=model.entry_price,
        exit_price=model.exit_price,
        exit_price_2=model.exit_price_2,
        entry_date=model.entry_date,
        notes=model.notes,
        exchange=model.exchange,
    )


def futures_entity_to_model(entity: FuturesTradingEntity) -> FuturesTrading:
    """Convertir une dataclass FuturesTrading en modèle Django"""
    return FuturesTrading(
        symbol=entity.symbol,
        amount=entity.amount,
        entry_price=entity.entry_price,
        exit_price=entity.exit_price,
        exit_price_2=entity.exit_price_2,
        entry_date=entity.entry_date,
        notes=entity.notes,
        direction=entity.direction,
        risk_reward_ratio=entity.risk_reward_ratio,
        feeling=entity.feeling,
        why=entity.why,
    )


def futures_model_to_entity(model: FuturesTrading) -> FuturesTradingEntity:
    """Convertir un modèle Django FuturesTrading en dataclass"""
    return FuturesTradingEntity(
        symbol=model.symbol,
        amount=model.amount,
        entry_price=model.entry_price,
        exit_price=model.exit_price,
        exit_price_2=model.exit_price_2,
        entry_date=model.entry_date,
        notes=model.notes,
        direction=model.direction,
        risk_reward_ratio=model.risk_reward_ratio,
        feeling=model.feeling,
        why=model.why,
    )
