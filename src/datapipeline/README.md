### Base vs. Fine-tuned Gemini (phishing classifier)

**Eval set:** 200 held-out emails (stratified sample)  

| Metric                | Base `gemini-2.0-flash-001` | Fine-tuned Gemini | Change              |
|-----------------------|-----------------------------|-------------------|---------------------|
| Accuracy              | 0.925                       | **0.990**         | +0.065 (≈ +7% rel.) |
| Precision (scam)      | 0.933                       | **0.981**         | fewer false alarms  |
| Recall (scam)         | 0.925                       | **1.000**         | caught all scams    |
| F1 (scam)             | 0.929                       | **0.991**         |                     |
| Precision (benign)    | 0.916                       | **1.000**         | never mislabeled benign as scam |
| Recall (benign)       | 0.926                       | **0.979**         | fewer good emails flagged |
| F1 (benign)           | 0.921                       | **0.989**         |                     |
| False positive rate   | 0.035                       | **0.010**         | 3.5% → 1.0%         |
| False negative rate   | 0.040                       | **0.000**         | 4.0% → 0%           |
| FP count              | 7                           | **2**             |                     |
| FN count              | 8                           | **0**             |                     |
| Total errors          | 15                          | **2**             | ~**86% fewer** errors |
| Avg latency (sec)     | 0.464                       | **0.616**         | slightly slower (~+33%) |
| # examples            | 200                         | 200               |                     |