// Enriquecimento do modelo, rodado pelo DSL (!script) a cada carga do workspace.
//
// 1. Perspectivas: cada propriedade de estudo (status, código, observabilidade...) vira uma perspectiva.
//    No diagrama, o botão de perspectivas destaca quem tem aquela informação e mostra o valor no próprio nó.
// 2. Link do elemento: o primeiro caminho de "codigo" abre o arquivo no GitHub (ícone de link no nó).
// 3. Animação: toda visão estática ganha passos na ordem do fluxo (das entradas para as dependências),
//    para estudar a visão camada por camada com os botões de animação do Lite.
// Não edite os elementos aqui: mude os .dsl. Este script só deriva informação do que já está declarado.

import com.structurizr.model.*
import com.structurizr.view.*

// Base dos links de código: a propriedade "repo.blob" do workspace (ver workspace.dsl). "-" = sem link.
def REPO = (workspace.properties ?: [:])["repo.blob"] ?: ""
if (REPO == "-") REPO = ""  // o DSL não aceita propriedade vazia
def PERSPECTIVAS = [
    "status"         : "Status",
    "area"           : "Área",
    "codigo"         : "Código",
    "spec"           : "Especificação",
    "observabilidade": "Observabilidade",
    "metricas"       : "Métricas",
    "equipe"         : "Equipe",
    "nota"           : "Nota",
    "ramo"           : "Ramo",
]

workspace.model.elements.each { e ->
    def p = e.properties ?: [:]
    PERSPECTIVAS.each { chave, nome ->
        def valor = p[chave]
        if (valor) {
            // O valor da perspectiva Status colore o destaque; nas outras, vai o texto inteiro.
            e.addPerspective(nome, valor.toString(), chave == "status" ? valor.toString() : "")
        }
    }
    def codigo = p["codigo"]
    // Código que mora em outro ramo (propriedade "ramo") não tem link: o arquivo não existe no ramo do REPO.
    if (REPO && codigo && !e.url && !p["ramo"]) {
        def primeiro = codigo.toString().split(/[,;\s]+/).find { it.contains("/") || it.contains(".") }
        if (primeiro) {
            primeiro = primeiro.replaceAll(/[`()]/, "").replaceAll(/:\d+.*$/, "")
            try { e.url = REPO + primeiro } catch (ignored) { }
        }
    }
}

def views = []
views.addAll(workspace.views.systemLandscapeViews)
views.addAll(workspace.views.systemContextViews)
views.addAll(workspace.views.containerViews)
views.addAll(workspace.views.componentViews)

views.each { v ->
    def ids = v.elements.collect { it.element } as Set
    def rels = v.relationships.collect { it.relationship }
    def entrada = [:].withDefault { 0 }
    def saida = [:].withDefault { [] }
    rels.each { r ->
        if (ids.contains(r.source) && ids.contains(r.destination) && r.source != r.destination) {
            entrada[r.destination] = entrada[r.destination] + 1
            saida[r.source] << r.destination
        }
    }
    def raizes = ids.findAll { entrada[it] == 0 && saida[it] }
    if (!raizes) { raizes = ids.findAll { it instanceof Person } }
    if (!raizes) { raizes = [ids.max { saida[it].size() }] }

    def visto = [] as Set
    def camadas = []
    def atual = raizes as List
    while (atual) {
        atual = atual.findAll { !visto.contains(it) }
        if (!atual) break
        visto.addAll(atual)
        camadas << atual
        atual = atual.collectMany { saida[it] }.unique()
    }
    def resto = ids.findAll { !visto.contains(it) }
    if (resto) camadas << (resto as List)

    // No máximo 8 passos: as camadas mais fundas se juntam no último.
    while (camadas.size() > 8) {
        def ult = camadas.remove(camadas.size() - 1)
        camadas[-1] = camadas[-1] + ult
    }
    if (camadas.size() > 1) {
        camadas.each { c -> v.addAnimation(c as Element[]) }
    }
}
