const failureData=JSON.parse($('orbit-failures').textContent);
let activeFailure=null;
function renderFailures(){
  const root=$('failure-cards');root.replaceChildren();
  for(const item of failureData.cases){
    const card=el('article','failure-card');card.append(el('h3','',T('failure_'+item.id)));
    const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
    svg.setAttribute('viewBox','0 0 320 200');svg.setAttribute('role','img');svg.setAttribute('aria-label',T('failurePlotAlt'));
    function shape(tag,attributes){const n=document.createElementNS(svg.namespaceURI,tag);for(const [key,value] of Object.entries(attributes))n.setAttribute(key,value);svg.append(n);return n;}
    const point=p=>[18+p[0]*284,10+p[1]*180];
    shape('rect',{x:point([.08,.08])[0],y:point([.08,.08])[1],width:.84*284,height:.84*180,fill:'none',stroke:'var(--line)'});
    const goal=point(item.goal);shape('ellipse',{cx:goal[0],cy:goal[1],rx:C.HIT*284,ry:C.HIT*180,fill:'none',stroke:'var(--accent)','stroke-width':2});
    for(const [points,color,dash] of [[[item.start,...item.predicted],'var(--accent)','5 4'],[item.actual,'var(--text)','']]){
      shape('polyline',{points:points.map(p=>point(p).join(',')).join(' '),fill:'none',stroke:color,'stroke-width':2.4,'stroke-dasharray':dash});
      const end=point(points.at(-1));shape('circle',{cx:end[0],cy:end[1],r:3.5,fill:color});
    }
    card.append(svg);const legend=el('div','failure-legend');legend.append(el('span','',T('failurePredicted')),el('span','',T('failureActual')));card.append(legend);
    card.append(el('p','',T('failure_'+item.id+'Body')));
    card.append(el('p','failure-metrics',T('failureDistance',{d:(item.actualDistance*23).toFixed(2)})));
    const button=el('button','secondary',T('failureOpen'));button.type='button';button.disabled=!pack;
    button.onclick=()=>openFailure(item.id);card.append(button);root.append(card);
  }
  $('failure-active').hidden=!activeFailure;
  if(activeFailure)txt('failure-active',T('failureActive',{name:T('failure_'+activeFailure)}));
}
function openFailure(id,scroll=true){
  const item=failureData.cases.find(x=>x.id===id);if(!item||!pack)return;
  switchMode('lab');if(mode!=='lab')return; // Respect the existing daily-progress confirmation.
  newScene();activeFailure=id;
  $('noise').value=item.noise;txt('noise-value',item.noise.toFixed(2));
  scene=C.scenario(item.seed,item.noise);ranked=C.rankPlans(pack,scene.frames,scene.goalFrame);
  actions=ranked[0].actions.slice();predicted=C.predict(pack,scene.frames,actions);
  drawInputs();renderControls();renderStatus();renderInspection();renderFailures();draw();
  const u=new URL(location.href);u.searchParams.set('example',id);u.hash='play';history.replaceState(null,'',u);
  if(scroll)$('play').scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
}
function clearFailure(){
  activeFailure=null;$('failure-active').hidden=true;
  const u=new URL(location.href);u.searchParams.delete('example');history.replaceState(null,'',u);
}
$('show-failures').onclick=()=>{
  $('failure-gallery').hidden=!$('failure-gallery').hidden;
  $('show-failures').setAttribute('aria-expanded',String(!$('failure-gallery').hidden));
  renderFailures();
};
