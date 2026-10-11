"""Банк Python-контестов: пять направлений, четыре грейда, три сложности.

Шаблоны вызываются с rng при старте попытки. Некоторые генераторы пока
содержат фиксированные данные; абсолютная уникальность не гарантируется.
"""
from app.testing_bank.bank import TEMPLATES, Template, templates_for

__all__ = ["TEMPLATES", "Template", "templates_for"]
