/* Evidências são estáticas e não comprovam execução nem estado da árvore. */
(function () {
  'use strict';
  let data=null, referenciaMapa=null;
  const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const obter=e=>data && data.componentes && data.componentes[e.ident || e.id];
  function estado(e){const x=obter(e);if(!x || !x.testes || x.testes.estado!=='medido')return 'desconhecido';return x.testes.arquivos.length?'referenciado':'sem_referencia';}
  // Texto no idioma da página: as chaves entram no dicionário do explorador na primeira chamada (saude.js carrega antes dele).
  const DICT={
    pt:{sdTitulo:'Saúde',sdSem:'Sem evidências para este componente.',sdEvid:'Saúde · evidências',sdTestes:n=>`${n} arquivo(s) de teste referenciam o código`,sdTestesDesc:'Referências de teste desconhecidas',
      sdCob:'Cobertura',sdJunit:'JUnit',sdFalhas:n=>`${n} falha(s) associada(s)`,sdDesc:'desconhecida',sdDescM:'desconhecido',sdProva:'Referências estáticas não comprovam execução.',sdJunitNota:'JUnit só associa testes com atributo file.',
      sdCommits:(a,b,c)=>`Commits em 30/90 dias: ${a} / ${b}; última mudança: ${c}.`,sdRef:(d,c)=>`Referência: ${d} · commit ${c} · árvore de trabalho não verificada.`,
      sdDiverge:'Divergência: status Pronto sem referências estáticas de teste encontradas.',sdIgual:'Commit de evidência coincide com o commit do mapa selecionado.',
      sdDifere:'Commit de evidência difere do commit do mapa selecionado; pode estar desatualizada.',sdNaoComparou:'Não foi possível comparar o commit da evidência ao mapa.'},
    en:{sdTitulo:'Health',sdSem:'No evidence for this component.',sdEvid:'Health · evidence',sdTestes:n=>`${n} test file(s) reference the code`,sdTestesDesc:'Test references unknown',
      sdCob:'Coverage',sdJunit:'JUnit',sdFalhas:n=>`${n} associated failure(s)`,sdDesc:'unknown',sdDescM:'unknown',sdProva:'Static references do not prove execution.',sdJunitNota:'JUnit only associates tests that have a file attribute.',
      sdCommits:(a,b,c)=>`Commits in 30/90 days: ${a} / ${b}; last change: ${c}.`,sdRef:(d,c)=>`Reference: ${d} · commit ${c} · working tree not verified.`,
      sdDiverge:'Mismatch: status Ready with no static test references found.',sdIgual:'Evidence commit matches the commit of the selected map.',
      sdDifere:'Evidence commit differs from the commit of the selected map; it may be out of date.',sdNaoComparou:'Could not compare the evidence commit with the map.'}};
  function T(k,...a){
    const I=window.LodemapIdioma;
    if(I && I.dicionario && !I.dicionario.pt.sdTitulo){Object.assign(I.dicionario.pt,DICT.pt);Object.assign(I.dicionario.en,DICT.en);}
    if(I && I.dicionario)return I.t(k,...a);
    const v=DICT.pt[k];return typeof v==='function'?v(...a):v;
  }
  function texto(e){
    const x=obter(e);if(!x)return `<h2>${esc(T('sdTitulo'))}</h2><p>${esc(T('sdSem'))}</p>`;
    const r=data.referencia || {}, tests=x.testes || {}, cob=x.cobertura || {}, junit=x.junit || {}, git=x.git || {};
    const test=tests.estado==='medido'?T('sdTestes',(tests.arquivos||[]).length):T('sdTestesDesc');
    const cobertura=cob.estado==='medido'?(cob.arquivos||[]).map(a=>`${esc(a.arquivo)}: ${a.percentual==null?T('sdDesc'):esc(a.percentual)+'%'}`).join('; '):`${esc(T('sdCob'))}: ${esc(cob.estado||T('sdDesc'))}`;
    const falhas=junit.estado==='medido'?T('sdFalhas',(junit.falhas||[]).length):`${T('sdJunit')}: ${esc(junit.estado||T('sdDescM'))}`;
    const divergencia=e.props && e.props.status==='Pronto' && tests.estado==='medido' && !(tests.arquivos||[]).length ? `<p class="impacto aviso">${esc(T('sdDiverge'))}</p>` : '';
    const comparacao=referenciaMapa && r.commit ? (referenciaMapa===r.commit?T('sdIgual'):T('sdDifere')):T('sdNaoComparou');
    const commits=T('sdCommits',esc(git.commits_30_dias ?? T('sdDescM')),esc(git.commits_90_dias ?? T('sdDescM')),esc(git.ultima_mudanca || T('sdDesc')));
    return `<h2>${esc(T('sdEvid'))}</h2><p>${esc(test)}. ${esc(T('sdProva'))}</p><p>${cobertura}</p><p>${esc(falhas)}. ${esc(T('sdJunitNota'))}</p><p>${commits}</p><p>${T('sdRef',esc(r.data||T('sdDesc')),esc(r.commit||T('sdDescM')))} ${esc(comparacao)}</p>${divergencia}`;
  }
  function carregar(){return new Promise(resolve=>{if(window.LODEMAP_EVIDENCIAS){data=window.LODEMAP_EVIDENCIAS;return resolve(data);}const inserir=()=>{const s=document.createElement('script');s.src='evidencias.js';s.onload=()=>{data=window.LODEMAP_EVIDENCIAS;resolve(data);};s.onerror=()=>resolve(null);document.head.appendChild(s);};if(location.protocol==='file:')inserir();else fetch('evidencias.js',{method:'HEAD'}).then(r=>r.ok?inserir():resolve(null)).catch(()=>resolve(null));});}
  window.LodemapSaude={carregar,estado,texto,referencia:sha=>{referenciaMapa=sha||null;}};
})();
