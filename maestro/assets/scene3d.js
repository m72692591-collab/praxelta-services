(() => {
  const canvas = document.getElementById('scene3d');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  const buttons = [...document.querySelectorAll('[data-scene]')];
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  let mode = 'object', angle = .5, tilt = -.25, dragging = false, lastX = 0, lastY = 0, frame = 0, visible = true;
  const colors = {object:'#ff8c3d', space:'#65ccff', data:'#9b83ff'};
  const project = (p, w, h) => {
    const ca=Math.cos(angle), sa=Math.sin(angle), ct=Math.cos(tilt), st=Math.sin(tilt);
    const x=p[0]*ca-p[2]*sa, z=p[0]*sa+p[2]*ca;
    const y=p[1]*ct-z*st, depth=p[1]*st+z*ct;
    const scale=420/(420+depth);
    return [w/2+x*scale, h/2+y*scale, scale, depth];
  };
  function line(a,b,color,alpha=1,width=1){ctx.globalAlpha=alpha;ctx.strokeStyle=color;ctx.lineWidth=width;ctx.beginPath();ctx.moveTo(a[0],a[1]);ctx.lineTo(b[0],b[1]);ctx.stroke();ctx.globalAlpha=1;}
  function poly(points,fill,stroke){ctx.beginPath();ctx.moveTo(points[0][0],points[0][1]);for(let i=1;i<points.length;i++)ctx.lineTo(points[i][0],points[i][1]);ctx.closePath();ctx.fillStyle=fill;ctx.fill();ctx.strokeStyle=stroke;ctx.lineWidth=.7;ctx.stroke()}
  function draw(){
    const dpr=Math.min(devicePixelRatio||1,2), w=canvas.clientWidth, h=canvas.clientHeight;
    if (!w || !h) return;
    if (canvas.width!==Math.round(w*dpr)||canvas.height!==Math.round(h*dpr)){canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr)}
    ctx.setTransform(dpr,0,0,dpr,0,0);
    ctx.clearRect(0,0,w,h);
    const glow=ctx.createRadialGradient(w*.5,h*.5,5,w*.5,h*.5,w*.58);glow.addColorStop(0,'rgba(255,115,42,.13)');glow.addColorStop(1,'rgba(255,115,42,0)');ctx.fillStyle=glow;ctx.fillRect(0,0,w,h);
    const s=Math.min(w/570,h/400,1.15), P=p=>project(p.map(v=>v*s),w,h), color=colors[mode];
    if(mode==='object'){
      const rings=24, segments=26, rows=[], faces=[];
      for(let i=0;i<rings;i++){let row=[];let u=i*2*Math.PI/rings;for(let j=0;j<segments;j++){let v=j*2*Math.PI/segments,R=116+39*Math.cos(v);row.push(P([R*Math.cos(u),39*Math.sin(v),R*Math.sin(u)]));}rows.push(row)}
      for(let i=0;i<rings;i++)for(let j=0;j<segments;j++){const u=i*2*Math.PI/rings,v=j*2*Math.PI/segments;const pts=[rows[i][j],rows[(i+1)%rings][j],rows[(i+1)%rings][(j+1)%segments],rows[i][(j+1)%segments]];const depth=pts.reduce((n,p)=>n+p[3],0)/4;const lit=Math.max(0,Math.cos(u-angle)*Math.cos(v)*.42+Math.sin(v)*.48+.5);faces.push({pts,depth,fill:`hsl(${24+lit*15} 90% ${17+lit*31}%)`})}
      faces.sort((a,b)=>b.depth-a.depth).forEach(f=>poly(f.pts,f.fill,'rgba(255,177,104,.14)'));
      for(let i=0;i<rings;i+=3)for(let j=0;j<segments;j++)line(rows[i][j],rows[i][(j+1)%segments],'#ffd298',.22,.6);
    }else if(mode==='space'){
      const cubes=[[-105,35,-15,92], [15,-38,0,125], [110,55,25,74]];
      const facets=[];for(const [cx,cy,cz,size] of cubes){const q=size/2,pts=[[-q,-q,-q],[q,-q,-q],[q,q,-q],[-q,q,-q],[-q,-q,q],[q,-q,q],[q,q,q],[-q,q,q]].map(v=>P([v[0]+cx,v[1]+cy,v[2]+cz]));for(const [index,face] of [[0,[0,1,2,3]],[1,[4,5,6,7]],[2,[0,1,5,4]],[3,[2,3,7,6]],[4,[1,2,6,5]],[5,[0,3,7,4]]]){const corners=face.map(n=>pts[n]);facets.push({corners,depth:corners.reduce((n,p)=>n+p[3],0)/4,index})}}
      facets.sort((a,b)=>b.depth-a.depth).forEach(f=>poly(f.corners,`hsla(${200+f.index*5} 84% ${18+f.index*4}% / .78)`,'rgba(123,220,255,.7)'));
      for(let i=0;i<7;i++){const a=P([-215+i*72,125,-150]),b=P([-215+i*72,125,160]);line(a,b,'#68bbdf',.13,.8)}
    }else{
      const curves=[[],[],[]];for(let i=0;i<95;i++){let t=i/94, y=(t-.5)*290;for(let k=0;k<3;k++){let a=t*Math.PI*7+k*2*Math.PI/3;curves[k].push(P([Math.cos(a)*95,y,Math.sin(a)*95]))}}
      const shades=['#a98aff','#ff9852','#57d9ff'];for(const [k,curve] of curves.entries())for(let i=1;i<curve.length;i++){line(curve[i-1],curve[i],shades[k],.24,7);line(curve[i-1],curve[i],shades[k],.83,2.3)}
      for(let i=0;i<95;i+=6){line(curves[0][i],curves[1][i],color,.28,1);for(let k=0;k<3;k++){const p=curves[k][i];ctx.beginPath();ctx.arc(p[0],p[1],2.5+p[2],0,Math.PI*2);ctx.fillStyle=shades[k];ctx.fill()}}
    }
    ctx.font='600 11px system-ui';ctx.fillStyle='rgba(255,255,255,.52)';ctx.fillText('MAESTRO / 3D LAB',20,h-20);
    if(!reduced.matches&&!dragging&&visible&&!document.hidden){angle+=.0025;frame=requestAnimationFrame(draw)}
  }
  function select(next){mode=next;buttons.forEach(b=>{const active=b.dataset.scene===next;b.setAttribute('aria-pressed',String(active));b.classList.toggle('active',active)});cancelAnimationFrame(frame);draw()}
  buttons.forEach(b=>b.addEventListener('click',()=>select(b.dataset.scene)));
  canvas.addEventListener('pointerdown',e=>{dragging=true;lastX=e.clientX;lastY=e.clientY;canvas.setPointerCapture(e.pointerId);cancelAnimationFrame(frame)});
  canvas.addEventListener('pointermove',e=>{if(!dragging)return;angle+=(e.clientX-lastX)*.008;tilt=Math.max(-1.1,Math.min(1.1,tilt+(e.clientY-lastY)*.006));lastX=e.clientX;lastY=e.clientY;draw()});
  const release=()=>{dragging=false;cancelAnimationFrame(frame);draw()};
  canvas.addEventListener('pointerup',release);
  canvas.addEventListener('pointercancel',release);
  addEventListener('resize',()=>{cancelAnimationFrame(frame);draw()});
  reduced.addEventListener?.('change',()=>{cancelAnimationFrame(frame);draw()});
  if('IntersectionObserver' in window){new IntersectionObserver(entries=>{const entry=entries[0];visible=entry.isIntersecting;document.body.classList.toggle('viewing-3d',entry.intersectionRatio>.45);cancelAnimationFrame(frame);if(visible)draw()},{threshold:[0,.45]}).observe(canvas)}
  document.addEventListener('visibilitychange',()=>{cancelAnimationFrame(frame);if(!document.hidden&&visible)draw()});
  draw();
})();
