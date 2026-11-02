# Statistical Methodology

## Guiding rules

1. State the estimand, observation unit, and inclusion criteria.
2. Prefer methods matched to data sparsity (e.g., Wilson CI for proportions).
3. Correct for multiple testing when screening many hypotheses.
4. Never interpret FAERS-derived ROR as relative risk or causation.
5. Do not estimate incidence without a valid population denominator.

## Implemented methods

### Confidence intervals

- **Mean (Student-t):** independent continuous observations, n≥2.
- **Proportion (Wilson score):** preferred over Wald for sparse proportions.

### Hypothesis tests

- Welch’s t-test (unequal variances)
- Mann–Whitney U
- Chi-square test of independence (+ Cramer’s V)
- Fisher’s exact test (2×2)

All results carry an observational / non-causal warning.

### Exploratory safety signals — Reporting Odds Ratio

For a defined reporting universe counted at the **report** level:

- \(a\) = reports with drug and event  
- \(b\) = reports with drug without event  
- \(c\) = reports with event without drug  
- \(d\) = reports with neither  

\[\mathrm{ROR} = \frac{a \times d}{b \times c}\]

- Zero cells: optional Haldane–Anscombe continuity correction (default 0.5).
- CI: Woolf logit interval on \(\log(\mathrm{ROR})\).
- Minimum count threshold on \(a\) (default 3) flagged via `min_count_ok`.
- Multiple comparisons: Benjamini–Hochberg for screening p-values when used.

**Label:** `exploratory_reporting_signal` — not a validated safety conclusion.

## Reproducibility

Analyses should record: dataset snapshot / batch_id, filters, software versions,
random seeds (when applicable), and output paths under `reports/statistical/`.
