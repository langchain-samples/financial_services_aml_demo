"""AML Transaction Flagging Evaluation Package.

This package provides comprehensive evaluation tools for the AML transaction
flagging system, including:
- LLM-as-a-Judge evaluators for qualitative assessment
- Rule-based evaluators for quantitative metrics
- Curated test datasets with 14+ test cases
- Integration with LangSmith evaluation UI
"""

# Rule-based evaluators
from evaluation.aml_evaluator import (
    evaluate_transaction_flagging,
    evaluate_false_positive_rate,
    evaluate_false_negative_rate,
    evaluate_severity_distribution,
)

# LLM-as-a-Judge evaluators
from evaluation.llm_judge_evaluator import (
    aml_llm_judge,
    llm_judge_evaluator,
)

# Test dataset
from evaluation.test_dataset import get_test_dataset, get_dataset_summary

__all__ = [
    # Rule-based evaluators
    "evaluate_transaction_flagging",
    "evaluate_false_positive_rate",
    "evaluate_false_negative_rate",
    "evaluate_severity_distribution",
    # LLM judge evaluators
    "aml_llm_judge",
    "llm_judge_evaluator",
    # Dataset
    "get_test_dataset",
    "get_dataset_summary",
]
