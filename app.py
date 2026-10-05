
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="CITYMIND Prototype")

class Scenario(BaseModel):
    scenario: str = "road_closure"
    target: str = "R3"
    intensity: float = 1.0
    event_demand: float = 1.0

BASE = {"traffic":38,"transit":32,"parking":44,"ev":29,"emergency":25,"passenger":34}

def clamp(x): return max(0, min(100, round(x,1)))

def simulate(s):
    closure = s.intensity if s.scenario == "road_closure" else 0
    event_extra = (s.event_demand - 1.0) * 18 if s.scenario == "large_event" else 0
    buses = 12 if s.scenario in ("add_buses","combined") else 0
    signals = 9 if s.scenario in ("adaptive_signals","combined") else 0
    parking = 8 if s.scenario == "temporary_parking" else 0
    emergency = 10 if s.scenario == "emergency_corridor" else 0
    traffic = BASE["traffic"] + closure*38 + event_extra - buses*.7 - signals*.8 + (12 if s.scenario=="ev_surge" else 0)
    transit = BASE["transit"] + closure*30 + event_extra*.7 - buses*1.2 - signals*.5
    parking_score = BASE["parking"] + closure*28 + event_extra*.9 + (12 if s.scenario=="ev_surge" else 0) - parking*1.4
    ev = BASE["ev"] + event_extra*.8 + (35 if s.scenario=="ev_surge" else 0) + closure*12
    emerg = BASE["emergency"] + closure*35 + event_extra*.6 - signals*.6 - emergency*1.8
    passenger = BASE["passenger"] + closure*28 + event_extra*1.1 - buses*.9
    vals={k:clamp(v) for k,v in {"traffic":traffic,"transit":transit,"parking":parking_score,"ev":ev,"emergency":emerg,"passenger":passenger}.items()}
    impact=clamp(sum(vals.values())/6)
    return {"metrics":vals,"impact":impact,"avg_delay":clamp(5.5+impact*.11)}

def cascade(s,r):
    m=r["metrics"]
    if s.scenario=="large_event":
        return [("Large event","Passenger demand rises"),("Passenger demand","Bus + road demand increases"),("Road network",f"Traffic pressure reaches {m['traffic']:.0f}/100"),("Public transport",f"Transit stress reaches {m['transit']:.0f}/100"),("Parking",f"Parking pressure reaches {m['parking']:.0f}/100"),("Emergency",f"Emergency risk reaches {m['emergency']:.0f}/100")]
    if s.scenario=="road_closure":
        return [(s.target,"Road capacity removed"),("Diversion","Vehicles reroute to adjacent corridors"),("Intersection J4",f"Traffic pressure reaches {m['traffic']:.0f}/100"),("Bus routes",f"Transit stress reaches {m['transit']:.0f}/100"),("Parking P3",f"Parking pressure reaches {m['parking']:.0f}/100"),("Emergency route",f"Response risk reaches {m['emergency']:.0f}/100")]
    return [("Intervention","System response propagates"),("Traffic",f"Traffic pressure {m['traffic']:.0f}/100"),("Transit",f"Transit stress {m['transit']:.0f}/100"),("Parking",f"Parking pressure {m['parking']:.0f}/100"),("Emergency",f"Emergency risk {m['emergency']:.0f}/100")]

def recommend(s):
    candidates=[("Do nothing","baseline"),("Add 12 buses","add_buses"),("Adaptive signals","adaptive_signals"),("Buses + adaptive signals","combined"),("Temporary parking","temporary_parking"),("Emergency corridor","emergency_corridor")]
    out=[]
    for name,typ in candidates:
        rr=simulate(Scenario(scenario=typ,target=s.target,intensity=s.intensity,event_demand=s.event_demand))
        out.append({"name":name,"type":typ,"impact":rr["impact"],"delay":rr["avg_delay"]})
    return sorted(out,key=lambda x:x["impact"])[:4]

@app.get("/",response_class=HTMLResponse)
def home(): return HTMLResponse(INDEX)

@app.post("/api/simulate")
def api_simulate(s:Scenario):
    r=simulate(s)
    return {"scenario":s.model_dump(),"result":r,"cascade":cascade(s,r),"recommendations":recommend(s)}

