(() => {
  const canvas = document.getElementById('scene3d');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  const buttons = [...document.querySelectorAll('[data-scene]')];
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  let mode = 'object', angle = .5, tilt = -.25, dragging = false, lastX = 0, lastY = 0, frame = 0;
  const colors = {object:'#ff8c3d', space:'#65ccff', data:'#9b83ff'};
  const project = (p, w, h) => {
    const ca=Math.cos(angle), sa=Math.sin(angle), ct=Math.cos(tilt), st=Math.sin(tilt);
    const x=p[0]*ca-p[2]*sa, z=p[0]*sa+p[2]*ca;
    const y=p[1]*ct-z*st, depth=p[1]*st+z*ct;
    const scale=420/(420+depth);
    return [w/2+x*scale, h/2+y*scale, scale, depth];
  };
  function line(a,b,color,alpha=1,width=1){ctx.globalAlpha=alpha;ctx.strokeStyle=color;ctx.lineWidth=width;ctx.beginPath();ctx.moveTo(a[0],a[1]);ctx.lineTo(b[0],b[1]);ctx.stroke();ctx.globalAlpha=1;}
  function draw(){
    const dpr=Math.min(devicePixelRatio||1,2), w=canvas.clientWidth, h=canvas.clientHeight;
    if (!w || !h) return;
    if (canvas.width!==Math.round(w*dpr)||canvas.height!==Math.round(h*dpr)){canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr)}
    ctx.setTransform(dpr,0,0,dpr,0,0);
    ctx.clearRect(0,0,w,h);
    const glow=ctx.createRadialGradient(w*.5,h*.5,5,w*.5,h*.5,w*.58);glow.addColorStop(0,'rgba(255,115,42,.13)');glow.addColorStop(1,'rgba(255,115,42,0)');ctx.fillStyle=glow;ctx.fillRect(0,0,w,h);
    const s=Math.min(w/570,h/400,1.15), P=p=>project(p.map(v=>v*s),w,h), color=colors[mode];
    if(mode==='object'){
      const rings=22, segments=34, rows=[];
      for(let i=0;i<rings;i++){let row=[];let u=i*2*Math.PI/rings;for(let j=0;j<segments;j++){let v=j*2*Math.PI/segments,R=116+39*Math.cos(v);row.push(P([R*Math.cos(u),39*Math.sin(v),R*Math.sin(u)]));}rows.push(row)}
      for(let i=0;i<rings;i++)for(let j=0;j<segments;j++){const a=rows[i][j];line(a,rows[(i+1)%rings][j],color,.19+.34*a[2],1.05);line(a,rows[i][(j+1)%segments],color,.14+.25*a[2],.8)}
    }else if(mode==='space'){
      const cubes=[[-105,35,-15,92], [15,-38,0,125], [110,55,25,74]];
      for(const [cx,cy,cz,size] of cubes){const q=size/2,pts=[[-q,-q,-q],[q,-q,-q],[q,q,-q],[-q,q,-q],[-q,-q,q],[q,-q,q],[q,q,q],[-q,q,q]].map(v=>P([v[0]+cx,v[1]+cy,v[2]+cz]));for(const [a,b] of [[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[0,4],[1,5],[2,6],[3,7]])line(pts[a],pts[b],color,.65,1.6);}
    }else{
      const curves=[[],[],[]];for(let i=0;i<95;i++){let t=i/94, y=(t-.5)*290;for(let k=0;k<3;k++){let a=t*Math.PI*7+k*2*Math.PI/3;curves[k].push(P([Math.cos(a)*95,y,Math.sin(a)*95]))}}
      for(const curve of curves)for(let i=1;i<curve.length;i++)line(curve[i-1],curve[i],color,.22+.4*curve[i][2],1.7);
      for(let i=0;i<95;i+=6)line(curves[0][i],curves[1][i],color,.22,1);
    }
    ctx.font='600 11px system-ui';ctx.fillStyle='rgba(255,255,255,.52)';ctx.fillText('MAESTRO / 3D LAB',20,h-20);
    if(!reduced.matches&&!dragging){angle+=.0025;frame=requestAnimationFrame(draw)}
  }
  function select(next){mode=next;buttons.forEach(b=>{const active=b.dataset.scene===next;b.setAttribute('aria-pressed',String(active));b.classList.toggle('active',active)});cancelAnimationFrame(frame);draw()}
  buttons.forEach(b=>b.addEventListener('click',()=>select(b.dataset.scene)));
  canvas.addEventListener('pointerdown',e=>{dragging=true;lastX=e.clientX;lastY=e.clientY;canvas.setPointerCapture(e.pointerId);cancelAnimationFrame(frame)});
  canvas.addEventListener('pointermove',e=>{if(!dragging)return;angle+=(e.clientX-lastX)*.008;tilt=Math.max(-1.1,Math.min(1.1,tilt+(e.clientY-lastY)*.006));lastX=e.clientX;lastY=e.clientY;draw()});
  canvas.addEventListener('pointerup',()=>{dragging=false;draw()});
  addEventListener('resize',()=>{cancelAnimationFrame(frame);draw()});
  reduced.addEventListener?.('change',()=>{cancelAnimationFrame(frame);draw()});
  draw();
})();
