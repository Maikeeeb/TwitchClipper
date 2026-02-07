# Architecture overview (template)

Use this document to describe how the system is structured. Keep it concise and
current; update it when major decisions change.

## Data flow

Describe how data moves through the system from inputs to outputs. Include
major services, storage, and boundary interfaces.

## Module boundaries

List the main modules/services and their responsibilities. Note any strict
boundaries (e.g., UI never calls DB directly).

## Key invariants

Define invariants that must always hold (e.g., deterministic output for same
input, idempotent writes, strict validation rules).

## Decision log (optional)

Record important architectural decisions and tradeoffs.
