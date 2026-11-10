# Integração opcional com o Synapse

Lido pelo orquestrador só quando o projeto usa o Synapse (escopo `synapse` consentido). Sem Synapse, pule este arquivo: o pipeline não depende dele.

O Synapse entra como **contexto e registro**, nunca como autor do modelo. Script: `scripts/synapse_ponte.py`, que usa só
a biblioteca padrão e lê o endereço e o token de `~/.claude.json`, sem nunca imprimi-los. Sem Synapse, o script grava o
motivo e sai com 0, e o pipeline segue normalmente.

1. **Antes do modelador** (mapa novo ou mudança estrutural):
   `python ~/.claude/skills/lodemap/scripts/synapse_ponte.py contexto --repo <repo> --arq <pasta da arquitetura>`.
   O script grava `.lodemap/synapse-contexto.json` com as lições do projeto, buscadas com o **`projeto` explícito**
   (calculado pelo git common-dir, o mesmo valor no checkout e nos worktrees), e as notas da busca híbrida. O modelador
   lê esse arquivo junto com o inventário. As lições e notas são **contexto, não verdade**: cada uma é conferida no
   código antes de virar componente, relação ou status. Quando uma lição for usada, cite o `id` dela.
2. **Depois do gate aprovado:**
   - `synapse_ponte.py observar --repo <repo> --arq <pasta>` mostra a observação (nota, pendências, commit);
   - com `--aplicar`, grava a observação pelo `synapse_add_observation`, na entidade `arquitetura:<projeto>`.
   Rode o `--aplicar` só na sessão do dono ou com autorização dele.
3. **Lição nova** (um defeito da skill, um ponto cego do `ast`, um corte de componente que deu errado):
   - só pelo `synapse_record_learning_scoped`, com `projeto`, `autor` e evidência no formato `caminho:linha` ou
     `comando -> resultado`;
   - a lição vai para a quarentena, e o dono aprova com `synapse learnings`;
   - nada de `synapse_record_learning` sem escopo, `synapse_porteiro` ou `synapse_consolidate_session`, porque esses
     enviam conteúdo a provedores externos.
4. **Desfecho:** para cada lição citada, registre `synapse_learning_outcome` com `ajudou`, `nao_ajudou` ou `neutro`, e
   com `ref` igual ao commit do mapa.
5. **Fora da v1:** os tickets do Synapse por área. Quem orquestra é o Claude Code.
