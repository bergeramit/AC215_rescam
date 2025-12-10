#!/usr/bin/env python3
"""
Compare baseline and fine-tuned model metrics.
Usage:
  python3 compare_models.py --baseline baseline_metrics.json --finetuned finetuned_metrics.json
"""
import argparse
import json
import sys


def load_metrics(filepath):
    """Load metrics from JSON file."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: File not found: {filepath}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in {filepath}: {e}")
        sys.exit(1)


def format_percentage(value):
    """Format value as percentage."""
    return f"{value * 100:.1f}%"


def format_change(baseline, finetuned):
    """Format change between baseline and fine-tuned."""
    diff = finetuned - baseline
    sign = "+" if diff >= 0 else ""
    return f"{sign}{diff * 100:.1f}%"


def compare_metrics(baseline, finetuned):
    """Compare and display metrics."""
    print("=" * 70)
    print("Model Comparison: Baseline vs Fine-Tuned")
    print("=" * 70)
    print()
    
    # Model IDs
    print(f"Baseline Model: {baseline.get('model_id', 'unknown')}")
    print(f"Fine-Tuned Model: {finetuned.get('model_id', 'unknown')}")
    print()
    
    # Metrics comparison
    metrics_to_compare = [
        ('accuracy', 'Accuracy'),
        ('precision_scam', 'Precision (scam)'),
        ('recall_scam', 'Recall (scam)'),
        ('f1_scam', 'F1 Score (scam)'),
        ('precision_benign', 'Precision (benign)'),
        ('recall_benign', 'Recall (benign)'),
        ('f1_benign', 'F1 Score (benign)'),
        ('false_positive_rate', 'False Positive Rate'),
        ('false_negative_rate', 'False Negative Rate'),
    ]
    
    print("Metrics Comparison:")
    print("-" * 70)
    print(f"{'Metric':<30} {'Baseline':<15} {'Fine-Tuned':<15} {'Change':<15}")
    print("-" * 70)
    
    for key, label in metrics_to_compare:
        base_val = baseline.get(key, 0)
        fine_val = finetuned.get(key, 0)
        
        if base_val is None or fine_val is None:
            continue
            
        print(f"{label:<30} {format_percentage(base_val):<15} {format_percentage(fine_val):<15} {format_change(base_val, fine_val):<15}")
    
    print("-" * 70)
    print()
    
    # Confusion matrix comparison
    print("Confusion Matrix:")
    print("-" * 70)
    print("Baseline:")
    print(f"  True Positives:  {baseline.get('tp', 0)}")
    print(f"  True Negatives:  {baseline.get('tn', 0)}")
    print(f"  False Positives: {baseline.get('fp', 0)}")
    print(f"  False Negatives: {baseline.get('fn', 0)}")
    print()
    print("Fine-Tuned:")
    print(f"  True Positives:  {finetuned.get('tp', 0)}")
    print(f"  True Negatives:  {finetuned.get('tn', 0)}")
    print(f"  False Positives: {finetuned.get('fp', 0)}")
    print(f"  False Negatives: {finetuned.get('fn', 0)}")
    print()
    
    # Latency comparison
    print("Latency:")
    print("-" * 70)
    base_latency = baseline.get('latency_avg_sec', 0)
    fine_latency = finetuned.get('latency_avg_sec', 0)
    print(f"Baseline Average: {base_latency:.3f}s")
    print(f"Fine-Tuned Average: {fine_latency:.3f}s")
    if base_latency > 0:
        latency_change = ((fine_latency - base_latency) / base_latency) * 100
        print(f"Change: {latency_change:+.1f}%")
    print()
    
    # Summary
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    
    accuracy_improvement = finetuned.get('accuracy', 0) - baseline.get('accuracy', 0)
    fpr_improvement = baseline.get('false_positive_rate', 0) - finetuned.get('false_positive_rate', 0)
    fnr_improvement = baseline.get('false_negative_rate', 0) - finetuned.get('false_negative_rate', 0)
    
    if accuracy_improvement > 0:
        print(f"✅ Accuracy improved by {format_percentage(accuracy_improvement)}")
    else:
        print(f"⚠️  Accuracy changed by {format_percentage(accuracy_improvement)}")
    
    if fpr_improvement > 0:
        print(f"✅ False Positive Rate reduced by {format_percentage(fpr_improvement)}")
    else:
        print(f"⚠️  False Positive Rate changed by {format_percentage(-fpr_improvement)}")
    
    if fnr_improvement > 0:
        print(f"✅ False Negative Rate reduced by {format_percentage(fnr_improvement)}")
    else:
        print(f"⚠️  False Negative Rate changed by {format_percentage(-fnr_improvement)}")
    
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Compare baseline and fine-tuned model metrics"
    )
    parser.add_argument(
        '--baseline',
        required=True,
        help='Path to baseline metrics JSON file'
    )
    parser.add_argument(
        '--finetuned',
        required=True,
        help='Path to fine-tuned metrics JSON file'
    )
    
    args = parser.parse_args()
    
    baseline = load_metrics(args.baseline)
    finetuned = load_metrics(args.finetuned)
    
    compare_metrics(baseline, finetuned)


if __name__ == "__main__":
    main()


