# DRED Python API

The competition pipeline now exposes the core Defensive Re-Expansion Debt calculation as a provider-agnostic Python API.

```python
from defensive_recovery import compute_dred, standardize_width

z_width = standardize_width(
    width=[34.0, 31.0, 29.0, 32.0],
    median_width=35.0,
    robust_scale=2.0,
)
metrics = compute_dred(z_width, fps=10.0)

print(metrics.intensity)
print(metrics.integral)
```

## Definition

For contextual defensive-width z-score `z_width(t)` and abnormality threshold `tau`:

`contraction(t) = max(-z_width(t) - tau, 0)`

The default is `tau=1.0`, matching the Analytics Cup implementation.

`compute_dred(...)` returns:

- `integral`: sum of contraction excess divided by tracking frequency, in z-score seconds;
- `intensity`: mean contraction excess across observed samples;
- `peak`: largest contraction excess;
- `fraction`: fraction of samples with positive abnormal contraction;
- `n_samples`, `threshold_z`, and `fps` for provenance.

`standardize_width(...)` is optional. It converts raw defensive width to robust z-scores using a caller-supplied contextual median and positive robust scale. The competition pipeline estimates those references separately by match, defending team and out-of-possession phase, but the DRED API deliberately does not force that baseline strategy.

## Design boundary

The API computes the metric only. Detecting a line break, defining the recovery window, estimating contextual baselines and choosing an external validation outcome are separate analytical decisions. Keeping these steps separate makes the metric reusable and prevents the library function from silently encoding competition-specific labels.
