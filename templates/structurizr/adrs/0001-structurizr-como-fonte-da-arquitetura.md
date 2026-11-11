---
id: "0001"
titulo: Structurizr como fonte da arquitetura
status: aceita
data: {{DATA}}
date: {{DATA}}
decisores: [dono]
elementos: [sistema]
substitui: []
substituida_por: []
evidencia: []
---

# Structurizr como fonte da arquitetura

## Contexto

A arquitetura precisa ser estudada, alterada e conferida contra o código, sem diagramas que envelhecem sozinhos.

## Decisão

A arquitetura vive no Structurizr (modelo C4 em DSL), com um componente por módulo real, status por cor, propriedades
de código e de observabilidade e visões por área, por fluxo e por status. Explorador, leitor de documentação,
documentos derivados e métricas são gerados do próprio modelo pelo atualizador do Lodemap (`scripts/atualizar.ps1`).

## Alternativas

- Diagramas desenhados à mão (draw.io, Figma): rápidos de começar, mas ninguém confere contra o código e envelhecem.
- Só documentação em texto: não mostra relações nem impacto de mudança.

## Consequências

Mudou o status de algo no código? Muda a tag e a propriedade `status` no DSL no mesmo commit. Módulo novo sem lugar
no modelo faz o teste de cobertura falhar.
