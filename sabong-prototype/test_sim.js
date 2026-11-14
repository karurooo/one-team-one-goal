const Sim = require('./src/sim.js'); const { makeBot } = require('./src/bot.js');
function match(d0, d1, seed) {
  const s = Sim.create(seed); const b0 = makeBot(d0, seed * 3 + 1, 0), b1 = makeBot(d1, seed * 7 + 2, 1);
  const counts = {};
  let n = 0;
  while (s.phase !== 'ended' && n < 9000) { const ev = Sim.step(s, [b0.think(s), b1.think(s)]); for (const e of ev) counts[e.type] = (counts[e.type] || 0) + 1; n++; }
  return { res: s.result, n, counts, hp: s.m.map(m => Math.round(m.hp)), stats: s.m.map(m=>m.stats) };
}
const pairs = [['hard','easy'],['normal','easy'],['hard','normal'],['normal','normal']];
for (const [a,b] of pairs) {
  let w0=0,w1=0,dr=0, reasons={}, ticks=0, ev={};
  const N=300;
  for (let i=1;i<=N;i++){ const r=match(a,b,i); if(!r.res) throw new Error('no end '+i); ticks+=r.n;
    if(r.res.winner==='meron')w0++; else if(r.res.winner==='wala')w1++; else dr++;
    reasons[r.res.reason]=(reasons[r.res.reason]||0)+1; for(const k in r.counts) ev[k]=(ev[k]||0)+r.counts[k]; }
  console.log(a,'vs',b,'| win',(w0/N*100).toFixed(0)+'%','loss',w1,'draw',dr,'| avg secs',(ticks/N/60).toFixed(1),'|',JSON.stringify(reasons),'| per match:',Object.fromEntries(Object.entries(ev).filter(([k])=>['hit','clash_started','talikod','anti_air','exhausted','sentensya_started'].includes(k)).map(([k,v])=>[k,(v/N).toFixed(1)])));
}
