from __future__ import annotations

from decimal import Decimal

from .invoices import Invoice, InvoiceLine


def load_invoice(invoice_id: str) -> Invoice:
    return Invoice(
        id=invoice_id,
        customer_id="demo-customer",
        lines=[
            InvoiceLine("subscription", 1, Decimal("49.00")),
            InvoiceLine("usage", 12, Decimal("0.25")),
        ],
        tax_rate=Decimal("0.10"),
    )


def invoice_total_for_id(invoice_id: str) -> Decimal:
    from .invoices import invoice_total

    return invoice_total(load_invoice(invoice_id))
