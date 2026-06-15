# VB V2 Research Policy

## Frozen OOS

The years **2024, 2025, and 2026 are frozen out-of-sample data**.

They must not be used for:

- strategy design;
- parameter selection;
- filter selection;
- feature or bucket analysis;
- debugging a candidate's trading behavior;
- comparing V2 candidates.

All VB V2 development and selection uses **2015-2023 only**. The V2 engine
enforces this boundary and refuses to load a market-data file dated 2024 or
later.

OOS data may only be evaluated after a V2 candidate and its evaluation protocol
have been frozen in writing.

## Selection Priorities

Candidates are judged in this order:

1. no lookahead or timing ambiguity;
2. controlled initial risk and executable position size;
3. stability across years;
4. performance under execution-cost stress;
5. return.

No candidate may be selected only because it has the highest aggregate return.
