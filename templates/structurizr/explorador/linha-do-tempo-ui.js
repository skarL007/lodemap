/* Linha do tempo usa somente snapshots históricos normalizados por identificador.
   Rota própria (#linha-do-tempo), texto no dicionário do explorador (data-i18n), cores relidas ao trocar o tema,
   layout dagre e nós do tamanho do rótulo. window.LodemapLinhaDoTempo = {abrir, fechar, aberto}. */
(function () {
  'use strict';
  const centro = document.getElementById('centro'), esq = document.getElementById('esq');
  if (!centro || !esq) return;
  const HASH = '#linha-do-tempo', MARGEM = 24, FONTE = 12, MAX_TEXTO = 150, PAD = 10;
  const I = window.LodemapIdioma, rota = window.LodemapRota || {};
  if (I && I.dicionario) {
    Object.assign(I.dicionario.pt, {
      tlTitulo: 'Linha do tempo', tlAria: 'Linha do tempo da arquitetura', tlSair: 'Voltar ao mapa',
      tlIntro: 'Selecione uma versão para ver o mapa daquela data. Evidências de saúde atuais não são aplicadas ao histórico.',
      tlTocar: 'Tocar evolução', tlPausar: 'Pausar evolução', tlVersoes: 'Versões da arquitetura',
      tlLegenda: ['◆ Entrou', '◌ Saiu', '■ Mudou', '● Sem alteração', '━━ Relação nova', '┄┄ Relação removida'],
      tlVisao: 'Visão histórica', tlMais: 'Ampliar grafo', tlMenos: 'Reduzir grafo', tlEnquadrar: 'Enquadrar',
      tlInspecionar: 'Inspecionar componente', tlEscolha: 'Selecione um componente', tlGrafoAria: 'Grafo da versão selecionada',
      tlInspVazio: 'Selecione um componente no grafo para ver seu histórico.', tlCarregando: 'Carregando versões…',
      tlNenhuma: 'Nenhuma versão disponível. Gere a linha do tempo para este mapa.',
      tlIndisp: 'Dados indisponíveis para esta versão.', tlVisaoIndisp: 'Visão indisponível', tlCompIndisp: 'Componente indisponível',
      tlInspIndisp: 'Nenhum componente disponível nesta versão.', tlTudo: 'Modelo inteiro',
      tlTraducao: 'Tradução', tlSemAlt: 'Sem alteração arquitetural', tlTrabalho: 'Trabalho não commitado', tlTrab: 'Trabalho',
      tlNaoCommit: 'Não commitado', tlTrabMin: 'trabalho', tlAlteracoes: n => n + (n === 1 ? ' alteração' : ' alterações'),
      tlSemDesc: 'Sem descrição nesta versão.', tlHistorico: 'Histórico do componente', tlSemHist: 'Sem alterações registradas.',
      tlEntrou: 'entrou', tlSaiu: 'saiu', tlMudou: 'mudou',
      tlDica: 'Zoom mínimo legível: arraste o grafo para ver o resto.',
      tlRelease: 'release', tlMapa: 'mapa'
    });
    Object.assign(I.dicionario.en, {
      tlTitulo: 'Timeline', tlAria: 'Architecture timeline', tlSair: 'Back to the map',
      tlIntro: 'Pick a version to see the map as of that date. Current health evidence is not applied to history.',
      tlTocar: 'Play evolution', tlPausar: 'Pause evolution', tlVersoes: 'Architecture versions',
      tlLegenda: ['◆ Added', '◌ Removed', '■ Changed', '● Unchanged', '━━ New relation', '┄┄ Removed relation'],
      tlVisao: 'Historical view', tlMais: 'Zoom in', tlMenos: 'Zoom out', tlEnquadrar: 'Fit',
      tlInspecionar: 'Inspect component', tlEscolha: 'Select a component', tlGrafoAria: 'Graph of the selected version',
      tlInspVazio: 'Select a component in the graph to see its history.', tlCarregando: 'Loading versions…',
      tlNenhuma: 'No version available. Generate the timeline for this map.',
      tlIndisp: 'No data for this version.', tlVisaoIndisp: 'View unavailable', tlCompIndisp: 'Component unavailable',
      tlInspIndisp: 'No component available in this version.', tlTudo: 'Whole model',
      tlTraducao: 'Translation', tlSemAlt: 'No architectural change', tlTrabalho: 'Uncommitted work', tlTrab: 'Work',
      tlNaoCommit: 'Uncommitted', tlTrabMin: 'work', tlAlteracoes: n => n + (n === 1 ? ' change' : ' changes'),
      tlSemDesc: 'No description in this version.', tlHistorico: 'Component history', tlSemHist: 'No changes recorded.',
      tlEntrou: 'added', tlSaiu: 'removed', tlMudou: 'changed',
      tlDica: 'Minimum readable zoom: drag the graph to see the rest.',
      tlRelease: 'release', tlMapa: 'map'
    });
  }
  const t = (k, ...a) => I ? I.t(k, ...a) : k;
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  const sec = document.createElement('section');
  sec.id = 'timelinePanel'; sec.hidden = true; sec.tabIndex = -1; sec.setAttribute('data-i18n-aria', 'tlAria');
  sec.innerHTML = '<div class="tl-cab"><div><strong data-i18n="tlTitulo"></strong><p data-i18n="tlIntro"></p></div>' +
    '<button class="botao" id="tlSair" data-i18n="tlSair"></button></div>' +
    '<div class="tl-controles"><button class="botao" id="tlTocar" data-i18n="tlTocar"></button><span id="tlEstado" role="status"></span></div>' +
    '<div class="tl-trilho" id="tlTrilho" role="group" data-i18n-aria="tlVersoes"></div>' +
    '<div class="tl-legenda">' + [0, 1, 2, 3, 4, 5].map(n => '<span data-tl-leg="' + n + '"></span>').join('') + '</div>' +
    '<div class="tl-filtros"><label for="tlVisao" data-i18n="tlVisao"></label><select id="tlVisao"></select>' +
    '<button class="botao" id="tlMais" data-i18n-aria="tlMais">+</button><button class="botao" id="tlMenos" data-i18n-aria="tlMenos">−</button>' +
    '<button class="botao" id="tlEnquadrar" data-i18n="tlEnquadrar"></button></div>' +
    '<small id="tlDica" hidden></small>' +
    '<label for="tlComponentes" data-i18n="tlInspecionar"></label><select id="tlComponentes"></select>' +
    '<div class="tl-corpo"><div id="tlGrafo" role="img" data-i18n-aria="tlGrafoAria"></div><aside id="tlInspetor" aria-live="polite"></aside></div>';
  centro.appendChild(sec);
  const abrirBtn = document.createElement('button');
  abrirBtn.className = 'item'; abrirBtn.id = 'tlAbrir'; abrirBtn.setAttribute('data-i18n', 'tlTitulo');
  esq.insertBefore(abrirBtn, esq.firstChild);

  const $ = id => sec.querySelector('#' + id);
  const trilho = $('tlTrilho'), estado = $('tlEstado'), inspe = $('tlInspetor'), filtro = $('tlVisao'), escolha = $('tlComponentes');
  const CONTROLES = ['tlVisao', 'tlComponentes', 'tlMais', 'tlMenos', 'tlEnquadrar'];
  let versoes = [], atual = 0, cy = null, timer = null, carregado = false, inspecionado = '', chaveAtual = null, medida = '';
  const medidaDoGrafo = () => $('tlGrafo').clientWidth + 'x' + $('tlGrafo').clientHeight;

  function textoFixo() {
    if (I) I.aplicar();
    sec.querySelectorAll('[data-tl-leg]').forEach(el => { el.textContent = t('tlLegenda')[Number(el.getAttribute('data-tl-leg'))]; });
    $('tlTocar').textContent = t(timer ? 'tlPausar' : 'tlTocar');
  }
  function parar() { if (timer) { clearInterval(timer); timer = null; } $('tlTocar').textContent = t('tlTocar'); }
  function carregar() {
    return new Promise(resolve => {
      if (window.LODEMAP_LINHA_DO_TEMPO) return resolve(window.LODEMAP_LINHA_DO_TEMPO);
      const inserir = () => { const s = document.createElement('script'); s.src = 'linha-do-tempo.js'; s.onload = () => resolve(window.LODEMAP_LINHA_DO_TEMPO); s.onerror = () => resolve(null); document.head.appendChild(s); };
      if (location.protocol === 'file:') inserir(); else fetch('linha-do-tempo.js', { method: 'HEAD' }).then(r => r.ok ? inserir() : resolve(null)).catch(() => resolve(null));
    });
  }
  const nomeVersao = v => v.tag || v.sha || t('tlTrabalho');
  // `data` é a do commit do mapa (várias versões podem sair no mesmo dia); `data_tag`, a do commit que a tag marca, é a da
  // release e vem na frente. Arquivos antigos, ou versões sem tag, não têm `data_tag`: ficam só com a data do mapa.
  const dataDe = v => v.data_tag || v.data || '';
  const datasHtml = v => v.data_tag
    ? `<span>${esc(t('tlRelease'))} ${esc(v.data_tag)}</span><span class="tl-mapa">${esc(t('tlMapa'))} ${esc(v.data || '')}</span>`
    : `<span>${esc(v.data || '')}</span>`;
  function historico(id) {
    const tipos = { adicionados: 'tlEntrou', removidos: 'tlSaiu', alterados: 'tlMudou' };
    return versoes.map(v => {
      const k = v.dados && Object.keys(tipos).find(c => ((v.componentes || {})[c] || []).some(e => e.ident === id));
      return k ? `<li>${esc(dataDe(v) || t('tlNaoCommit'))} · ${esc(v.tag || v.sha || t('tlTrabMin'))} — ${esc(t(tipos[k]))}</li>` : '';
    }).join('');
  }
  function inspecionar(id, elements) {
    const e = (elements || elementos)[id];
    if (!e) return;
    inspecionado = id; escolha.value = id;
    inspe.innerHTML = `<strong>${esc(e.nome || id)}</strong><p><code>${esc(id)}</code></p><p>${esc(e.desc || t('tlSemDesc'))}</p><h3>${esc(t('tlHistorico'))}</h3><ul>${historico(id) || '<li>' + esc(t('tlSemHist')) + '</li>'}</ul>`;
  }
  let elementos = {};

  // Nó do tamanho do rótulo: mede o texto quebrado em linhas (largura máxima MAX_TEXTO) com a mesma fonte do grafo.
  const familia = () => getComputedStyle(document.body).fontFamily || 'sans-serif';
  const medidor = document.createElement('canvas').getContext('2d');
  function tamanho(rotulo) {
    medidor.font = FONTE + 'px ' + familia();
    const linhas = []; let linha = '';
    String(rotulo).split(/\s+/).forEach(p => {
      const cand = linha ? linha + ' ' + p : p;
      if (linha && medidor.measureText(cand).width > MAX_TEXTO) { linhas.push(linha); linha = p; } else linha = cand;
    });
    linhas.push(linha);
    const larg = Math.min(MAX_TEXTO, Math.max(...linhas.map(l => medidor.measureText(l).width)));
    return { w: Math.ceil(larg) + 2 * PAD, h: Math.ceil(linhas.length * FONTE * 1.25) + 2 * PAD };
  }
  // Cores lidas do tema vigente cada vez que o estilo é montado (e de novo em lm:tema).
  function estilo() {
    const css = getComputedStyle(document.documentElement), c = n => css.getPropertyValue(n).trim();
    return [
      { selector: 'node', style: { label: 'data(label)', shape: 'round-rectangle', 'background-color': c('--surface-2'), 'border-width': 2, 'border-color': c('--separator-strong'), color: c('--label'), 'font-size': FONTE, 'font-family': familia(), 'text-wrap': 'wrap', 'text-max-width': MAX_TEXTO, width: 'data(w)', height: 'data(h)', 'text-valign': 'center', 'text-halign': 'center' } },
      { selector: 'node.entrou', style: { 'border-color': c('--ok'), 'border-width': 4 } },
      { selector: 'node.saiu', style: { 'border-style': 'dashed', 'border-color': c('--err'), opacity: 0.7 } },
      { selector: 'node.mudou', style: { shape: 'rectangle', 'border-color': c('--warn'), 'border-width': 4 } },
      { selector: 'edge', style: { width: 1, 'line-color': c('--separator-strong'), 'target-arrow-color': c('--separator-strong'), 'target-arrow-shape': 'triangle', 'curve-style': 'bezier' } },
      { selector: 'edge.rel-entrou', style: { width: 3, 'line-color': c('--ok'), 'target-arrow-color': c('--ok') } },
      { selector: 'edge.rel-saiu', style: { width: 2, 'line-style': 'dashed', 'line-color': c('--err'), 'target-arrow-color': c('--err') } },
      { selector: 'edge.rel-resposta', style: { 'line-style': 'dashed' } }];
  }
  // Piso de zoom do mapa principal no celular (texto de 10 px ou mais); a área do grafo é pequena, então o mesmo piso vale na janela larga.
  const estreito = () => matchMedia('(max-width: 900px)').matches;
  const zoomLegivel = () => 0.85;
  // Enquadra o grafo; se o zoom caísse abaixo do legível, fica no mínimo legível e o resto se alcança arrastando.
  // O recorte começa no que mudou naquela versão (entrou, saiu, mudou); sem mudança, no canto de cima.
  function enquadrar() {
    if (!cy) return;
    cy.resize(); cy.fit(undefined, MARGEM);
    const corte = cy.zoom() < zoomLegivel();
    if (corte) {
      // A janela do tamanho da área, no zoom legível, que começa onde pega mais nós que mudaram (e, no empate, mais nós).
      const z = zoomLegivel(), W = (cy.width() - 2 * MARGEM) / z, H = (cy.height() - 2 * MARGEM) / z;
      const mudou = new Set(cy.nodes('.entrou, .saiu, .mudou').map(n => n.id()));
      const caixas = cy.nodes().map(n => ({ m: mudou.has(n.id()), b: n.boundingBox({ includeLabels: false }) }));
      let melhor = null;
      caixas.forEach(a => {
        const x0 = a.b.x1 - 8, y0 = a.b.y1 - 8;
        const dentro = caixas.filter(c => c.b.x1 >= x0 && c.b.y1 >= y0 && c.b.x2 <= x0 + W && c.b.y2 <= y0 + H);
        const nota = dentro.filter(c => c.m).length * 1000 + dentro.length;
        if (!melhor || nota > melhor.nota) melhor = { nota, x0, y0 };
      });
      const todos = cy.nodes().boundingBox({ includeLabels: false }), cabeX = todos.w * z <= cy.width() - 2 * MARGEM, cabeY = todos.h * z <= cy.height() - 2 * MARGEM;
      cy.zoom(z);
      cy.pan({ x: cabeX ? (cy.width() - todos.w * z) / 2 - todos.x1 * z : MARGEM - melhor.x0 * z,
               y: cabeY ? (cy.height() - todos.h * z) / 2 - todos.y1 * z : MARGEM - melhor.y0 * z });
    }
    $('tlDica').hidden = !corte; $('tlDica').textContent = corte ? t('tlDica') : '';
  }
  const temDagre = () => { try { return !!window.cytoscape('layout', 'dagre'); } catch (e) { return false; /* dagre não carregou */ } };
  const disposicao = dir => temDagre() ? { name: 'dagre', rankDir: dir, nodeSep: 24, rankSep: 56, fit: false, animate: false } : { name: 'grid', fit: false, padding: MARGEM };
  // Da esquerda para a direita ou de cima para baixo: a que deixa o grafo no maior zoom dentro da área (um nó com muitos filhos
  // fica largo demais de cima para baixo, e alto, mas estreito, da esquerda para a direita).
  function direcao() {
    if (!cy || !temDagre()) return 'TB';
    const zoomDe = d => { cy.layout(disposicao(d)).run(); const bb = cy.elements().boundingBox(); return Math.min((cy.width() - 2 * MARGEM) / Math.max(1, bb.w), (cy.height() - 2 * MARGEM) / Math.max(1, bb.h)); };
    return zoomDe('LR') > zoomDe('TB') ? 'LR' : 'TB';
  }

  function indisponivel() {
    estado.textContent = t('tlIndisp');
    if (cy) { cy.destroy(); cy = null; }
    filtro.innerHTML = '<option value="">' + esc(t('tlVisaoIndisp')) + '</option>';
    escolha.innerHTML = '<option value="">' + esc(t('tlCompIndisp')) + '</option>';
    CONTROLES.forEach(id => { $(id).disabled = true; });
    inspe.textContent = t('tlInspIndisp'); $('tlDica').hidden = true; elementos = {};
  }
  function selecionar(i, escolhida) {
    atual = i; const v = versoes[i];
    trilho.querySelectorAll('button').forEach((b, n) => b.setAttribute('aria-pressed', String(n === i)));
    if (!v.dados || !v.snapshot) return indisponivel();
    CONTROLES.forEach(id => { $(id).disabled = false; });
    estado.textContent = (v.mudou_idioma ? t('tlTraducao') + ' · ' : '') + (v.resumo.total === 0 ? t('tlSemAlt') + ' · ' : '') + (v.tag || v.sha || t('tlTrabalho'));
    const s = v.snapshot, adicionados = new Set(v.componentes.adicionados.map(x => x.ident)), removidos = new Map(v.componentes.removidos.map(x => [x.ident, x])), alterados = new Set(v.componentes.alterados.map(x => x.ident));
    const visoes = (s.visoes || []).filter(x => x.elementos && x.elementos.length);
    const anteriores = versoes.find(x => x.sha === v.base && x.snapshot);
    const relevantes = new Set([...adicionados, ...removidos.keys(), ...alterados]);
    const pontuar = x => x.elementos.filter(id => relevantes.has(id)).length;
    const melhor = visoes.filter(x => x.elementos.length <= 24 && x.elementos.length >= 3).sort((a, b) => pontuar(b) - pontuar(a) || b.elementos.length - a.elementos.length)[0];
    const chave = escolhida || (melhor && melhor.chave) || '__tudo';
    chaveAtual = chave;
    const visao = visoes.find(x => x.chave === chave), visaoAnt = anteriores && (anteriores.snapshot.visoes || []).find(x => x.chave === chave);
    filtro.innerHTML = '<option value="__tudo">' + esc(t('tlTudo')) + '</option>' + visoes.map(x => `<option value="${esc(x.chave)}">${esc(x.titulo || x.chave)} (${x.elementos.length})</option>`).join('');
    filtro.value = chave;
    const ids = visao ? new Set(visao.elementos) : null;
    const elements = Object.fromEntries(Object.entries(s.elementos).filter(([id]) => !ids || ids.has(id)));
    removidos.forEach((e, id) => { if (!elements[id] && (!ids || (visaoAnt && visaoAnt.elementos.includes(id)))) elements[id] = e; });
    elementos = elements;
    escolha.innerHTML = '<option value="">' + esc(t('tlEscolha')) + '</option>' + Object.entries(elements).map(([id, e]) => `<option value="${esc(id)}">${esc(e.nome || id)}</option>`).join('');
    const marca = id => removidos.has(id) ? '◌ ' : adicionados.has(id) ? '◆ ' : alterados.has(id) ? '■ ' : '';
    const nodes = Object.entries(elements).map(([id, e]) => ({ data: { id: 'n:' + id, ident: id, label: marca(id) + (e.nome || id), ...tamanho(marca(id) + (e.nome || id)) }, classes: removidos.has(id) ? 'saiu' : adicionados.has(id) ? 'entrou' : alterados.has(id) ? 'mudou' : '' }));
    const iguais = (a, b) => a.de === b.de && a.para === b.para && (a.desc || null) === (b.desc || null) && (a.tech || null) === (b.tech || null);
    const novas = (v.relacoes && v.relacoes.novas) || [], sumidas = (v.relacoes && v.relacoes.removidas) || [];
    const fluxo = visao && visao.tipo === 'dinamica' && s.fluxos && s.fluxos[chave];
    const atuais = fluxo ? (fluxo.passos || []).map(p => {
      const origem = p.resposta ? p.para : p.de, destino = p.resposta ? p.de : p.para;
      const rel = (visao.relacoes || []).find(r => r.de === origem && r.para === destino);
      return { de: p.de, para: p.para, desc: p.desc || (rel && rel.desc), nova: !!rel && novas.some(n => iguais(n, rel)), resposta: !!p.resposta };
    }) : (visao ? visao.relacoes : s.relacoes).map(r => ({ ...r, nova: novas.some(n => iguais(n, r)) }));
    const antigas = (!visao ? sumidas : visaoAnt ? sumidas.filter(r => (visaoAnt.relacoes || []).some(a => iguais(a, r))) : []);
    const fluxoAnt = visaoAnt && visaoAnt.tipo === 'dinamica' && anteriores.snapshot.fluxos && anteriores.snapshot.fluxos[chave];
    const fantasmas = fluxoAnt ? antigas.flatMap(r => (fluxoAnt.passos || []).filter(p => p.resposta ? p.para === r.de && p.de === r.para : p.de === r.de && p.para === r.para).map(p => ({ de: p.de, para: p.para, desc: p.desc || r.desc, removida: true }))) : antigas.map(r => ({ ...r, removida: true }));
    const edges = atuais.concat(fantasmas).filter(r => elements[r.de] && elements[r.para]).map((r, j) => ({ data: { id: 'r:' + j, source: 'n:' + r.de, target: 'n:' + r.para, label: r.desc || '' }, classes: r.removida ? 'rel-saiu' : r.nova ? 'rel-entrou' : r.resposta ? 'rel-resposta' : '' }));
    if (cy) cy.destroy();
    cy = window.cytoscape({ container: $('tlGrafo'), elements: nodes.concat(edges), style: estilo(), minZoom: 0.3, maxZoom: 3 });
    cy.layout({ ...disposicao(direcao()), stop: () => {
      // Ligação que passaria por trás de um nó que não é ponta dela ganha uma barriga (o mesmo desvio do mapa principal).
      if (window.LodemapDesvio) window.LodemapDesvio.desviar(cy, estreito() ? { w: cy.width(), zoom: zoomLegivel() } : null);
      medida = medidaDoGrafo(); enquadrar();
    } }).run();
    cy.on('tap', 'node', ev => inspecionar(ev.target.data('ident')));
    if (inspecionado && elements[inspecionado]) inspecionar(inspecionado); else { inspecionado = ''; inspe.textContent = t('tlInspVazio'); }
  }

  function montarTrilho() {
    trilho.innerHTML = versoes.map((v, i) => `<button type="button" class="tl-versao${v.resumo && !v.resumo.total ? ' tl-zero' : ''}" aria-pressed="false" data-tl="${i}"><b>${esc(v.tag || v.sha || t('tlTrab'))}</b>${datasHtml(v)}<small>${v.mudou_idioma ? esc(t('tlTraducao')) : v.resumo ? esc(t('tlAlteracoes', v.resumo.total)) : esc(t('tlIndisp'))}</small></button>`).join('');
    trilho.querySelectorAll('button').forEach(b => b.addEventListener('click', () => { parar(); selecionar(Number(b.dataset.tl)); }));
  }
  async function abrir() {
    sec.hidden = false; document.body.classList.remove('com-painel');
    textoFixo(); sec.focus({ preventScroll: true });
    if (!carregado) {
      estado.textContent = t('tlCarregando');
      const d = await carregar(); carregado = true;
      versoes = d && Array.isArray(d.versoes) ? d.versoes : [];
      if (sec.hidden) return;                                   // fechou enquanto carregava
    }
    if (!versoes.length) { estado.textContent = t('tlNenhuma'); return; }
    montarTrilho(); selecionar(Math.min(atual || versoes.length - 1, versoes.length - 1));
  }
  function fechar() {
    parar(); sec.hidden = true;
    if (cy) { cy.destroy(); cy = null; }
    if (sec.contains(document.activeElement)) abrirBtn.focus({ preventScroll: true });
  }
  window.LodemapLinhaDoTempo = { abrir, fechar, aberto: () => !sec.hidden };

  abrirBtn.addEventListener('click', () => { if (rota.empilhar) rota.empilhar(HASH); abrir(); });
  $('tlSair').addEventListener('click', () => { if (rota.fecharTL) rota.fecharTL(); else fechar(); });
  filtro.addEventListener('change', () => selecionar(atual, filtro.value));
  escolha.addEventListener('change', () => inspecionar(escolha.value));
  const zoom = f => { if (cy) cy.zoom({ level: cy.zoom() * f, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } }); };
  $('tlMais').addEventListener('click', () => zoom(1.3));
  $('tlMenos').addEventListener('click', () => zoom(1 / 1.3));
  $('tlEnquadrar').addEventListener('click', enquadrar);
  $('tlTocar').addEventListener('click', () => {
    if (timer) return parar();
    if (!versoes.length) return;
    if (atual === versoes.length - 1) selecionar(0);
    $('tlTocar').textContent = t('tlPausar');
    timer = setInterval(() => { if (atual >= versoes.length - 1) return parar(); selecionar(atual + 1); }, 1600);
  });
  // O painel pode ganhar seu tamanho final depois do layout (grade, inspetor, rotação do aparelho): enquadra de novo quando o tamanho muda.
  if (window.ResizeObserver) new ResizeObserver(() => { if (!cy || sec.hidden || medidaDoGrafo() === medida) return; medida = medidaDoGrafo(); enquadrar(); }).observe($('tlGrafo'));
  document.addEventListener('lm:tema', () => { if (cy) { cy.style(estilo()); } });
  document.addEventListener('lm:idioma', () => {
    textoFixo();
    if (sec.hidden || !versoes.length) return;
    montarTrilho(); selecionar(atual, chaveAtual);
  });
  textoFixo();
  if (location.hash === HASH) abrir();                          // recarregar com o painel aberto reabre o painel
})();
