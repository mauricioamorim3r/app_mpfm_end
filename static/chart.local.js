(function(){
  function isNum(v){ return typeof v==='number' && isFinite(v); }
  function rgba(c,a){
    if(!c) return `rgba(38,160,255,${a})`;
    if(c.startsWith('rgba')) return c.replace(/rgba\(([^,]+),([^,]+),([^,]+),[^\)]+\)/, `rgba($1,$2,$3,${a})`);
    if(c.startsWith('rgb(')) return c.replace('rgb(','rgba(').replace(')',`,${a})`);
    if(c[0]==='#'){
      const h=c.slice(1); const n=h.length===3?h.split('').map(x=>x+x).join(''):h;
      const r=parseInt(n.slice(0,2),16), g=parseInt(n.slice(2,4),16), b=parseInt(n.slice(4,6),16);
      return `rgba(${r},${g},${b},${a})`;
    }
    return c;
  }
  function pick(v,i,def){ return Array.isArray(v)? (v[i] ?? def) : (v ?? def); }
  class Chart {
    constructor(ctx, cfg){
      this.ctx = ctx; this.canvas = ctx.canvas; this.cfg = cfg || {}; this._onResize = ()=>this.render();
      this.data = this.cfg.data || {};
      this.options = this.cfg.options || {};
      this.chartArea = null;
      this.scales = {};
      this._datasetMeta = [];
      window.addEventListener('resize', this._onResize); this.render();
    }
    destroy(){ try{ window.removeEventListener('resize', this._onResize);}catch(e){}; this.clear(); }
    clear(){ const c=this.canvas, x=this.ctx; x.clearRect(0,0,c.width,c.height); }
    resize(){ this.render(); }
    isDatasetVisible(){ return true; }
    getDatasetMeta(index){ return this._datasetMeta[index] || { data: [] }; }
    toBase64Image(){ return this.canvas.toDataURL('image/png'); }
    size(){ const rect=this.canvas.getBoundingClientRect(); const dpr=window.devicePixelRatio||1;
      const w=Math.max(300, Math.floor(rect.width||this.canvas.width||900)); const h=Math.max(220, Math.floor(rect.height||this.canvas.height||320));
      this.canvas.width=w*dpr; this.canvas.height=h*dpr; this.canvas.style.width=w+'px'; this.canvas.style.height=h+'px';
      this.ctx.setTransform(dpr,0,0,dpr,0,0); return {w,h}; }
    render(){
      const {w,h}=this.size(); const ctx=this.ctx; ctx.clearRect(0,0,w,h);
      const data=(this.cfg.data||{}), labels=(data.labels||[]), datasets=(data.datasets||[]).filter(d=>Array.isArray(d.data));
      this.data = data;
      this.options = this.cfg.options || {};
      if(!labels.length||!datasets.length){ this.scales = {}; this._empty(w,h); return; }
      const legendH = 0; const m={l:54,r:24,t:20+legendH,b:38}; const iw=w-m.l-m.r, ih=h-m.t-m.b;
      this.chartArea = { left:m.l, top:m.t, right:w-m.r, bottom:h-m.b, width:iw, height:ih };
      let ymin=Infinity,ymax=-Infinity;
      datasets.forEach(ds=> ds.data.forEach(v=> { if(isNum(v)){ ymin=Math.min(ymin,v); ymax=Math.max(ymax,v);} }));
      if(!isFinite(ymin)||!isFinite(ymax)){ this.scales = {}; this._empty(w,h); return; }
      if(ymin===ymax){ const d=Math.abs(ymin||1)*0.1; ymin-=d; ymax+=d; }
      // Support beginAtZero option
      const beginAtZero = this.options?.scales?.y?.beginAtZero || this.options?.scales?.yL?.beginAtZero;
      if (beginAtZero && ymin > 0) ymin = 0;
      const fixedMin = this.options?.scales?.y?.min;
      const fixedMax = this.options?.scales?.y?.max;
      if (isNum(fixedMin)) ymin = fixedMin;
      if (isNum(fixedMax)) ymax = fixedMax;
      if (!(isNum(fixedMin) || isNum(fixedMax))) {
        const pad=(ymax-ymin)*0.08;
        if (beginAtZero && ymin === 0) ymax += pad;
        else { ymin-=pad; ymax+=pad; }
      }
      const y = v => m.t + ih - ((v-ymin)/(ymax-ymin))*ih;
      const x = i => labels.length<=1 ? m.l+iw/2 : m.l + (i*(iw/(labels.length-1)));
      const categoryWidth = labels.length ? iw / labels.length : iw;
      const xCategoryCenter = i => m.l + (categoryWidth * i) + (categoryWidth / 2);
      const hasBarOnly = datasets.length > 0 && datasets.every(ds => (ds.type || this.cfg.type) === 'bar');
      const xTick = hasBarOnly ? xCategoryCenter : x;
      this.scales = {
        x: {
          id: 'x',
          type: 'category',
          min: 0,
          max: Math.max(0, labels.length - 1),
          getPixelForValue(value) {
            return xTick(typeof value === 'number' ? value : 0);
          }
        },
        y: {
          id: 'y',
          type: 'linear',
          min: ymin,
          max: ymax,
          getPixelForValue(value) {
            return y(value);
          }
        }
      };
      // grid
      ctx.strokeStyle='rgba(255,255,255,.08)'; ctx.lineWidth=1; ctx.setLineDash([]); ctx.fillStyle='#8ea3ba'; ctx.font='10px sans-serif';
      const ticks=5;
      const tickCallback = this.options?.scales?.y?.ticks?.callback || this.options?.scales?.yL?.ticks?.callback;
      for(let t=0;t<=ticks;t++){
        const yy=m.t + (ih*t/ticks); ctx.beginPath(); ctx.moveTo(m.l,yy); ctx.lineTo(w-m.r,yy); ctx.stroke();
        const val=(ymax - (ymax-ymin)*t/ticks);
        const label = tickCallback ? tickCallback(val) : (Math.abs(val)>=1000? val.toFixed(0): val.toFixed(2)).replace(/\.00$/,'');
        ctx.fillText(label, 4, yy+3);
      }
      // x labels
      labels.forEach((lab,i)=>{ if(labels.length>40 && i%Math.ceil(labels.length/12)!==0) return; const xx=xTick(i); ctx.fillText(String(lab), xx-8, h-12); });
      // axes
      ctx.strokeStyle='rgba(255,255,255,.18)'; ctx.beginPath(); ctx.moveTo(m.l,m.t); ctx.lineTo(m.l,h-m.b); ctx.lineTo(w-m.r,h-m.b); ctx.stroke();
      this._datasetMeta = [];
      (Chart._plugins || []).forEach(plugin => {
        const options = this.options?.plugins?.[plugin.id];
        if (typeof plugin.beforeDatasetsDraw === 'function') {
          plugin.beforeDatasetsDraw(this, null, options);
        }
      });
      ctx.save();
      ctx.beginPath();
      ctx.rect(this.chartArea.left, this.chartArea.top, this.chartArea.width, this.chartArea.height);
      ctx.clip();
      const barDatasets = datasets.filter(ds => (ds.type || this.cfg.type) === 'bar');
      const barDatasetCount = barDatasets.length;
      const barGroupWidth = Math.min(56, categoryWidth * 0.84);
      const singleBarWidth = barDatasetCount ? Math.max(4, Math.min(22, barGroupWidth / barDatasetCount)) : 0;
      const baseValue = (ymin <= 0 && ymax >= 0) ? 0 : ymin;
      const baseY = y(baseValue);
      datasets.forEach(ds=>{
        const color = pick(ds.borderColor,0,'#26a0ff'); const bg = ds.backgroundColor && ds.backgroundColor!=='transparent' ? ds.backgroundColor : rgba(color,.12);
        const meta = { data: [] };
        if ((ds.type || this.cfg.type) === 'bar') {
          const barIndex = Math.max(0, barDatasets.indexOf(ds));
          ds.data.forEach((v,i)=>{
            if(!isNum(v)){ meta.data.push({ getProps(){ return { x: NaN, y: NaN }; } }); return; }
            const xx = xCategoryCenter(i) - (barGroupWidth / 2) + (singleBarWidth * barIndex) + (singleBarWidth / 2);
            const yy = y(v);
            const top = Math.min(yy, baseY);
            const height = Math.max(0, Math.abs(baseY - yy));
            const width = Math.max(3, singleBarWidth * 0.82);
            meta.data.push({ getProps(){ return { x: xx, y: yy }; } });
            ctx.beginPath();
            ctx.fillStyle = pick(ds.backgroundColor,i,bg);
            ctx.fillRect(xx - (width / 2), top, width, height);
            const stroke = pick(ds.borderColor,i,color);
            const lineWidth = pick(ds.borderWidth,i,1);
            if (stroke && lineWidth > 0) {
              ctx.lineWidth = lineWidth;
              ctx.strokeStyle = stroke;
              ctx.strokeRect(xx - (width / 2), top, width, height);
            }
          });
        } else {
          ctx.beginPath(); let started=false; ctx.setLineDash(ds.borderDash||[]); ctx.lineWidth=ds.borderWidth||2; ctx.strokeStyle=color;
          ds.data.forEach((v,i)=>{ if(!isNum(v)){ if(!ds.spanGaps) started=false; meta.data.push({ getProps(){ return { x: NaN, y: NaN }; } }); return; } const xx=x(i), yy=y(v); meta.data.push({ getProps(){ return { x: xx, y: yy }; } }); if(!started){ ctx.moveTo(xx,yy); started=true; } else ctx.lineTo(xx,yy); });
          ctx.stroke();
          if(ds.fill && ds.fill!==false){ ctx.lineTo(x(labels.length-1), h-m.b); ctx.lineTo(x(0), h-m.b); ctx.closePath(); ctx.fillStyle=bg; ctx.fill(); }
          ds.data.forEach((v,i)=>{ if(!isNum(v)) return; const r=pick(ds.pointRadius,i,2); if(r<=0) return; const xx=x(i), yy=y(v); ctx.beginPath(); ctx.fillStyle=pick(ds.pointBackgroundColor,i,color); ctx.arc(xx,yy,r,0,Math.PI*2); ctx.fill(); const bc=pick(ds.pointBorderColor,i,null); if(bc){ ctx.strokeStyle=bc; ctx.lineWidth=1; ctx.stroke(); } });
        }
        this._datasetMeta.push(meta);
      });
      ctx.restore();
      (Chart._plugins || []).forEach(plugin => {
        const options = this.options?.plugins?.[plugin.id];
        if (typeof plugin.afterDatasetsDraw === 'function') {
          plugin.afterDatasetsDraw(this, null, options);
        }
      });
      // simple legend
      let lx=m.l, ly=12; ctx.font='11px sans-serif';
      datasets.filter(ds=>!(ds.label||'').startsWith('__band')).slice(0,8).forEach(ds=>{ const txt=String(ds.label||''); const tw=ctx.measureText(txt).width; if(lx+tw+24 > w-m.r){ lx=m.l; ly+=14; } ctx.fillStyle=pick(ds.borderColor,0,'#26a0ff'); ctx.fillRect(lx,ly-8,10,3); ctx.fillStyle='#9ca3af'; ctx.fillText(txt,lx+14,ly); lx += tw+28; });
    }
    _empty(w,h){ const ctx=this.ctx; ctx.fillStyle='#8ea3ba'; ctx.font='12px sans-serif'; ctx.fillText('Sem dados para exibir', Math.max(20,w/2-60), h/2); }
  }
  Chart._plugins = [];
  Chart.register = function(){
    for (let i = 0; i < arguments.length; i += 1) {
      const plugin = arguments[i];
      if (plugin && plugin.id && !Chart._plugins.some(item => item.id === plugin.id)) {
        Chart._plugins.push(plugin);
      }
    }
  };
  window.Chart = Chart;
})();
