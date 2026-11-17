const navigationRoot=new URL('../',new URL(cfg.assetPrefix,location.href));
// Pin asset URLs before history changes so lazy images and later fetches stay valid.
cfg.assetPrefix=new URL('assets/',navigationRoot).href;
document.querySelectorAll('img[src]').forEach(n=>n.src=new URL(n.getAttribute('src'),location.href).href);
function syncLanguageUrl(){
  try{history.replaceState(null,'',OrbitNavigation.languageUrl(location.href,navigationRoot,lang));}catch{}
  const canonical=new URL(lang==='en'?'':lang+'/',cfg.baseUrl).href;
  document.querySelector('link[rel="canonical"]').href=canonical;
  const values={'description':T('description'),'og:url':canonical,'og:title':T('pageTitle'),'og:description':T('description'),
    'og:image':new URL('assets/orbit-social-'+lang+'.png',cfg.baseUrl).href,
    'og:image:alt':T('description'),'twitter:title':T('pageTitle'),'twitter:description':T('description'),
    'twitter:image':new URL('assets/orbit-social-'+lang+'.png',cfg.baseUrl).href};
  for(const [key,value] of Object.entries(values)){
    const node=document.querySelector('meta[property="'+key+'"],meta[name="'+key+'"]');
    if(node)node.content=value;
  }
}
