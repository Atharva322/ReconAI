from reconai_benchmark import GOLDEN_NORTHSTAR_TRUTH


def test_golden_truth_arithmetic_is_exact() -> None:
    truth = GOLDEN_NORTHSTAR_TRUTH

    assert truth["invoice_total_cents"] - truth["payment_received_cents"] == truth["claimed_deduction_cents"]
    assert (
        truth["claimed_deduction_cents"] - truth["authorized_promotion_cents"]
        == truth["unexplained_deduction_cents"]
    )
    assert truth["expected_workflow"] == "REVIEW_REQUIRED"
