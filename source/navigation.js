// Preserve the current game while moving to the language's real public route.
(function(root){
  function languageUrl(current, base, language){
    const url = new URL(current), origin = new URL(base);
    url.pathname = origin.pathname + (language === 'en' ? '' : language + '/');
    url.searchParams.delete('lang');
    return url;
  }
  if(typeof module !== 'undefined' && module.exports) module.exports = {languageUrl};
  else root.OrbitNavigation = {languageUrl};
})(typeof globalThis !== 'undefined' ? globalThis : this);