INDEX = r'''
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CITYMIND - Urban Mobility Decision Twin</title>
<style>
:root{--bg:#07111f;--panel:#0d1a2b;--text:#e9f1f8;--muted:#91a4b8;--line:#203650;--good:#55d6a2;--warn:#f2bd5b;--bad:#f26d7d;--accent:#70a7ff}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 20% 0%,#122a43,#07111f 42%,#050b13);font-family:Inter,system-ui,Arial;color:var(--text)}
header{height:72px;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;padding:0 28px;background:#081525e8}.brand{font-weight:800;letter-spacing:.12em}.brand span{color:var(--accent)}.status{font-size:13px;color:var(--good)}.dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--good);margin-right:7px}
main{display:grid;grid-template-columns:290px 1fr 340px;gap:16px;padding:16px;min-height:calc(100vh - 72px)}.panel{background:linear-gradient(180deg,#0d1b2d,#0a1625);border:1px solid var(--line);border-radius:16px}.side{padding:18px}.title{font-size:12px;text-transform:uppercase;letter-spacing:.12em;color:var(--muted);margin-bottom:12px}
label{display:block;font-size:12px;color:var(--muted);margin:13px 0 7px}select,input{width:100%;padding:11px 12px;border-radius:10px;border:1px solid var(--line);background:#081423;color:var(--text)}button{width:100%;border:0;border-radius:11px;padding:12px;background:var(--accent);color:#06101c;font-weight:800;cursor:pointer;margin-top:16px}
.mapPanel{overflow:hidden}.mapHead{padding:18px 20px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between}.map{height:650px;background:radial-gradient(circle at 50% 50%,#132b3d,#091522 65%)}svg{width:100%;height:100%}.road{stroke:#3c5870;stroke-width:15;stroke-linecap:round}.road.hot{stroke:#f26d7d}.road.mid{stroke:#f2bd5b}.node{fill:#13263a;stroke:#6d8ca7;stroke-width:2}.node.hot{fill:#4a1e2a;stroke:#f26d7d}.nodetext{font-size:11px;fill:#b9c8d6}.legend{position:relative;margin:-85px 18px 0;width:max-content;background:#081423dd;border:1px solid var(--line);border-radius:10px;padding:10px;font-size:11px;color:var(--muted)}
.metricGrid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.metric{background:#0a1726;border:1px solid var(--line);border-radius:12px;padding:12px}.metric small{color:var(--muted)}.metric strong{display:block;font-size:24px;margin-top:5px}.bar{height:6px;background:#17283a;border-radius:10px;margin-top:8px;overflow:hidden}.fill{height:100%;border-radius:10px}
.impact{padding:16px;margin-top:14px;background:#10243a;border-radius:14px;border:1px solid var(--line)}.impact strong{font-size:38px}.risk{color:var(--warn)}.cascade{margin-top:14px}.chain{border-left:2px solid #31506e;padding-left:15px;margin-left:5px}.step{padding:7px 0;position:relative}.step:before{content:"";position:absolute;left:-21px;top:12px;width:9px;height:9px;border-radius:50%;background:var(--accent)}.step b{font-size:12px}.step span{display:block;color:var(--muted);font-size:10px;margin-top:2px}.rec{margin-top:14px}.recItem{border:1px solid var(--line);border-radius:10px;padding:9px;margin-top:7px;background:#0a1726}.recItem.best{border-color:var(--good)}.recItem span{float:right;color:var(--good);font-weight:800}
@media(max-width:1050px){main{grid-template-columns:250px 1fr}.right{grid-column:1/-1;display:grid;grid-template-columns:1fr 1fr;gap:15px}}@media(max-width:760px){main{display:block}.side,.mapPanel,.right{margin-bottom:15px}.map{height:480px}.right{display:block}}
</style></head><body>
<header><div class="brand">CITY<span>MIND</span></div><div class="status"><i class="dot"></i>DIGITAL TWIN ONLINE</div></header>
<main>
<section class="panel side"><div class="title">Scenario Builder</div>
<label>Scenario</label><select id="scenario"><option value="road_closure">Close major road</option><option value="large_event">Large event</option><option value="ev_surge">EV demand surge</option><option value="add_buses">Add buses</option><option value="emergency_corridor">Emergency corridor</option></select>
<label>Target road</label><select id="target"><option>R3</option><option>R2</option><option>R1</option></select>
<label>Intensity <span id="intensityLabel">100%</span></label><input id="intensity" type="range" min=".5" max="1.5" step=".1" value="1">
<label>Event demand <span id="eventLabel">1.0x</span></label><input id="event" type="range" min="1" max="3" step=".1" value="1">
<button onclick="runSimulation()">SIMULATE SCENARIO -&gt;</button>
<p style="margin-top:18px;color:var(--muted);font-size:11px;line-height:1.6"><b style="color:var(--text)">Prototype engine</b><br>Agent-inspired demand model + dependency graph + intervention ranking. Replace the synthetic engine with SUMO/TraCI in the next version.</p>
</section>
<section class="panel mapPanel"><div class="mapHead"><div><b id="mapTitle">Baseline City</b><div style="font-size:11px;color:var(--muted);margin-top:4px">Traffic / transit / emergency network</div></div><div id="simTime" style="color:var(--muted);font-size:12px">18:00</div></div>
<div class="map"><svg viewBox="0 0 800 600"><g>
<line class="road" id="R1" x1="80" y1="100" x2="720" y2="100"/><line class="road" id="R2" x1="80" y1="300" x2="720" y2="300"/><line class="road" id="R3" x1="80" y1="500" x2="720" y2="500"/><line class="road" id="R4" x1="250" y1="60" x2="250" y2="540"/><line class="road" id="R5" x1="520" y1="60" x2="520" y2="540"/></g><g id="nodes"></g></svg>
<div class="legend">normal / stressed / critical<br><b>Impact propagation is computed from the scenario.</b></div></div></section>
<section class="panel side right"><div class="title">System Impact</div><div class="metricGrid" id="metrics"></div>
<div class="impact"><div class="title">CITY IMPACT SCORE</div><strong id="impact">34</strong><span class="risk"> / 100</span><div style="font-size:11px;color:var(--muted)">Lower is better</div></div>
<div class="cascade"><div class="title">Impact Chain</div><div class="chain" id="cascade"></div></div>
<div class="rec"><div class="title">Recommended interventions</div><div id="recs"></div></div></section>
</main>
<script>
const $=id=>document.getElementById(id);
$("intensity").oninput=()=>{$("intensityLabel").textContent=Math.round($("intensity").value*100)+"%"};
$("event").oninput=()=>{$("eventLabel").textContent=Number($("event").value).toFixed(1)+"x"};
function mc(v){return v>=70?'#f26d7d':v>=45?'#f2bd5b':'#55d6a2'}
function metrics(m){const L={traffic:'Traffic',transit:'Transit',parking:'Parking',ev:'EV charging',emergency:'Emergency',passenger:'Passengers'};$("metrics").innerHTML=Object.entries(L).map(([k,l])=>`<div class="metric"><small>${l}</small><strong>${m[k]}</strong><div class="bar"><div class="fill" style="width:${m[k]}%;background:${mc(m[k])}"></div></div></div>`).join('')}
function map(m,s,t){['R1','R2','R3','R4','R5'].forEach(id=>$(id).setAttribute('class','road'));if(s==='road_closure')$(t).setAttribute('class','road hot');else if(m.traffic>=70)['R2','R3'].forEach(id=>$(id).setAttribute('class','road hot'));else if(m.traffic>=45)['R2','R3'].forEach(id=>$(id).setAttribute('class','road mid'));$("nodes").innerHTML=[[250,100,'J1'],[520,100,'J2'],[250,300,'J3'],[520,300,'J4'],[250,500,'J5'],[520,500,'J6']].map(([x,y,n])=>`<circle class="${m.traffic>70&&(n==='J4'||n==='J5')?'node hot':'node'}" cx="${x}" cy="${y}" r="11"/><text class="nodetext" x="${x+14}" y="${y+4}">${n}</text>`).join('')}
function chain(c){$("cascade").innerHTML=c.map((x,i)=>`<div class="step"><b>${i+1}. ${x[0]}</b><span>${x[1]}</span></div>`).join('')}
function recs(rs){$("recs").innerHTML=rs.map((r,i)=>`<div class="recItem ${i?'':'best'}"><b>${i===0?'TOP ':''}${r.name}</b><span>${r.impact}</span><div style="font-size:10px;color:var(--muted);margin-top:3px">${r.delay} min avg delay</div></div>`).join('')}
async function runSimulation(){const body={scenario:$("scenario").value,target:$("target").value,intensity:+$("intensity").value,event_demand:+$("event").value};$("mapTitle").textContent="Simulating...";const r=await fetch('/api/simulate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}).then(x=>x.json());metrics(r.result.metrics);$("impact").textContent=r.result.impact;map(r.result.metrics,body.scenario,body.target);chain(r.cascade);recs(r.recommendations);$("mapTitle").textContent=body.scenario.replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase());$("simTime").textContent="Simulation complete"}runSimulation();
</script></body></html>
'''
print("success")