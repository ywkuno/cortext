from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class InvoiceLine:
    description: str
    quantity: int
    unit_price: Decimal


@dataclass(frozen=True)
class Invoice:
    id: str
    customer_id: str
    lines: list[InvoiceLine]
    tax_rate: Decimal


def subtotal(invoice: Invoice) -> Decimal:
    total = Decimal("0")
    for line in invoice.lines:
        total += line.unit_price * line.quantity
    return total


def tax(invoice: Invoice) -> Decimal:
    return subtotal(invoice) * invoice.tax_rate


def invoice_total(invoice: Invoice) -> Decimal:
    return subtotal(invoice) + tax(invoice)


def render_invoice_summary(invoice: Invoice) -> str:
    return f"{invoice.id}: {invoice_total(invoice):.2f}"
