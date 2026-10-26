(() => {
  const targets=[];
  const add=(selector,rect,pseudo=false)=>document.querySelectorAll(selector).forEach(el=>targets.push({el,rect,pseudo}));
  add('#products > .visual-stripe',[0,0,766,325]);
  add('.pricing-stripe',[775,0,761,325]);
  add('.docs-stripe',[0,335,766,320]);
  add('#portfolio .portfolio-photo',[775,665,761,359]);
  add('.process-photo',[0,0,758,1024]);
  add('#lead .lead-photo',[780,0,756,1024]);
  document.querySelectorAll('#products .grid3 .card').forEach((el,i)=>targets.push({el,rect:[[0,514,1030][i%3],[0,334,650][Math.floor(i/3)],500,300],pseudo:true}));
  function fit({el,rect,pseudo}){
    const w=el.clientWidth,h=pseudo?parseFloat(getComputedStyle(el,'::before').height):el.clientHeight;
    if(!w||!h)return;
    const [x,y,cw,ch]=rect,scale=Math.max(w/cw,h/ch);
    el.style.setProperty('--crop-size',`${1536*scale}px ${1024*scale}px`);
    el.style.setProperty('--crop-position',`${-x*scale+(w-cw*scale)/2}px ${-y*scale+(h-ch*scale)/2}px`);
    el.dataset.cropScale=String(scale);
  }
  const update=()=>targets.forEach(fit);
  if('ResizeObserver' in window){const observer=new ResizeObserver(update);targets.forEach(({el})=>observer.observe(el))}
  addEventListener('resize',update);
  update();
})();
