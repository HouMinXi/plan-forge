# F2 Fail Fixture

A plan where one noun-phrase bigram appears in three or more sections.

## Background

The DatabaseConnection Pool manages all database access.
DatabaseConnection Pool is initialized at startup.

## Design

DatabaseConnection Pool is used by every service layer.
DatabaseConnection Pool settings are in config.yaml.

## Implementation

DatabaseConnection Pool must be closed gracefully on shutdown.
DatabaseConnection Pool size defaults to ten.

## Testing

DatabaseConnection Pool is verified under load.

## Summary

The phrase "databaseconnection pool" appears in Background, Design,
Implementation, and Testing sections, which should trigger F2.
