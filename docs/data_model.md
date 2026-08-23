# Data Model

**Status: placeholder.** This document will be completed in Phase 3 of the
implementation plan, alongside `sql/01_create_schema.sql`.

It will describe the PostgreSQL-compatible star schema built on top of the
cleaned data in `data/processed/`:

- **Fact tables:** `fact_usage_events`, `fact_feedback`, `fact_training_attendance`
- **Dimension tables:** `dim_user`, `dim_date`, `dim_feature`, `dim_business_unit`, `dim_role`

For each table this document will specify the grain, primary/foreign keys,
and relationships to other tables, plus an entity-relationship diagram.
