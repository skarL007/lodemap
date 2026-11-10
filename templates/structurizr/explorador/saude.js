/* Evidências são estáticas e não comprovam execução nem estado da árvore. */
(function () {
  'use strict';
  let data=null, referenciaMapa=null;
  const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const obter=e=>data && data.componentes && data.componentes[e.ident || e.id];
  function estado(e){const x=obter(e);if(!x || !x.testes || x.testes.estado!=='medido')return 'desconhecido';return x.testes.arquivos.length?'referenciado':'sem_referencia';}
  function texto(e){
    const x=obter(e);if(!x)return '<h2>Saúde</h2><p>Sem evidências para este componente.</p>';
    const r=data.referencia || {}, tests=x.testes || {}, cob=x.cobertura || {}, junit=x.junit || {}, git=x.git || {};
    const test=tests.estado==='medido'?`${(tests.arquivos||[]).length} arquivo(s) de teste referenciam o código`:'Referências de teste desconhecidas';
    const cobertura=cob.estado==='medido'?(cob.arquivos||[]).map(a=>`${esc(a.arquivo)}: ${a.percentual==null?'desconhecida':esc(a.percentual)+'%'}`).join('; '):`Cobertura: ${esc(cob.estado||'desconhecida')}`;
    const falhas=junit.estado==='medido'?`${(junit.falhas||[]).length} falha(s) associada(s)`:`JUnit: ${esc(junit.estado||'desconhecido')}`;
    const divergencia=e.props && e.props.status==='Pronto' && tests.estado==='medido' && !(tests.arquivos||[]).length ? '<p class="impacto aviso">Divergência: status Pronto sem referências estáticas de teste encontradas.</p>' : '';
    const comparacao=referenciaMapa && r.commit ? (referenciaMapa===r.commit?'Commit de evidência coincide com o commit do mapa selecionado.':'Commit de evidência difere do commit do mapa selecionado; pode estar desatualizada.'):'Não foi possível comparar o commit da evidência ao mapa.';
    return `<h2>Saúde · evidências</h2><p>${esc(test)}. Referências estáticas não comprovam execução.</p><p>${cobertura}</p><p>${esc(falhas)}. JUnit só associa testes com atributo file.</p><p>Commits em 30/90 dias: ${esc(git.commits_30_dias ?? 'desconhecido')} / ${esc(git.commits_90_dias ?? 'desconhecido')}; última mudança: ${esc(git.ultima_mudanca || 'desconhecida')}.</p><p>Referência: ${esc(r.data||'desconhecida')} · commit ${esc(r.commit||'desconhecido')} · árvore de trabalho não verificada. ${esc(comparacao)}</p>${divergencia}`;
  }
  function carregar(){return new Promise(resolve=>{if(window.LODEMAP_EVIDENCIAS){data=window.LODEMAP_EVIDENCIAS;return resolve(data);}const inserir=()=>{const s=document.createElement('script');s.src='evidencias.js';s.onload=()=>{data=window.LODEMAP_EVIDENCIAS;resolve(data);};s.onerror=()=>resolve(null);document.head.appendChild(s);};if(location.protocol==='file:')inserir();else fetch('evidencias.js',{method:'HEAD'}).then(r=>r.ok?inserir():resolve(null)).catch(()=>resolve(null));});}
  window.LodemapSaude={carregar,estado,texto,referencia:sha=>{referenciaMapa=sha||null;}};
})();
