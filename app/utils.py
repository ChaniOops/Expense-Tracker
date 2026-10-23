"""Utility and formatting helper functions for Expense Tracker."""

from decimal import Decimal


def format_inr(value, include_symbol=True):
    """Format a numeric monetary amount using the Indian numbering system.

    Examples:
        150.00 -> '₹150.00'
        1250.00 -> '₹1,250.00'
        12500.00 -> '₹12,500.00'
        125000.00 -> '₹1,25,000.00'
        -1250.50 -> '-₹1,250.50'
    """
    if value is None or value == '':
        return "₹0.00" if include_symbol else "0.00"

    try:
        dec_val = Decimal(str(value))
    except Exception:
        symbol = "₹" if include_symbol else ""
        return f"{symbol}{value}"

    is_negative = dec_val < 0
    abs_val = abs(dec_val)

    # Format with 2 decimal places
    formatted_num = f"{abs_val:.2f}"
    int_part, dec_part = formatted_num.split(".")

    if len(int_part) <= 3:
        grouped_int = int_part
    else:
        last_three = int_part[-3:]
        remaining = int_part[:-3]
        pairs = []
        while len(remaining) > 2:
            pairs.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            pairs.insert(0, remaining)
        grouped_int = ",".join(pairs) + "," + last_three

    symbol = "₹" if include_symbol else ""
    formatted_result = f"{symbol}{grouped_int}.{dec_part}"
    return f"-{formatted_result}" if is_negative else formatted_result
