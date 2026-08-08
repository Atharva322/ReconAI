from pathlib import Path

from reconai_domain import Money, ReconciliationInput, reconcile_payment
from reconai_domain.evaluate import evaluate_benchmark_reconciliation


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


def test_partial_payment_routes_to_partial_review() -> None:
    result = reconcile_payment(
        ReconciliationInput(
            invoice_number="NSB-INV-2001",
            payment_reference="PAY-NSB-2001",
            invoice_total=Money.parse("8000.00"),
            payment_received=Money.parse("6000.00"),
            authorized_promotion=Money.parse("0.00"),
            stated_deduction=Money.parse("0.00"),
            review_reason="partial_payment_open_balance",
        )
    )

    assert result.status == "PARTIAL_REVIEW"
    assert result.review_reason == "partial_payment_open_balance"
    assert result.deduction.claimed_deduction.amount_cents == 0
    assert result.deduction.unexplained_deduction.amount_cents == 0


def test_validation_error_overrides_other_status() -> None:
    result = reconcile_payment(
        ReconciliationInput(
            invoice_number="NSB-INV-3001",
            payment_reference="PAY-NSB-3001",
            invoice_total=Money.parse("10000.00"),
            payment_received=Money.parse("8750.00"),
            authorized_promotion=Money.parse("500.00"),
            validation_error="inconsistent_arithmetic",
        )
    )

    assert result.status == "VALIDATION_FAILED"
    assert result.review_reason == "inconsistent_arithmetic"


def test_phase4_benchmark_reconciliation_scores_all_scenarios() -> None:
    evaluation = evaluate_benchmark_reconciliation(Path.cwd())

    assert evaluation.scenario_count == 12
    assert evaluation.status_accuracy == 1
    assert evaluation.deduction_exact_accuracy == 1
    assert evaluation.confirmed_match_precision == 1
    assert evaluation.review_routing_recall == 1
    assert evaluation.false_auto_match_count == 0
