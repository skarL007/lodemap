---
id: "0001"
titulo: Structurizr as the source of the architecture
status: aceita
data: {{DATA}}
date: {{DATA}}
decisores: [owner]
elementos: [sistema]
substitui: []
substituida_por: []
evidencia:
  - workspace.dsl
  - scripts/atualizar.ps1
---

# Structurizr as the source of the architecture

## Context

The architecture has to be studied, changed and checked against the code, without diagrams that go stale on their own.

## Decision

The architecture lives in Structurizr (a C4 model in DSL), with one component per real module, status by color, code and
observability properties, and views by area, by flow and by status. The explorer, the docs reader, the derived documents
and the metrics are generated from the model itself by `scripts/atualizar.ps1`.

## Alternatives

- Hand-drawn diagrams (draw.io, Figma): quick to start, but nobody checks them against the code and they go stale.
- Text-only documentation: shows neither relationships nor the impact of a change.

## Consequences

Did the status of something change in the code? Change the tag and the `status` property in the DSL in the same commit.
A new module with no place in the model makes the coverage test fail.
