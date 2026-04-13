# AB Test Results: kanker_nl

## Aggregate Metrics

| Variant | Chunks | Avg Words | Recall@5 | Precision@5 | MRR | vs Baseline |
|---------|--------|-----------|----------|-------------|-----|-------------|
| A_baseline | 5114 | 281.5 | 0.733 | 0.373 | 0.511 | — |
| B_sentence | 5853 | 242.1 | 0.800 | 0.440 | 0.717 | +9.1% / +17.9% / +40.4% |
| C_paragraph | 4498 | 282.7 | 0.733 | 0.360 | 0.609 | +0.0% / -3.6% / +19.4% |
| D_semantic | 2882 | 441.3 | 0.833 | 0.440 | 0.633 | +13.6% / +17.9% / +24.0% |
| E_hybrid | 10582 | 240.4 | 0.767 | 0.480 | 0.631 | +4.5% / +28.6% / +23.5% |

## Per-Category Breakdown

### Living With

| Variant | Recall@5 | Precision@5 | MRR |
|---------|----------|-------------|-----|
| A_baseline | 0.500 | 0.260 | 0.353 |
| B_sentence | 0.700 | 0.340 | 0.450 |
| C_paragraph | 0.400 | 0.200 | 0.208 |
| D_semantic | 0.600 | 0.300 | 0.358 |
| E_hybrid | 0.400 | 0.200 | 0.233 |

### Symptom

| Variant | Recall@5 | Precision@5 | MRR |
|---------|----------|-------------|-----|
| A_baseline | 0.800 | 0.320 | 0.412 |
| B_sentence | 0.900 | 0.460 | 0.900 |
| C_paragraph | 0.900 | 0.440 | 0.850 |
| D_semantic | 1.000 | 0.460 | 0.692 |
| E_hybrid | 1.000 | 0.540 | 0.900 |

### Treatment

| Variant | Recall@5 | Precision@5 | MRR |
|---------|----------|-------------|-----|
| A_baseline | 0.900 | 0.540 | 0.767 |
| B_sentence | 0.800 | 0.520 | 0.800 |
| C_paragraph | 0.900 | 0.440 | 0.770 |
| D_semantic | 0.900 | 0.560 | 0.850 |
| E_hybrid | 0.900 | 0.700 | 0.758 |

## Decision

**Result: SHIP `B_sentence`** -- Recall@5 +9.1%, MRR +40.4% over baseline.