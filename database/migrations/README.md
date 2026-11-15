# Database migrations

Startup creates missing tables with SQLAlchemy metadata and records the idempotent marker `5.0-additive-context-provenance` in `schema_migrations`. Version 5 adds provenance, revision history, scoped report links, context observations, receipts and the synthetic outbox; it does not delete existing measurements or replace the database.

The existing legacy measurement-identity upgrade remains additive and makes a backup before changing a legacy schema. Restarting is safe; tests verify preservation of a legacy measurement, backup creation and repeated initialization. This is a local SQLite prototype migration mechanism, not an Alembic deployment framework. Back up a production database before upgrading; never substitute the demonstration database for real records. Legacy rows without capture evidence remain explicitly unverified.
