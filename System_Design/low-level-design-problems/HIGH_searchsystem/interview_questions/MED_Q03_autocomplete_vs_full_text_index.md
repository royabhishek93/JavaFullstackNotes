# MED Q03 - Autocomplete vs Full-Text Index

## Scenario
Can one index handle both autocomplete and full-text search well?

## Answer
Usually not optimally.
- Autocomplete needs prefix-oriented structures (edge n-grams, completion suggester).
- Full-text needs analyzers, stemming, ranking.
- Mixing them can increase index size and reduce quality.

## Interview One-Liner
Autocomplete is a prefix problem; full-text is a relevance problem.
