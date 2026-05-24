"""The fixed fund catalog defined by the challenge.

Single source of truth for the five funds. Both the seed script and the test
fixtures build from this list so the data never diverges.
"""

from __future__ import annotations

from app.domain.entities.fund import Fund
from app.domain.value_objects.enums import FundCategory
from app.domain.value_objects.money import Money

FUND_CATALOG: list[Fund] = [
    Fund("1", "FPV_BTG_PACTUAL_RECAUDADORA", Money.of(75_000), FundCategory.FPV),
    Fund("2", "FPV_BTG_PACTUAL_ECOPETROL", Money.of(125_000), FundCategory.FPV),
    Fund("3", "DEUDAPRIVADA", Money.of(50_000), FundCategory.FIC),
    Fund("4", "FDO-ACCIONES", Money.of(250_000), FundCategory.FIC),
    Fund("5", "FPV_BTG_PACTUAL_DINAMICA", Money.of(100_000), FundCategory.FPV),
]
