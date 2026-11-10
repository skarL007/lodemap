/* Linha do tempo usa somente snapshots históricos normalizados por identificador. */
(function () {
  'use strict';
  const centro = document.getElementById('centro'), esq = document.getElementById('esq');
  if (!centro || !esq) return;
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const sec = document.createElement('section');
  sec.id = 'timelinePanel'; sec.hidden = true; sec.setAttribute('aria-label', 'Linha do tempo da arquitetura');
  sec.innerHTML = '<div class="tl-cab"><div><strong>Linha do tempo</strong><p>Selecione uma versão para ver o mapa daquela data. Evidências de saúde atuais não são aplicadas ao histórico.</p></div><button class="botao" id="tlSair">Voltar ao mapa</button></div><div class="tl-controles"><button class="botao" id="tlTocar">Tocar evolução</button><span id="tlEstado" role="status"></span></div><div class="tl-trilho" id="tlTrilho" role="group" aria-label="Versões da arquitetura"></div><div class="tl-legenda"><span>◆ Entrou</span><span>◌ Saiu</span><span>■ Mudou</span><span>● Sem alteração</span><span>━━ Relação nova</span><span>┄┄ Relação removida</span></div><div class="tl-filtros"><label for="tlVisao">Visão histórica</label><select id="tlVisao"></select><button class="botao" id="tlMais" aria-label="Ampliar grafo">+</button><button class="botao" id="tlMenos" aria-label="Reduzir grafo">−</button><button class="botao" id="tlEnquadrar">Enquadrar</button></div><label for="tlComponentes">Inspecionar componente</label><select id="tlComponentes"><option value="">Selecione um componente</option></select><div class="tl-corpo"><div id="tlGrafo" role="img" aria-label="Grafo da versão selecionada"></div><aside id="tlInspetor" aria-live="polite">Selecione um componente no grafo para ver seu histórico.</aside></div>';
  centro.appendChild(sec);
  const abrir = document.createElement('button'); abrir.className='item'; abrir.id='tlAbrir'; abrir.textContent='Linha do tempo';
  esq.insertBefore(abrir, esq.firstChild);
  let versoes=[], atual=0, cy=null, timer=null;
  const trilho=sec.querySelector('#tlTrilho'), estado=sec.querySelector('#tlEstado'), inspe=sec.querySelector('#tlInspetor');
  function parar(){if(timer){clearInterval(timer);timer=null;} sec.querySelector('#tlTocar').textContent='Tocar evolução';}
  function carregar(){return new Promise(resolve => {
    if(window.LODEMAP_LINHA_DO_TEMPO) return resolve(window.LODEMAP_LINHA_DO_TEMPO);
    const inserir=()=>{const s=document.createElement('script');s.src='linha-do-tempo.js';s.onload=()=>resolve(window.LODEMAP_LINHA_DO_TEMPO);s.onerror=()=>resolve(null);document.head.appendChild(s);};
    if(location.protocol==='file:') inserir(); else fetch('linha-do-tempo.js',{method:'HEAD'}).then(r=>r.ok?inserir():resolve(null)).catch(()=>resolve(null));
  });}
  function historico(id){return versoes.filter(v => v.dados && ['adicionados','removidos','alterados'].some(k => (v.componentes[k]||[]).some(e=>e.ident===id))).map(v=>{
    const tipo=['adicionados','removidos','alterados'].find(k=>(v.componentes[k]||[]).some(e=>e.ident===id));
    return `<li>${esc(v.data || 'Não commitado')} · ${esc(v.tag || v.sha || 'trabalho')} — ${esc({adicionados:'entrou',removidos:'saiu',alterados:'mudou'}[tipo])}</li>`;
  }).join('');}
  function selecionar(i, escolhida){
    atual=i; const v=versoes[i]; trilho.querySelectorAll('button').forEach((b,n)=>b.setAttribute('aria-pressed',String(n===i)));
    if(!v.dados || !v.snapshot){
      estado.textContent='Dados indisponíveis para esta versão.';
      if(cy){cy.destroy();cy=null;}
      sec.querySelector('#tlVisao').innerHTML='<option value="">Visão indisponível</option>';
      sec.querySelector('#tlComponentes').innerHTML='<option value="">Componente indisponível</option>';
      ['tlVisao','tlComponentes','tlMais','tlMenos','tlEnquadrar'].forEach(id=>sec.querySelector('#'+id).disabled=true);
      inspe.textContent='Nenhum componente disponível nesta versão.';
      return;
    }
    ['tlVisao','tlComponentes','tlMais','tlMenos','tlEnquadrar'].forEach(id=>sec.querySelector('#'+id).disabled=false);
    estado.textContent=(v.mudou_idioma?'Tradução · ':'')+(v.resumo.total===0?'Sem alteração arquitetural · ':'')+(v.tag || v.sha || 'Trabalho não commitado');
    const s=v.snapshot, adicionados=new Set(v.componentes.adicionados.map(x=>x.ident)), removidos=new Map(v.componentes.removidos.map(x=>[x.ident,x])), alterados=new Set(v.componentes.alterados.map(x=>x.ident));
    const visoes=(s.visoes||[]).filter(x=>x.elementos && x.elementos.length);
    const anteriores=versoes.find(x=>x.sha===v.base && x.snapshot);
    const relevantes=new Set([...adicionados,...removidos.keys(),...alterados]);
    const pontuar=x=>x.elementos.filter(id=>relevantes.has(id)).length;
    const melhor=visoes.filter(x=>x.elementos.length<=24 && x.elementos.length>=3).sort((a,b)=>pontuar(b)-pontuar(a) || b.elementos.length-a.elementos.length)[0];
    const chave=escolhida || (melhor && melhor.chave) || '__tudo';
    const visao=visoes.find(x=>x.chave===chave), visaoAnt=anteriores && (anteriores.snapshot.visoes||[]).find(x=>x.chave===chave);
    const filtro=sec.querySelector('#tlVisao'); filtro.innerHTML='<option value="__tudo">Modelo inteiro</option>'+visoes.map(x=>`<option value="${esc(x.chave)}">${esc(x.titulo||x.chave)} (${x.elementos.length})</option>`).join(''); filtro.value=chave;
    filtro.onchange=()=>selecionar(atual,filtro.value);
    const ids=visao?new Set(visao.elementos):null;
    const elements=Object.fromEntries(Object.entries(s.elementos).filter(([id])=>!ids || ids.has(id)));
    removidos.forEach((e,id)=>{if(!elements[id] && (!ids || (visaoAnt && visaoAnt.elementos.includes(id)))) elements[id]=e;});
    const escolha=sec.querySelector('#tlComponentes'); escolha.innerHTML='<option value="">Selecione um componente</option>'+Object.entries(elements).map(([id,e])=>`<option value="${esc(id)}">${esc(e.nome||id)}</option>`).join('');
    function inspecionar(id){const e=elements[id];if(!e)return; escolha.value=id;inspe.innerHTML=`<strong>${esc(e.nome||id)}</strong><p><code>${esc(id)}</code></p><p>${esc(e.desc||'Sem descrição nesta versão.')}</p><h3>Histórico do componente</h3><ul>${historico(id)||'<li>Sem alterações registradas.</li>'}</ul>`;}
    escolha.onchange=()=>inspecionar(escolha.value);
    const nodes=Object.entries(elements).map(([id,e])=>({data:{id:'n:'+id,ident:id,label:e.nome||id},classes:removidos.has(id)?'saiu':adicionados.has(id)?'entrou':alterados.has(id)?'mudou':''}));
    const iguais=(a,b)=>a.de===b.de && a.para===b.para && (a.desc||null)===(b.desc||null) && (a.tech||null)===(b.tech||null);
    const novas=(v.relacoes && v.relacoes.novas)||[], sumidas=(v.relacoes && v.relacoes.removidas)||[];
    const fluxo=visao && visao.tipo==='dinamica' && s.fluxos && s.fluxos[chave];
    const atuais=fluxo ? (fluxo.passos||[]).map(p=>{
      const origem=p.resposta?p.para:p.de, destino=p.resposta?p.de:p.para;
      const rel=(visao.relacoes||[]).find(r=>r.de===origem && r.para===destino);
      return {de:p.de,para:p.para,desc:p.desc || (rel && rel.desc),nova:!!rel && novas.some(n=>iguais(n,rel)),resposta:!!p.resposta};
    }) : (visao?visao.relacoes:s.relacoes).map(r=>({...r,nova:novas.some(n=>iguais(n,r))}));
    const antigas=(!visao ? sumidas : visaoAnt ? sumidas.filter(r=>(visaoAnt.relacoes||[]).some(a=>iguais(a,r))) : []);
    const fluxoAnt=visaoAnt && visaoAnt.tipo==='dinamica' && anteriores.snapshot.fluxos && anteriores.snapshot.fluxos[chave];
    const fantasmas=fluxoAnt ? antigas.flatMap(r=>(fluxoAnt.passos||[]).filter(p=>p.resposta ? p.para===r.de && p.de===r.para : p.de===r.de && p.para===r.para).map(p=>({de:p.de,para:p.para,desc:p.desc||r.desc,removida:true}))) : antigas.map(r=>({...r,removida:true}));
    const edges=atuais.concat(fantasmas).filter(r=>elements[r.de] && elements[r.para]).map((r,j)=>({data:{id:'r:'+j,source:'n:'+r.de,target:'n:'+r.para,label:r.desc||''},classes:r.removida?'rel-saiu':r.nova?'rel-entrou':r.resposta?'rel-resposta':''}));
    if(cy)cy.destroy();
    const css=getComputedStyle(document.documentElement), token=n=>css.getPropertyValue(n).trim();
    cy=cytoscape({container:sec.querySelector('#tlGrafo'),elements:nodes.concat(edges),style:[
      {selector:'node',style:{'label':'data(label)','shape':'round-rectangle','background-color':token('--surface-2'),'border-width':2,'border-color':token('--separator-strong'),'color':token('--label'),'font-size':11,'text-wrap':'wrap','text-max-width':110,'width':110,'height':38,'text-valign':'center','text-halign':'center'}},
      {selector:'node.entrou',style:{'shape':'diamond','border-color':token('--ok'),'border-width':4}},
      {selector:'node.saiu',style:{'shape':'ellipse','border-style':'dashed','border-color':token('--err'),'opacity':0.7}},
      {selector:'node.mudou',style:{'shape':'rectangle','border-color':token('--warn'),'border-width':4}},
      {selector:'edge',style:{'width':1,'line-color':token('--separator-strong'),'target-arrow-color':token('--separator-strong'),'target-arrow-shape':'triangle','curve-style':'bezier'}},
      {selector:'edge.rel-entrou',style:{'width':3,'line-color':token('--ok'),'target-arrow-color':token('--ok')}},
      {selector:'edge.rel-saiu',style:{'width':2,'line-style':'dashed','line-color':token('--err'),'target-arrow-color':token('--err')}},
      {selector:'edge.rel-resposta',style:{'line-style':'dashed'}}],
      layout:{name:'grid',fit:true,padding:24},minZoom:0.05,maxZoom:3});
    cy.on('tap','node',ev=>inspecionar(ev.target.data('ident')));
    inspe.textContent='Selecione um componente no grafo para ver seu histórico.';
  }
  abrir.addEventListener('click',async()=>{sec.hidden=false;document.body.classList.remove('com-painel');estado.textContent='Carregando versões…';const d=await carregar();versoes=d && Array.isArray(d.versoes)?d.versoes:[];if(!versoes.length){estado.textContent='Nenhuma versão disponível. Gere a linha do tempo para este mapa.';return;}trilho.innerHTML=versoes.map((v,i)=>`<button type="button" class="tl-versao${v.resumo && !v.resumo.total?' tl-zero':''}" aria-pressed="false" data-tl="${i}"><b>${esc(v.tag||v.sha||'Trabalho')}</b><span>${esc(v.data||'')}</span><small>${v.mudou_idioma?'Tradução':v.resumo?esc(v.resumo.total)+' alterações':'Dados indisponíveis'}</small></button>`).join('');trilho.querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>{parar();selecionar(Number(b.dataset.tl));}));selecionar(versoes.length-1);});
  function zoom(fator){if(!cy)return;cy.zoom({level:cy.zoom()*fator,renderedPosition:{x:cy.width()/2,y:cy.height()/2}});}
  sec.querySelector('#tlMais').addEventListener('click',()=>zoom(1.3));
  sec.querySelector('#tlMenos').addEventListener('click',()=>zoom(1/1.3));
  sec.querySelector('#tlEnquadrar').addEventListener('click',()=>{if(cy)cy.fit(24);});
  sec.querySelector('#tlSair').addEventListener('click',()=>{parar();sec.hidden=true;if(cy){cy.destroy();cy=null;}});
  sec.querySelector('#tlTocar').addEventListener('click',()=>{if(timer){parar();return;}if(!versoes.length)return;if(atual===versoes.length-1)selecionar(0);sec.querySelector('#tlTocar').textContent='Pausar evolução';timer=setInterval(()=>{if(atual>=versoes.length-1){parar();return;}selecionar(atual+1);},1600);});
})();
