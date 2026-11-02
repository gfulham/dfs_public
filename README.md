# Weekly DFS Lineup Optimizer

A Python-based NFL Daily Fantasy Sports (DFS) lineup optimizer that combines player projections and salaries from a Snowflake data warehouse to generate high-projected-point DraftKings lineups.

## Features

- **Snowflake integration:** Retrieves player projections, salaries, and value metrics from the analytics data warehouse.
- **Player selection:** Ranks players by projected points per $1,000 of salary to build candidate pools by position.
- **Lineup optimization:** Uses NumPy vectorization and precomputed player combinations to efficiently evaluate lineups under a salary cap.
- **Roster constraints:** Builds valid lineups with 1 QB, 2 RBs, 3 WRs, 1 TE, 1 FLEX, and 1 DST.
- **Exposure management:** Limits individual player exposure across selected lineups to improve lineup diversity.
- **Performance optimization:** Processes combinations in chunks and prunes lineups that cannot meet salary constraints to reduce memory usage.

## Tech Stack

Python, Pandas, NumPy, Snowflake SQL, and Jupyter Notebook.

## Workflow

1. Connect to Snowflake and retrieve player projections and salaries.
2. Rank players by value and create position-specific candidate pools.
3. Precompute player combinations and evaluate salary and projection totals.
4. Filter invalid combinations and retain high-scoring candidate lineups.
5. Select a final set of lineups while enforcing player exposure limits and avoiding duplicates.

## Purpose

This project demonstrates data warehouse integration, analytical SQL, vectorized computation, combinatorial optimization, and resource-efficient processing of large search spaces for fantasy sports analytics.
