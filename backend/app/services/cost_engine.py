from decimal import Decimal
from datetime import datetime

class CostEngine:
    @staticmethod
    def calculate_earned_value(budget_at_completion: Decimal, progress_pct: int) -> Decimal:
        """EV = BAC * % Complete"""
        return budget_at_completion * (Decimal(progress_pct) / Decimal(100))

    @staticmethod
    def calculate_cpi(earned_value: Decimal, actual_cost: Decimal) -> float:
        """CPI = EV / AC"""
        if actual_cost == 0:
            return 1.0 if earned_value == 0 else 9.99  # Avoid division by zero
        return float(earned_value / actual_cost)

    @staticmethod
    def calculate_eac(budget_at_completion: Decimal, cpi: float) -> Decimal:
        """EAC = BAC / CPI"""
        if cpi == 0:
            return budget_at_completion
        return budget_at_completion / Decimal(cpi)

    @staticmethod
    def calculate_burn_rate(actual_cost: Decimal, start_date: datetime) -> Decimal:
        """Daily Burn Rate = AC / Days Elapsed"""
        s_date = start_date.replace(tzinfo=None)
        days_elapsed = (datetime.utcnow() - s_date).days
        if days_elapsed <= 0:
            return actual_cost
        return actual_cost / Decimal(days_elapsed)
