"""Mapa de vinculos interativo e autocontido, para notebooks (Colab/Jupyter)
e para embutir em qualquer pagina: um bloco HTML com SVG e JavaScript puro,
sem biblioteca externa.

Filtros: confianca minima, tipos de entidade e busca. Clique num no para ver
atributos e vinculos. Varios mapas podem coexistir na mesma pagina (cada um
recebe um prefixo proprio).
"""

from __future__ import annotations

import json
import secrets

from ..grafo.modelo import Grafo

CORES = {"telefone": "#3b82f6", "pessoa": "#f59e0b", "organizacao": "#10b981",
         "email": "#a855f7", "dominio": "#06b6d4", "url": "#94a3b8", "faixa": "#64748b",
         "cep": "#ef4444", "municipio": "#f97316", "documento": "#e11d48", "diario": "#0ea5e9",
         "sancao": "#dc2626", "cpf-parcial": "#fb7185", "prestadora": "#84cc16"}


def mapa_html(g: Grafo, altura: int = 600, limite: int = 400) -> str:
    uid = "fio" + secrets.token_hex(3)
    graus: dict[str, int] = {}
    for a in g.arestas.values():
        graus[a.origem] = graus.get(a.origem, 0) + 1
        graus[a.destino] = graus.get(a.destino, 0) + 1
    ids = sorted(g.entidades, key=lambda i: (-g.entidades[i].alvo_primario, -graus.get(i, 0)))[:limite]
    conj = set(ids)
    nos = [{"id": i, "t": g.entidades[i].tipo, "r": (g.entidades[i].rotulo or g.entidades[i].valor)[:40],
            "a": g.entidades[i].alvo_primario,
            "at": {k: v for k, v in g.entidades[i].atributos.items()
                   if v not in (None, "", [], {}) and k not in ("dorks", "variantes")}}
           for i in ids]
    ars = [{"o": a.origem, "d": a.destino, "r": a.relacao, "c": a.confianca,
            "f": ", ".join(sorted({f"{f.coletor} {f.admiralty}" for f in a.fontes}))}
           for a in g.arestas.values() if a.origem in conj and a.destino in conj]
    dados = json.dumps({"n": nos, "e": ars, "cores": CORES}, ensure_ascii=False, default=str)
    dados = dados.replace("</", "<\\/")
    return f"""
<div id="{uid}" class="fio-mapa" style="--fg:#1f2937;--mut:#6b7280;--bd:#d1d5db;--bg:#ffffff;--pn:#f9fafb;
 font:13px/1.45 system-ui,-apple-system,Segoe UI,sans-serif;color:var(--fg);border:1px solid var(--bd);border-radius:10px;background:var(--bg);overflow:hidden">
<style>
@media (prefers-color-scheme:dark){{#{uid}{{--fg:#e5e7eb;--mut:#9ca3af;--bd:#374151;--bg:#111827;--pn:#1f2937}}}}
#{uid} .bar{{display:flex;flex-wrap:wrap;gap:10px 16px;align-items:center;padding:10px 12px;border-bottom:1px solid var(--bd);background:var(--pn)}}
#{uid} .bar label{{display:inline-flex;gap:5px;align-items:center;cursor:pointer}}
#{uid} .bar input[type=search]{{border:1px solid var(--bd);border-radius:6px;padding:4px 8px;background:var(--bg);color:var(--fg);min-width:140px}}
#{uid} .corpo{{display:grid;grid-template-columns:1fr 260px}}
#{uid} svg{{width:100%;height:{altura}px;display:block;touch-action:none;background:var(--bg)}}
#{uid} .det{{border-left:1px solid var(--bd);padding:10px 12px;overflow:auto;max-height:{altura}px;background:var(--pn)}}
#{uid} .det td{{padding:2px 6px 2px 0;vertical-align:top;word-break:break-word}}
#{uid} .mut{{color:var(--mut)}} #{uid} .pill{{display:inline-block;padding:0 6px;border-radius:99px;color:#fff;font-size:11px;font-weight:700}}
#{uid} .dot{{width:10px;height:10px;border-radius:50%;display:inline-block}}
@media (max-width:700px){{#{uid} .corpo{{grid-template-columns:1fr}} #{uid} .det{{border-left:0;border-top:1px solid var(--bd)}}}}
</style>
<div class="bar"><label>confiança mínima <input type="range" min="0" max="0.9" step="0.05" value="0" class="lim"> <b class="limv">0,00</b></label>
<span class="tipos"></span><input type="search" class="busca" placeholder="buscar…"><span class="mut cont"></span></div>
<div class="corpo"><svg></svg><div class="det mut">Clique num círculo para ver atributos e vínculos. Arraste para reorganizar.</div></div>
<script>
(function(){{
var R=document.getElementById("{uid}"),D={dados},svg=R.querySelector("svg"),NS="http://www.w3.org/2000/svg";
var W=svg.clientWidth||900,H={altura};svg.setAttribute("viewBox","0 0 "+W+" "+H);
var niv=function(c){{return c>=.75?"#10b981":c>=.5?"#f59e0b":c>=.25?"#f97316":"#94a3b8"}};
var tipos={{}};D.n.forEach(function(n){{tipos[n.t]=(tipos[n.t]||0)+1}});
var ativos={{}};var T=R.querySelector(".tipos");Object.keys(tipos).forEach(function(t){{ativos[t]=true;
 var l=document.createElement("label");l.innerHTML='<input type="checkbox" checked> <i class="dot" style="background:'+(D.cores[t]||"#94a3b8")+'"></i> '+t+' ('+tipos[t]+')';
 l.firstChild.onchange=function(e){{ativos[t]=e.target.checked;filtra()}};T.appendChild(l)}});
var idx={{}};D.n.forEach(function(n,i){{idx[n.id]=i;n.x=W/2+Math.cos(i*2.4)*W*.3*Math.random();n.y=H/2+Math.sin(i*2.4)*H*.3*Math.random();n.vx=0;n.vy=0}});
var grau={{}};D.e.forEach(function(e){{grau[e.o]=(grau[e.o]||0)+1;grau[e.d]=(grau[e.d]||0)+1}});
var gl=document.createElementNS(NS,"g"),gn=document.createElementNS(NS,"g");svg.appendChild(gl);svg.appendChild(gn);
var L=D.e.map(function(e){{var l=document.createElementNS(NS,"line");l.setAttribute("stroke",niv(e.c));l.setAttribute("stroke-width",1+e.c*2.4);l.setAttribute("stroke-opacity",".6");
 if(e.c<.35)l.setAttribute("stroke-dasharray","5 4");var t=document.createElementNS(NS,"title");t.textContent=e.r+" ("+e.c+")";l.appendChild(t);gl.appendChild(l);return l}});
var arr=null,alfa=1;
var C=D.n.map(function(n){{var g=document.createElementNS(NS,"g");g.style.cursor="pointer";var r=5+Math.min(12,(grau[n.id]||0)*1.3)+(n.a?4:0);n.rad=r;
 var c=document.createElementNS(NS,"circle");c.setAttribute("r",r);c.setAttribute("fill",D.cores[n.t]||"#94a3b8");if(n.a){{c.setAttribute("stroke","currentColor");c.setAttribute("stroke-width","2.5")}}
 var tx=document.createElementNS(NS,"text");tx.setAttribute("font-size","10");tx.setAttribute("text-anchor","middle");tx.setAttribute("fill","currentColor");tx.setAttribute("fill-opacity",".75");tx.setAttribute("dy",r+11);tx.textContent=n.r.slice(0,26);
 g.appendChild(c);g.appendChild(tx);gn.appendChild(g);g.addEventListener("pointerdown",function(ev){{arr=n;g.setPointerCapture(ev.pointerId);det(n);alfa=Math.max(alfa,.2)}});return g}});
svg.style.color="var(--fg)";
svg.addEventListener("pointermove",function(ev){{if(!arr)return;var p=svg.createSVGPoint();p.x=ev.clientX;p.y=ev.clientY;var q=p.matrixTransform(svg.getScreenCTM().inverse());arr.x=q.x;arr.y=q.y}});
svg.addEventListener("pointerup",function(){{arr=null}});
function vis(n){{return ativos[n.t]}}
function filtra(){{var lim=+R.querySelector(".lim").value,q=R.querySelector(".busca").value.toLowerCase(),nv=0,ev=0;
 R.querySelector(".limv").textContent=lim.toFixed(2).replace(".",",");
 D.n.forEach(function(n,i){{var ok=vis(n)&&(!q||n.r.toLowerCase().indexOf(q)>=0||n.id.toLowerCase().indexOf(q)>=0||!q);n.on=vis(n);C[i].style.display=n.on?"":"none";
  C[i].style.opacity=(q&&n.r.toLowerCase().indexOf(q)<0&&n.id.toLowerCase().indexOf(q)<0)?.25:1;if(n.on)nv++}});
 D.e.forEach(function(e,i){{var on=e.c>=lim&&D.n[idx[e.o]].on&&D.n[idx[e.d]].on;e.on=on;L[i].style.display=on?"":"none";if(on)ev++}});
 R.querySelector(".cont").textContent=nv+" nós · "+ev+" vínculos";alfa=Math.max(alfa,.3)}}
R.querySelector(".lim").oninput=filtra;R.querySelector(".busca").oninput=filtra;
function esc(s){{return String(s).replace(/[&<>]/g,function(c){{return{{"&":"&amp;","<":"&lt;",">":"&gt;"}}[c]}})}}
function det(n){{var lig=D.e.filter(function(e){{return e.o===n.id||e.d===n.id}}).sort(function(a,b){{return b.c-a.c}});
 R.querySelector(".det").innerHTML='<span class="pill" style="background:'+(D.cores[n.t]||"#94a3b8")+'">'+esc(n.t)+'</span><div style="font-weight:700;margin:6px 0">'+esc(n.r)+'</div><table>'+
 Object.keys(n.at).map(function(k){{var v=n.at[k];return '<tr><td class="mut">'+esc(k)+'</td><td>'+esc(typeof v==="object"?JSON.stringify(v):v)+'</td></tr>'}}).join("")+'</table><div style="margin-top:8px;font-weight:700">Vínculos ('+lig.length+')</div>'+
 lig.map(function(e){{var o=e.o===n.id?e.d:e.o;return '<div style="margin:5px 0"><span class="pill" style="background:'+niv(e.c)+'">'+e.c+'</span> '+esc(e.r)+' <b>'+esc(D.n[idx[o]].r)+'</b><div class="mut" style="font-size:11.5px">'+esc(e.f)+'</div></div>'}}).join("")}}
var k=Math.sqrt(W*H/Math.max(D.n.length,1))*.7;
function passo(){{if(alfa>.01){{var N=D.n.filter(function(n){{return n.on}});
 for(var i=0;i<N.length;i++)for(var j=i+1;j<N.length;j++){{var a=N[i],b=N[j],dx=a.x-b.x,dy=a.y-b.y,d2=dx*dx+dy*dy||.01;if(d2>90000)continue;var f=k*k/d2*.05*alfa;a.vx+=dx*f;a.vy+=dy*f;b.vx-=dx*f;b.vy-=dy*f}}
 D.e.forEach(function(e){{if(!e.on)return;var a=D.n[idx[e.o]],b=D.n[idx[e.d]],dx=b.x-a.x,dy=b.y-a.y,dd=Math.sqrt(dx*dx+dy*dy)||1,f=(dd-k)/dd*.06*alfa;a.vx+=dx*f;a.vy+=dy*f;b.vx-=dx*f;b.vy-=dy*f}});
 N.forEach(function(n){{n.vx+=(W/2-n.x)*.002*alfa;n.vy+=(H/2-n.y)*.002*alfa;if(n!==arr){{n.x+=n.vx;n.y+=n.vy}}n.vx*=.6;n.vy*=.6;n.x=Math.max(14,Math.min(W-14,n.x));n.y=Math.max(14,Math.min(H-20,n.y))}});alfa*=.985}}
 D.e.forEach(function(e,i){{var a=D.n[idx[e.o]],b=D.n[idx[e.d]];L[i].setAttribute("x1",a.x);L[i].setAttribute("y1",a.y);L[i].setAttribute("x2",b.x);L[i].setAttribute("y2",b.y)}});
 D.n.forEach(function(n,i){{C[i].setAttribute("transform","translate("+n.x+","+n.y+")")}});if(document.body.contains(R))requestAnimationFrame(passo)}}
filtra();passo();
}})();
</script></div>"""
