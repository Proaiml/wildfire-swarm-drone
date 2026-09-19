const el=id=>document.getElementById(id);
const ctx=el('field').getContext('2d');
let runs=[], playing=false, previous=0;
function current(){return runs.find(r=>r.algorithm===el('algorithm').value && String(r.seed)===el('seed').value);}
function draw(){
 const run=current(), t=Number(el('timeline').value);ctx.clearRect(0,0,640,640);if(!run)return;
 ctx.strokeStyle='#28434d';ctx.lineWidth=1;for(let n=0;n<=640;n+=80){ctx.beginPath();ctx.moveTo(n,0);ctx.lineTo(n,640);ctx.moveTo(0,n);ctx.lineTo(640,n);ctx.stroke();}
 const colors=['#6ee7ef','#ffc76a','#bca4ff','#f391c0'];const history=run.history.filter(h=>h.t<=t);
 for(let i=0;i<4;i++){ctx.strokeStyle=colors[i];ctx.lineWidth=2;ctx.beginPath();for(const [index,h] of history.entries()){const [x,y]=h.xy[i];if(index===0)ctx.moveTo(x*.8,640-y*.8);else ctx.lineTo(x*.8,640-y*.8);}ctx.stroke();const last=history.at(-1);if(last){const [x,y]=last.xy[i];ctx.fillStyle=colors[i];ctx.beginPath();ctx.arc(x*.8,640-y*.8,5,0,Math.PI*2);ctx.fill();ctx.fillText(`D${i}`,x*.8+7,640-y*.8-7);}}
 for(const [index,target] of run.targets.entries()){const found=target.detected_s!==null&&target.detected_s<=t;if(!found&&!el('truth').checked)continue;ctx.strokeStyle=found?'#69ee99':'#e6a4ff';ctx.setLineDash(t<target.ignition_s?[3,5]:[]);ctx.lineWidth=2;ctx.beginPath();ctx.arc(target.xy[0]*.8,640-target.xy[1]*.8,10,0,Math.PI*2);ctx.stroke();ctx.fillStyle=ctx.strokeStyle;ctx.fillText(`Y${index+1}`,target.xy[0]*.8+12,640-target.xy[1]*.8);ctx.setLineDash([]);}
 const found=run.targets.filter(x=>x.detected_s!==null&&x.detected_s<=t).length;
 el('time').textContent=`${t} / 600 saniye • ${found} sensör keşfi`;
 el('metrics').textContent=`Koşu sonu: ${run.found}/4 hedef. Artçı keşif %${100*run.secondary_recall}. En küçük ayrılma ${run.minimum_separation_m.toFixed(1)} m. Mesafe ${(run.distance_m/1000).toFixed(1)} km. Kaçırmalar dahil ortalama gecikme ${run.penalized_delay_s.toFixed(1)} s.`;
 el('events').textContent=run.targets.map((v,i)=>`Y${i+1}: tutuşma ${v.ignition_s}s, ${v.detected_s===null?'600s içinde bulunamadı':`keşif ${v.detected_s}s`}`).join(' • ');
}
function seeds(){const values=runs.filter(r=>r.algorithm===el('algorithm').value).map(r=>r.seed);el('seed').replaceChildren(...values.map(v=>new Option(v,v)));el('timeline').value=0;draw();}
el('algorithm').onchange=seeds;el('seed').onchange=()=>{el('timeline').value=0;draw();};el('timeline').oninput=draw;el('truth').onchange=draw;el('play').onclick=()=>{playing=!playing;if(playing&&Number(el('timeline').value)>=600)el('timeline').value=0;el('play').textContent=playing?'Ⅱ Duraklat':'▶ Oynat (20×)';};
function animate(stamp){if(playing&&stamp-previous>=50){el('timeline').value=Math.min(600,Number(el('timeline').value)+1);draw();if(Number(el('timeline').value)>=600){playing=false;el('play').textContent='▶ Oynat (20×)';}previous=stamp;}requestAnimationFrame(animate);}requestAnimationFrame(animate);
Promise.all([fetch('/api/benchmarks/runs').then(r=>{if(!r.ok)throw Error('Koşular henüz hazır değil');return r.json();}),fetch('/api/benchmarks/results').then(r=>r.json())]).then(([rows,summary])=>{runs=rows.filter(r=>r.status==='ok');el('algorithm').replaceChildren(...[...new Set(runs.map(r=>r.algorithm))].map(v=>new Option(v,v)));seeds();el('progress').textContent=`${summary.status}: ${summary.completed_runs}/${summary.expected_runs} koşu. Başarısız: ${summary.failures.length}.`;
 for(const row of summary.ranking){const tr=document.createElement('tr');for(const value of [row.algorithm,`${(100*row.recall).toFixed(0)}%`,`${(100*row.secondary_recall).toFixed(0)}%`,row.safety_pass?'bu koşularda geçti':'İHLAL']){const td=document.createElement('td');td.textContent=value;tr.append(td);}el('ranking').append(tr);}
}).catch(e=>el('metrics').textContent=e.message);
