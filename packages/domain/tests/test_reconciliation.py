from reconai_domain import Money, ReconciliationInput, reconcile_payment


def test_golden_northstar_deduction_routes_unexplained_amount_to_review() -> None:
    result = reconcile_payment(
        ReconciliationInput(
            invoice_number="NSB-INV-1001",
            payment_reference="PAY-NORTHSTAR-0001",
            invoice_total=Money.parse("18450.00"),
            payment_received=Money.parse("17200.00"),
            authorized_promotion=Money.parse("1000.00"),
            promotion_code="PROMO-SUMMER-1000",
        )
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.matched_cents == 1_720_000
    assert result.deduction.claimed_deduction.amount_cents == 125_000
    assert result.deduction.validated_deduction.amount_cents == 100_000
    assert result.deduction.unexplained_deduction.amount_cents == 25_000
    assert "UNEXPLAINED_DEDUCTION_REVIEW" in result.rule_codes


def test_exact_payment_has_no_deduction() -> None:
    result = reconcile_payment(
        ReconciliationInput(
            invoice_number="NSB-INV-1002",
            payment_reference="PAY-NORTHSTAR-0002",
            invoice_total=Money.parse("250.00"),
            payment_received=Money.parse("250.00"),
            authorized_promotion=Money.parse("0.00"),
        )
    )

    assert result.status == "MATCHED"
    assert result.deduction.claimed_deduction.amount_cents == 0
