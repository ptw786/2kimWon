[CARE_SIGNAL_예인_대시보드_프로토타입.html](https://github.com/user-attachments/files/34558631/CARE_SIGNAL_._._.html)# 2kimWon
[CARE_SIGNAL_%EC%98%88%EC%9D%B8_%EB%8C%80%EC%8B%9C%EB%B3%B4%EB%93%9C_%ED%94%84%EB%A1%9C%ED%86%A0%ED%83%80%EC%9E%85.html](https://github.com/user-attachments/files/34558556/CARE_SIGNAL_.EC.98.88.EC.9D.B8_.EB.8C.80.EC.8B.9C.EB.B3.B4.EB.93.9C_.ED.94.84.EB.A1.9C.ED.86.A0.ED.83.80.EC.9E.85.html)
<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CARE SIGNAL 대시보드</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f3f6f8;color:#203342;font-family:Arial,'Malgun Gothic',sans-serif}.app{display:flex;min-height:100vh}.side{width:220px;background:#183b56;color:white;padding:25px 16px}.logo{font-size:22px;font-weight:bold;padding:0 10px}.logo small{display:block;font-size:10px;color:#a9c0ce;letter-spacing:2px;margin-top:5px}.nav{margin-top:35px}.nav button{display:block;width:100%;padding:13px;border:0;border-radius:8px;background:none;color:#dce8ee;text-align:left;cursor:pointer;margin:4px 0}.nav button.active,.nav button:hover{background:#2b526c}.main{padding:28px;max-width:1400px;width:100%;margin:auto}.top{display:flex;justify-content:space-between;align-items:center;margin-bottom:24px}.eyebrow{font-size:11px;color:#2d8b83;font-weight:bold;letter-spacing:1px}.top h1{font-size:25px;margin:7px 0}.muted{color:#71818d;font-size:12px}.page{display:none}.page.active{display:block}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.card,.panel{background:white;border:1px solid #e4ebf0;border-radius:13px;padding:18px;margin-bottom:15px}.card .v{font-size:28px;font-weight:bold;margin:10px 0}.grid{display:grid;grid-template-columns:1.2fr 1fr;gap:15px;margin-top:15px}.panel h2{font-size:15px;margin:0 0 8px}.toolbar{display:flex;justify-content:space-between;gap:10px;margin:15px 0}.btn{background:#183b56;color:white;border:0;border-radius:8px;padding:10px 14px;cursor:pointer}.btn.light{background:#eaf1f5;color:#183b56}.search,input,select,textarea{border:1px solid #dfe7ec;border-radius:8px;padding:10px;font-size:12px}.search{min-width:220px}table{width:100%;border-collapse:collapse;font-size:12px}th{text-align:left;background:#f8fafb;color:#71818d;padding:11px}td{padding:12px 10px;border-bottom:1px solid #edf1f4}tbody tr{cursor:pointer}tbody tr:hover{background:#f8fbfc}.pill{display:inline-block;padding:5px 9px;border-radius:20px;font-size:10px;font-weight:bold}.red{background:#fff0ef;color:#c65353}.yellow{background:#fff6e6;color:#b77d22}.green{background:#eaf6f0;color:#39856b}.gray{background:#eef2f5;color:#667782}.priority{display:flex;justify-content:space-between;align-items:center;border:1px solid #e4ebf0;border-radius:9px;padding:12px;margin:8px 0;cursor:pointer}.priority b{font-size:12px}.priority small{display:block;color:#71818d;margin-top:4px}.week{display:grid;grid-template-columns:repeat(7,1fr);gap:5px}.day{border:1px solid #e4ebf0;border-radius:8px;padding:9px 3px;text-align:center;font-size:11px}.note{background:#f2f7f8;border-left:3px solid #2d8b83;padding:13px;border-radius:5px;font-size:12px;line-height:1.7;margin-top:12px}.modal{display:none;position:fixed;inset:0;background:#102b3b88;align-items:center;justify-content:center;padding:20px}.modal.show{display:flex}.box{background:white;border-radius:14px;padding:24px;width:min(600px,100%);max-height:90vh;overflow:auto}.form{display:grid;grid-template-columns:1fr 1fr;gap:12px}.form label{display:block;font-size:11px;color:#71818d;margin-bottom:5px}.form input,.form textarea{width:100%}.full{grid-column:1/-1}.detailgrid{display:grid;grid-template-columns:1fr 1fr;gap:9px;margin:15px 0}.detail{background:#f7fafb;padding:12px;border-radius:8px}.detail small{display:block;color:#71818d}.detail b{display:block;margin-top:6px;font-size:13px}
@media(max-width:850px){.side{width:175px}.cards{grid-template-columns:1fr 1fr}.grid{grid-template-columns:1fr}}@media(max-width:600px){.app{display:block}.side{width:100%;padding:15px}.nav{display:flex;overflow:auto;margin-top:15px}.nav button{white-space:nowrap;width:auto}.main{padding:15px}.cards{grid-template-columns:1fr 1fr}.week{gap:2px}}
</style></head><body>
<div class="app"><aside class="side"><div class="logo">CARE SIGNAL<small>SMART CARE MANAGEMENT</small></div><div class="nav">
<button class="active" data-page="home">▦ 대시보드</button><button data-page="seniors">♙ 어르신 관리</button><button data-page="calls">☏ 통화 기록</button><button data-page="priority">◎ 오늘 방문 우선순위</button></div><p class="muted" style="color:#b5c9d4;margin:30px 10px">AI 분석은 참고 정보이며<br>최종 확인과 조치는 담당자가<br>결정합니다.</p></aside>
<main class="main"><header class="top"><div><div class="eyebrow">CARE SIGNAL / ADMIN</div><h1 id="title">돌봄 현황 대시보드</h1></div><div class="muted" id="date"></div></header>
<section class="page active" id="home"><div class="cards">
<div class="card"><div class="muted">등록 어르신</div><div class="v" id="total">24명</div><div class="muted">시범 운영 등록 인원</div></div>
<div class="card"><div class="muted">오늘 통화 완료</div><div class="v">19명</div><div class="muted">전체 대상자 중 79%</div></div>
<div class="card"><div class="muted">주의 확인 필요</div><div class="v" style="color:#b77d22">4명</div><div class="muted">생활 변화 신호 누적</div></div>
<div class="card"><div class="muted">긴급 확인</div><div class="v" style="color:#c65353">1명</div><div class="muted">담당자 즉시 확인 필요</div></div></div>
<div class="grid"><div class="panel"><h2>오늘 우선 확인이 필요한 어르신</h2><p class="muted">최근 생활 변화 신호를 바탕으로 정렬한 시연 목록</p><div id="homePriority"></div><button class="btn light" onclick="page('priority')">전체 우선순위 보기 →</button></div>
<div class="panel"><h2>오늘의 돌봄 현황</h2><p class="muted">통화 진행 및 확인 상태</p><p>통화 완료　<b>19명</b></p><p>재통화 예정　<b>4명</b></p><p>미응답　<b>1명</b></p><div class="note">미응답 한 번만으로 응급상황을 확정하지 않습니다. 재발신과 담당자 확인을 거칩니다.</div></div></div>
<div class="panel"><h2>최근 7일 생활 기록</h2><p class="muted">어르신별 일주일 생활 변화 예시</p><div class="toolbar"><select id="weekPerson" onchange="week()"><option value="P-023">김정순 어르신</option><option value="P-041">박영수 어르신</option><option value="P-008">이말례 어르신</option></select><span class="muted">최근 7일 · 샘플 데이터</span></div><div id="weekTable"></div></div></section>
<section class="page" id="seniors"><div class="toolbar"><div><h2>어르신 관리</h2><p class="muted">기본 정보 등록 및 수정</p></div><button class="btn" onclick="register()">+ 어르신 등록</button></div><div class="toolbar"><input class="search" id="sq" placeholder="이름 또는 관리번호 검색" oninput="renderSeniors()"></div><div class="panel" style="overflow:auto;padding:0"><table><thead><tr><th>어르신</th><th>연령</th><th>연락처</th><th>최근 통화</th><th>상태</th><th>관리</th></tr></thead><tbody id="seniorRows"></tbody></table></div></section>
<section class="page" id="calls"><h2>통화 기록</h2><p class="muted">AI 안부 전화 결과와 대화 요약</p><div class="toolbar"><input class="search" id="cq" placeholder="이름·통화 내용 검색" oninput="renderCalls()"><select id="cf" onchange="renderCalls()"><option value="전체">전체 상태</option><option>완료</option><option>미응답</option></select></div><div class="panel" style="overflow:auto;padding:0"><table><thead><tr><th>통화 시각</th><th>어르신</th><th>결과</th><th>대화 요약</th><th>확인 상태</th></tr></thead><tbody id="callRows"></tbody></table></div></section>
<section class="page" id="priority"><h2>오늘 방문 우선순위</h2><p class="muted">AI가 정리한 생활 변화 신호를 바탕으로 담당자의 확인 순서를 제안합니다.</p><div class="panel" style="overflow:auto;padding:0"><table><thead><tr><th>순위</th><th>어르신</th><th>점수</th><th>감지된 변화</th><th>권고 조치</th><th>상세</th></tr></thead><tbody id="priorityRows"></tbody></table></div><div class="note">점수와 순위는 시연용 가상 값입니다. 실제 방문 여부와 응급 여부는 담당자가 판단합니다.</div></section>
<p class="muted" style="font-size:10px">※ 화면의 인원·통화·위험 신호·점수는 프로토타입 시연을 위한 가상 데이터입니다.</p></main></div>
<div class="modal" id="regModal"><div class="box"><div class="toolbar"><h2 id="regTitle">어르신 등록</h2><button class="btn light" onclick="closeModal('regModal')">닫기</button></div><form class="form" id="form"><div><label>이름</label><input id="name" required></div><div><label>연령</label><input id="age" type="number" required></div><div><label>연락처</label><input id="phone" required></div><div><label>관리번호</label><input id="pid" required></div><div class="full"><label>참고 사항</label><textarea id="memo" rows="2"></textarea></div><div class="full" style="text-align:right"><button class="btn">저장</button></div></form></div></div>
<div class="modal" id="detailModal"><div class="box"><div class="toolbar"><h2 id="detailTitle">상세 정보</h2><button class="btn light" onclick="closeModal('detailModal')">닫기</button></div><div id="detail"></div></div></div>
<script>
let seniors=[
{id:"P-023",name:"김정순",age:78,phone:"010-****-1023",last:"오늘 10:12",status:"주의",memo:"식사 준비 어려움, 수면 불편 반복"},
{id:"P-041",name:"박영수",age:82,phone:"010-****-2041",last:"오늘 10:25",status:"확인 필요",memo:"평소와 다른 미응답 1회"},
{id:"P-008",name:"이말례",age:85,phone:"010-****-1008",last:"오늘 09:48",status:"긴급",memo:"구조 요청 의심 이벤트 감지"},
{id:"P-015",name:"최순자",age:74,phone:"010-****-3015",last:"오늘 10:40",status:"정상",memo:"특이사항 없음"},
{id:"P-032",name:"정만수",age:80,phone:"010-****-3032",last:"어제 10:03",status:"정상",memo:"특이사항 없음"}];
let calls=[
{time:"오늘 10:40",id:"P-015",name:"최순자",result:"완료",summary:"식사와 수면 모두 평소와 비슷하다고 응답",meal:"양호",sleep:"양호",pain:"없음",state:"확인 완료"},
{time:"오늘 10:25",id:"P-041",name:"박영수",result:"미응답",summary:"1차 발신에 응답하지 않아 재통화 필요",meal:"확인 불가",sleep:"확인 불가",pain:"확인 불가",state:"확인 대기"},
{time:"오늘 10:12",id:"P-023",name:"김정순",result:"완료",summary:"최근 식사 준비가 어렵고 잠들기 불편하다고 반복 언급",meal:"식사 준비 어려움",sleep:"불편 호소",pain:"없음",state:"주의 확인"},
{time:"오늘 09:48",id:"P-008",name:"이말례",result:"완료",summary:"생활음향에서 구조 요청 의심 이벤트 감지, 담당자 확인 필요",meal:"보통",sleep:"확인",pain:"확인 필요",state:"긴급 확인"}];
let priority=[{id:"P-008",name:"이말례",score:92,level:"긴급",change:"구조 요청 의심 이벤트 감지",action:"즉시 전화 확인 및 긴급 대응 절차"},{id:"P-023",name:"김정순",score:78,level:"주의",change:"식사 곤란 3일 반복, 수면 불편 2회",action:"당일 안부 전화 및 필요 시 방문"},{id:"P-041",name:"박영수",score:55,level:"확인 필요",change:"평소와 다른 미응답 1회",action:"재발신 후 연락 상태 확인"},{id:"P-032",name:"정만수",score:22,level:"정상",change:"특이 변화 없음",action:"정기 모니터링 유지"}];
let weeks={"P-023":[["월","양호","양호","특이사항 없음"],["화","양호","보통","특이사항 없음"],["수","간단히 식사","불편","식사 준비 어려움"],["목","식사 어려움","불편","추가 확인 필요"],["금","식사 어려움","불편","반복 호소"],["토","확인 예정","예정","통화 예정"],["일","확인 예정","예정","통화 예정"]],"P-041":[["월","양호","양호","특이사항 없음"],["화","양호","양호","특이사항 없음"],["수","양호","보통","특이사항 없음"],["목","양호","양호","특이사항 없음"],["금","확인 불가","확인 불가","미응답"],["토","확인 예정","예정","재통화 예정"],["일","확인 예정","예정","통화 예정"]],"P-008":[["월","양호","양호","특이사항 없음"],["화","양호","양호","특이사항 없음"],["수","양호","보통","특이사항 없음"],["목","보통","불편","추가 확인"],["금","확인","확인","구조 요청 의심 이벤트"],["토","확인 예정","예정","담당자 확인"],["일","확인 예정","예정","통화 예정"]]};
function badge(s){let c=s==="긴급"?"red":s==="주의"||s==="확인 필요"?"yellow":s==="정상"||s==="완료"?"green":"gray";return `<span class="pill ${c}">${s}</span>`}
function page(id){document.querySelectorAll(".page").forEach(x=>x.classList.toggle("active",x.id===id));document.querySelectorAll(".nav button").forEach(x=>x.classList.toggle("active",x.dataset.page===id));document.getElementById("title").textContent=({home:"돌봄 현황 대시보드",seniors:"어르신 관리",calls:"통화 기록",priority:"오늘 방문 우선순위"})[id]}
document.querySelectorAll(".nav button").forEach(b=>b.onclick=()=>page(b.dataset.page));
function renderSeniors(){let q=(document.getElementById("sq").value||"").toLowerCase();document.getElementById("total").textContent=seniors.length+"명";document.getElementById("seniorRows").innerHTML=seniors.filter(s=>(s.name+s.id).toLowerCase().includes(q)).map(s=>`<tr><td><b>${s.name} 어르신</b><br><small>${s.id}</small></td><td>${s.age}세</td><td>${s.phone}</td><td>${s.last}</td><td>${badge(s.status)}</td><td><button class="btn light" onclick="edit('${s.id}')">수정</button></td></tr>`).join("")}
function renderCalls(){let q=(document.getElementById("cq").value||"").toLowerCase(),f=document.getElementById("cf").value;document.getElementById("callRows").innerHTML=calls.filter(c=>(c.name+c.summary).toLowerCase().includes(q)&&(f==="전체"||f===c.result)).map((c,i)=>`<tr onclick="callDetail(${i})"><td>${c.time}</td><td><b>${c.name}</b><br><small>${c.id}</small></td><td>${badge(c.result)}</td><td>${c.summary}</td><td>${badge(c.state==="긴급 확인"?"긴급":c.state==="주의 확인"?"주의":c.state==="확인 대기"?"확인 필요":"정상")}</td></tr>`).join("")}
function renderPriority(){document.getElementById("priorityRows").innerHTML=priority.map((p,i)=>`<tr><td>${i+1}위</td><td>${p.name} 어르신<br><small>${p.id}</small></td><td><b>${p.score}</b>점</td><td>${p.change}</td><td>${p.action}</td><td><button class="btn light" onclick="personDetail('${p.id}')">상세</button></td></tr>`).join("");document.getElementById("homePriority").innerHTML=priority.slice(0,3).map((p,i)=>`<div class="priority" onclick="personDetail('${p.id}')"><b>${i+1}. ${p.name} 어르신<small>${p.change}</small></b>${badge(p.level)}</div>`).join("")}
function week(){let id=document.getElementById("weekPerson").value;document.getElementById("weekTable").innerHTML=`<table><thead><tr><th>요일</th><th>식사</th><th>수면</th><th>생활 변화</th></tr></thead><tbody>${weeks[id].map(r=>`<tr><td>${r[0]}</td><td>${r[1]}</td><td>${r[2]}</td><td>${r[3]}</td></tr>`).join("")}</tbody></table>`}
function register(){document.getElementById("form").reset();document.getElementById("regTitle").textContent="어르신 등록";document.getElementById("regModal").dataset.edit="";document.getElementById("pid").disabled=false;document.getElementById("regModal").classList.add("show")}
function edit(id){let s=seniors.find(x=>x.id===id);register();document.getElementById("regTitle").textContent="어르신 정보 수정";["name","age","phone","pid","memo"].forEach((k,i)=>document.getElementById(k).value=[s.name,s.age,s.phone,s.id,s.memo][i]);document.getElementById("pid").disabled=true;document.getElementById("regModal").dataset.edit=id}
document.getElementById("form").onsubmit=e=>{e.preventDefault();let editId=document.getElementById("regModal").dataset.edit;let o={id:document.getElementById("pid").value,name:document.getElementById("name").value,age:document.getElementById("age").value,phone:document.getElementById("phone").value,last:"등록 완료",status:"정상",memo:document.getElementById("memo").value};if(editId){let i=seniors.findIndex(s=>s.id===editId);seniors[i]={...seniors[i],...o}}else seniors.push(o);close("regModal");renderSeniors()}
function callDetail(i){let c=calls[i];document.getElementById("detailTitle").textContent=c.name+" 어르신 · "+c.time;document.getElementById("detail").innerHTML=`<div class="detailgrid">${[["통화 결과",c.result],["관리번호",c.id],["식사 상태",c.meal],["수면 상태",c.sleep],["통증·건강",c.pain],["담당자 확인",c.state]].map(x=>`<div class="detail"><small>${x[0]}</small><b>${x[1]}</b></div>`).join("")}</div><div class="note"><b>AI 대화 요약</b><br>${c.summary}<br><br><b>권고</b><br>이전 기록과 함께 확인한 뒤 필요하면 추가 안부 전화 또는 방문 상담을 진행합니다.</div>`;document.getElementById("detailModal").classList.add("show")}
function personDetail(id){let s=seniors.find(x=>x.id===id),p=priority.find(x=>x.id===id);document.getElementById("detailTitle").textContent=s.name+" 어르신 · "+id;document.getElementById("detail").innerHTML=`<div class="detailgrid"><div class="detail"><small>연령</small><b>${s.age}세</b></div><div class="detail"><small>연락처</small><b>${s.phone}</b></div><div class="detail"><small>최근 통화</small><b>${s.last}</b></div><div class="detail"><small>현재 상태</small><b>${s.status}</b></div></div><div class="note"><b>최근 확인 사항</b><br>${s.memo}<br><br><b>AI 우선순위 근거</b><br>${p.change}<br><br><b>권고 조치</b><br>${p.action}</div>`;document.getElementById("detailModal").classList.add("show")}
function close(id){document.getElementById(id).classList.remove("show")}
document.getElementById("date").textContent=new Intl.DateTimeFormat("ko-KR",{dateStyle:"full"}).format(new Date());renderSeniors();renderCalls();renderPriority();week();
</script></body></html>


[Upl<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CARE SIGNAL 대시보드</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f3f6f8;color:#203342;font-family:Arial,'Malgun Gothic',sans-serif}.app{display:flex;min-height:100vh}.side{width:220px;background:#183b56;color:white;padding:25px 16px}.logo{font-size:22px;font-weight:bold;padding:0 10px}.logo small{display:block;font-size:10px;color:#a9c0ce;letter-spacing:2px;margin-top:5px}.nav{margin-top:35px}.nav button{display:block;width:100%;padding:13px;border:0;border-radius:8px;background:none;color:#dce8ee;text-align:left;cursor:pointer;margin:4px 0}.nav button.active,.nav button:hover{background:#2b526c}.main{padding:28px;max-width:1400px;width:100%;margin:auto}.top{display:flex;justify-content:space-between;align-items:center;margin-bottom:24px}.eyebrow{font-size:11px;color:#2d8b83;font-weight:bold;letter-spacing:1px}.top h1{font-size:25px;margin:7px 0}.muted{color:#71818d;font-size:12px}.page{display:none}.page.active{display:block}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.card,.panel{background:white;border:1px solid #e4ebf0;border-radius:13px;padding:18px;margin-bottom:15px}.card .v{font-size:28px;font-weight:bold;margin:10px 0}.grid{display:grid;grid-template-columns:1.2fr 1fr;gap:15px;margin-top:15px}.panel h2{font-size:15px;margin:0 0 8px}.toolbar{display:flex;justify-content:space-between;gap:10px;margin:15px 0}.btn{background:#183b56;color:white;border:0;border-radius:8px;padding:10px 14px;cursor:pointer}.btn.light{background:#eaf1f5;color:#183b56}.search,input,select,textarea{border:1px solid #dfe7ec;border-radius:8px;padding:10px;font-size:12px}.search{min-width:220px}table{width:100%;border-collapse:collapse;font-size:12px}th{text-align:left;background:#f8fafb;color:#71818d;padding:11px}td{padding:12px 10px;border-bottom:1px solid #edf1f4}tbody tr{cursor:pointer}tbody tr:hover{background:#f8fbfc}.pill{display:inline-block;padding:5px 9px;border-radius:20px;font-size:10px;font-weight:bold}.red{background:#fff0ef;color:#c65353}.yellow{background:#fff6e6;color:#b77d22}.green{background:#eaf6f0;color:#39856b}.gray{background:#eef2f5;color:#667782}.priority{display:flex;justify-content:space-between;align-items:center;border:1px solid #e4ebf0;border-radius:9px;padding:12px;margin:8px 0;cursor:pointer}.priority b{font-size:12px}.priority small{display:block;color:#71818d;margin-top:4px}.week{display:grid;grid-template-columns:repeat(7,1fr);gap:5px}.day{border:1px solid #e4ebf0;border-radius:8px;padding:9px 3px;text-align:center;font-size:11px}.note{background:#f2f7f8;border-left:3px solid #2d8b83;padding:13px;border-radius:5px;font-size:12px;line-height:1.7;margin-top:12px}.modal{display:none;position:fixed;inset:0;background:#102b3b88;align-items:center;justify-content:center;padding:20px}.modal.show{display:flex}.box{background:white;border-radius:14px;padding:24px;width:min(600px,100%);max-height:90vh;overflow:auto}.form{display:grid;grid-template-columns:1fr 1fr;gap:12px}.form label{display:block;font-size:11px;color:#71818d;margin-bottom:5px}.form input,.form textarea{width:100%}.full{grid-column:1/-1}.detailgrid{display:grid;grid-template-columns:1fr 1fr;gap:9px;margin:15px 0}.detail{background:#f7fafb;padding:12px;border-radius:8px}.detail small{display:block;color:#71818d}.detail b{display:block;margin-top:6px;font-size:13px}
@media(max-width:850px){.side{width:175px}.cards{grid-template-columns:1fr 1fr}.grid{grid-template-columns:1fr}}@media(max-width:600px){.app{display:block}.side{width:100%;padding:15px}.nav{display:flex;overflow:auto;margin-top:15px}.nav button{white-space:nowrap;width:auto}.main{padding:15px}.cards{grid-template-columns:1fr 1fr}.week{gap:2px}}
</style></head><body>
<div class="app"><aside class="side"><div class="logo">CARE SIGNAL<small>SMART CARE MANAGEMENT</small></div><div class="nav">
<button class="active" data-page="home">▦ 대시보드</button><button data-page="seniors">♙ 어르신 관리</button><button data-page="calls">☏ 통화 기록</button><button data-page="priority">◎ 오늘 방문 우선순위</button></div><p class="muted" style="color:#b5c9d4;margin:30px 10px">AI 분석은 참고 정보이며<br>최종 확인과 조치는 담당자가<br>결정합니다.</p></aside>
<main class="main"><header class="top"><div><div class="eyebrow">CARE SIGNAL / ADMIN</div><h1 id="title">돌봄 현황 대시보드</h1></div><div class="muted" id="date"></div></header>
<section class="page active" id="home"><div class="cards">
<div class="card"><div class="muted">등록 어르신</div><div class="v" id="total">24명</div><div class="muted">시범 운영 등록 인원</div></div>
<div class="card"><div class="muted">오늘 통화 완료</div><div class="v">19명</div><div class="muted">전체 대상자 중 79%</div></div>
<div class="card"><div class="muted">주의 확인 필요</div><div class="v" style="color:#b77d22">4명</div><div class="muted">생활 변화 신호 누적</div></div>
<div class="card"><div class="muted">긴급 확인</div><div class="v" style="color:#c65353">1명</div><div class="muted">담당자 즉시 확인 필요</div></div></div>
<div class="grid"><div class="panel"><h2>오늘 우선 확인이 필요한 어르신</h2><p class="muted">최근 생활 변화 신호를 바탕으로 정렬한 시연 목록</p><div id="homePriority"></div><button class="btn light" onclick="page('priority')">전체 우선순위 보기 →</button></div>
<div class="panel"><h2>오늘의 돌봄 현황</h2><p class="muted">통화 진행 및 확인 상태</p><p>통화 완료　<b>19명</b></p><p>재통화 예정　<b>4명</b></p><p>미응답　<b>1명</b></p><div class="note">미응답 한 번만으로 응급상황을 확정하지 않습니다. 재발신과 담당자 확인을 거칩니다.</div></div></div>
<div class="panel"><h2>최근 7일 생활 기록</h2><p class="muted">어르신별 일주일 생활 변화 예시</p><div class="toolbar"><select id="weekPerson" onchange="week()"><option value="P-023">김정순 어르신</option><option value="P-041">박영수 어르신</option><option value="P-008">이말례 어르신</option></select><span class="muted">최근 7일 · 샘플 데이터</span></div><div id="weekTable"></div></div></section>
<section class="page" id="seniors"><div class="toolbar"><div><h2>어르신 관리</h2><p class="muted">기본 정보 등록 및 수정</p></div><button class="btn" onclick="register()">+ 어르신 등록</button></div><div class="toolbar"><input class="search" id="sq" placeholder="이름 또는 관리번호 검색" oninput="renderSeniors()"></div><div class="panel" style="overflow:auto;padding:0"><table><thead><tr><th>어르신</th><th>연령</th><th>연락처</th><th>최근 통화</th><th>상태</th><th>관리</th></tr></thead><tbody id="seniorRows"></tbody></table></div></section>
<section class="page" id="calls"><h2>통화 기록</h2><p class="muted">AI 안부 전화 결과와 대화 요약</p><div class="toolbar"><input class="search" id="cq" placeholder="이름·통화 내용 검색" oninput="renderCalls()"><select id="cf" onchange="renderCalls()"><option value="전체">전체 상태</option><option>완료</option><option>미응답</option></select></div><div class="panel" style="overflow:auto;padding:0"><table><thead><tr><th>통화 시각</th><th>어르신</th><th>결과</th><th>대화 요약</th><th>확인 상태</th></tr></thead><tbody id="callRows"></tbody></table></div></section>
<section class="page" id="priority"><h2>오늘 방문 우선순위</h2><p class="muted">AI가 정리한 생활 변화 신호를 바탕으로 담당자의 확인 순서를 제안합니다.</p><div class="panel" style="overflow:auto;padding:0"><table><thead><tr><th>순위</th><th>어르신</th><th>점수</th><th>감지된 변화</th><th>권고 조치</th><th>상세</th></tr></thead><tbody id="priorityRows"></tbody></table></div><div class="note">점수와 순위는 시연용 가상 값입니다. 실제 방문 여부와 응급 여부는 담당자가 판단합니다.</div></section>
<p class="muted" style="font-size:10px">※ 화면의 인원·통화·위험 신호·점수는 프로토타입 시연을 위한 가상 데이터입니다.</p></main></div>
<div class="modal" id="regModal"><div class="box"><div class="toolbar"><h2 id="regTitle">어르신 등록</h2><button class="btn light" onclick="closeModal('regModal')">닫기</button></div><form class="form" id="form"><div><label>이름</label><input id="name" required></div><div><label>연령</label><input id="age" type="number" required></div><div><label>연락처</label><input id="phone" required></div><div><label>관리번호</label><input id="pid" required></div><div class="full"><label>참고 사항</label><textarea id="memo" rows="2"></textarea></div><div class="full" style="text-align:right"><button class="btn">저장</button></div></form></div></div>
<div class="modal" id="detailModal"><div class="box"><div class="toolbar"><h2 id="detailTitle">상세 정보</h2><button class="btn light" onclick="closeModal('detailModal')">닫기</button></div><div id="detail"></div></div></div>
<script>
let seniors=[
{id:"P-023",name:"김정순",age:78,phone:"010-****-1023",last:"오늘 10:12",status:"주의",memo:"식사 준비 어려움, 수면 불편 반복"},
{id:"P-041",name:"박영수",age:82,phone:"010-****-2041",last:"오늘 10:25",status:"확인 필요",memo:"평소와 다른 미응답 1회"},
{id:"P-008",name:"이말례",age:85,phone:"010-****-1008",last:"오늘 09:48",status:"긴급",memo:"구조 요청 의심 이벤트 감지"},
{id:"P-015",name:"최순자",age:74,phone:"010-****-3015",last:"오늘 10:40",status:"정상",memo:"특이사항 없음"},
{id:"P-032",name:"정만수",age:80,phone:"010-****-3032",last:"어제 10:03",status:"정상",memo:"특이사항 없음"}];
let calls=[
{time:"오늘 10:40",id:"P-015",name:"최순자",result:"완료",summary:"식사와 수면 모두 평소와 비슷하다고 응답",meal:"양호",sleep:"양호",pain:"없음",state:"확인 완료"},
{time:"오늘 10:25",id:"P-041",name:"박영수",result:"미응답",summary:"1차 발신에 응답하지 않아 재통화 필요",meal:"확인 불가",sleep:"확인 불가",pain:"확인 불가",state:"확인 대기"},
{time:"오늘 10:12",id:"P-023",name:"김정순",result:"완료",summary:"최근 식사 준비가 어렵고 잠들기 불편하다고 반복 언급",meal:"식사 준비 어려움",sleep:"불편 호소",pain:"없음",state:"주의 확인"},
{time:"오늘 09:48",id:"P-008",name:"이말례",result:"완료",summary:"생활음향에서 구조 요청 의심 이벤트 감지, 담당자 확인 필요",meal:"보통",sleep:"확인",pain:"확인 필요",state:"긴급 확인"}];
let priority=[{id:"P-008",name:"이말례",score:92,level:"긴급",change:"구조 요청 의심 이벤트 감지",action:"즉시 전화 확인 및 긴급 대응 절차"},{id:"P-023",name:"김정순",score:78,level:"주의",change:"식사 곤란 3일 반복, 수면 불편 2회",action:"당일 안부 전화 및 필요 시 방문"},{id:"P-041",name:"박영수",score:55,level:"확인 필요",change:"평소와 다른 미응답 1회",action:"재발신 후 연락 상태 확인"},{id:"P-032",name:"정만수",score:22,level:"정상",change:"특이 변화 없음",action:"정기 모니터링 유지"}];
let weeks={"P-023":[["월","양호","양호","특이사항 없음"],["화","양호","보통","특이사항 없음"],["수","간단히 식사","불편","식사 준비 어려움"],["목","식사 어려움","불편","추가 확인 필요"],["금","식사 어려움","불편","반복 호소"],["토","확인 예정","예정","통화 예정"],["일","확인 예정","예정","통화 예정"]],"P-041":[["월","양호","양호","특이사항 없음"],["화","양호","양호","특이사항 없음"],["수","양호","보통","특이사항 없음"],["목","양호","양호","특이사항 없음"],["금","확인 불가","확인 불가","미응답"],["토","확인 예정","예정","재통화 예정"],["일","확인 예정","예정","통화 예정"]],"P-008":[["월","양호","양호","특이사항 없음"],["화","양호","양호","특이사항 없음"],["수","양호","보통","특이사항 없음"],["목","보통","불편","추가 확인"],["금","확인","확인","구조 요청 의심 이벤트"],["토","확인 예정","예정","담당자 확인"],["일","확인 예정","예정","통화 예정"]]};
function badge(s){let c=s==="긴급"?"red":s==="주의"||s==="확인 필요"?"yellow":s==="정상"||s==="완료"?"green":"gray";return `<span class="pill ${c}">${s}</span>`}
function page(id){document.querySelectorAll(".page").forEach(x=>x.classList.toggle("active",x.id===id));document.querySelectorAll(".nav button").forEach(x=>x.classList.toggle("active",x.dataset.page===id));document.getElementById("title").textContent=({home:"돌봄 현황 대시보드",seniors:"어르신 관리",calls:"통화 기록",priority:"오늘 방문 우선순위"})[id]}
document.querySelectorAll(".nav button").forEach(b=>b.onclick=()=>page(b.dataset.page));
function renderSeniors(){let q=(document.getElementById("sq").value||"").toLowerCase();document.getElementById("total").textContent=seniors.length+"명";document.getElementById("seniorRows").innerHTML=seniors.filter(s=>(s.name+s.id).toLowerCase().includes(q)).map(s=>`<tr><td><b>${s.name} 어르신</b><br><small>${s.id}</small></td><td>${s.age}세</td><td>${s.phone}</td><td>${s.last}</td><td>${badge(s.status)}</td><td><button class="btn light" onclick="edit('${s.id}')">수정</button></td></tr>`).join("")}
function renderCalls(){let q=(document.getElementById("cq").value||"").toLowerCase(),f=document.getElementById("cf").value;document.getElementById("callRows").innerHTML=calls.filter(c=>(c.name+c.summary).toLowerCase().includes(q)&&(f==="전체"||f===c.result)).map((c,i)=>`<tr onclick="callDetail(${i})"><td>${c.time}</td><td><b>${c.name}</b><br><small>${c.id}</small></td><td>${badge(c.result)}</td><td>${c.summary}</td><td>${badge(c.state==="긴급 확인"?"긴급":c.state==="주의 확인"?"주의":c.state==="확인 대기"?"확인 필요":"정상")}</td></tr>`).join("")}
function renderPriority(){document.getElementById("priorityRows").innerHTML=priority.map((p,i)=>`<tr><td>${i+1}위</td><td>${p.name} 어르신<br><small>${p.id}</small></td><td><b>${p.score}</b>점</td><td>${p.change}</td><td>${p.action}</td><td><button class="btn light" onclick="personDetail('${p.id}')">상세</button></td></tr>`).join("");document.getElementById("homePriority").innerHTML=priority.slice(0,3).map((p,i)=>`<div class="priority" onclick="personDetail('${p.id}')"><b>${i+1}. ${p.name} 어르신<small>${p.change}</small></b>${badge(p.level)}</div>`).join("")}
function week(){let id=document.getElementById("weekPerson").value;document.getElementById("weekTable").innerHTML=`<table><thead><tr><th>요일</th><th>식사</th><th>수면</th><th>생활 변화</th></tr></thead><tbody>${weeks[id].map(r=>`<tr><td>${r[0]}</td><td>${r[1]}</td><td>${r[2]}</td><td>${r[3]}</td></tr>`).join("")}</tbody></table>`}
function register(){document.getElementById("form").reset();document.getElementById("regTitle").textContent="어르신 등록";document.getElementById("regModal").dataset.edit="";document.getElementById("pid").disabled=false;document.getElementById("regModal").classList.add("show")}
function edit(id){let s=seniors.find(x=>x.id===id);register();document.getElementById("regTitle").textContent="어르신 정보 수정";["name","age","phone","pid","memo"].forEach((k,i)=>document.getElementById(k).value=[s.name,s.age,s.phone,s.id,s.memo][i]);document.getElementById("pid").disabled=true;document.getElementById("regModal").dataset.edit=id}
document.getElementById("form").onsubmit=e=>{e.preventDefault();let editId=document.getElementById("regModal").dataset.edit;let o={id:document.getElementById("pid").value,name:document.getElementById("name").value,age:document.getElementById("age").value,phone:document.getElementById("phone").value,last:"등록 완료",status:"정상",memo:document.getElementById("memo").value};if(editId){let i=seniors.findIndex(s=>s.id===editId);seniors[i]={...seniors[i],...o}}else seniors.push(o);close("regModal");renderSeniors()}
function callDetail(i){let c=calls[i];document.getElementById("detailTitle").textContent=c.name+" 어르신 · "+c.time;document.getElementById("detail").innerHTML=`<div class="detailgrid">${[["통화 결과",c.result],["관리번호",c.id],["식사 상태",c.meal],["수면 상태",c.sleep],["통증·건강",c.pain],["담당자 확인",c.state]].map(x=>`<div class="detail"><small>${x[0]}</small><b>${x[1]}</b></div>`).join("")}</div><div class="note"><b>AI 대화 요약</b><br>${c.summary}<br><br><b>권고</b><br>이전 기록과 함께 확인한 뒤 필요하면 추가 안부 전화 또는 방문 상담을 진행합니다.</div>`;document.getElementById("detailModal").classList.add("show")}
function personDetail(id){let s=seniors.find(x=>x.id===id),p=priority.find(x=>x.id===id);document.getElementById("detailTitle").textContent=s.name+" 어르신 · "+id;document.getElementById("detail").innerHTML=`<div class="detailgrid"><div class="detail"><small>연령</small><b>${s.age}세</b></div><div class="detail"><small>연락처</small><b>${s.phone}</b></div><div class="detail"><small>최근 통화</small><b>${s.last}</b></div><div class="detail"><small>현재 상태</small><b>${s.status}</b></div></div><div class="note"><b>최근 확인 사항</b><br>${s.memo}<br><br><b>AI 우선순위 근거</b><br>${p.change}<br><br><b>권고 조치</b><br>${p.action}</div>`;document.getElementById("detailModal").classList.add("show")}
function close(id){document.getElementById(id).classList.remove("show")}
document.getElementById("date").textContent=new Intl.DateTimeFormat("ko-KR",{dateStyle:"full"}).format(new Date());renderSeniors();renderCalls();renderPriority();week();
</script></body></html>oading CARE_SIGNAL_예인_대시보드_프로토타입.html…]()


[01_대시보드.html](https://github.com/user-attachments/files/34558719/01_.html)
<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>통합 대시보드 - CARE SIGNAL</title><style>
*{box-sizing:border-box}body{margin:0;background:#f4f7fb;color:#263449;font-family:Arial,'Malgun Gothic',sans-serif}
header{background:white;padding:22px 5%;border-bottom:1px solid #e5eaf2;font-size:21px;font-weight:800;color:#172b4d}
header span{color:#4776e6}main{max-width:1100px;margin:32px auto;padding:0 20px}
small,.muted{color:#718096}.eyebrow{color:#4776e6;font-size:12px;font-weight:bold;letter-spacing:1px}
h1{margin:8px 0;font-size:29px}h2{font-size:18px;margin:0 0 15px}
.panel,.stat{background:white;border:1px solid #e5eaf2;border-radius:15px;padding:21px;margin-bottom:16px}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:13px}.two{display:grid;grid-template-columns:1fr 1fr;gap:15px}
.num{font-size:29px;font-weight:800;color:#172b4d;margin-top:8px}
table{width:100%;border-collapse:collapse;font-size:14px}th,td{text-align:left;padding:12px 9px;border-bottom:1px solid #e5eaf2}th{color:#718096;background:#fafbfd}
input,select,textarea{padding:11px;border:1px solid #d9e1ec;border-radius:8px;font:inherit;width:100%;background:white}
button{padding:10px 14px;border:0;border-radius:8px;background:#4776e6;color:white;font-weight:bold;cursor:pointer}
button.alt{background:#edf2ff;color:#3459b5}button.del{background:#fff0ef;color:#c44}
.tag{display:inline-block;border-radius:20px;padding:5px 9px;background:#e9f8f1;color:#26966f;font-size:12px;font-weight:bold}
.tag.warn{background:#fff7e5;color:#a87512}.tag.red{background:#fff0ef;color:#d9534f}
.formgrid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.field label{display:block;font-size:12px;color:#718096;margin-bottom:5px}
.note{font-size:12px;color:#718096;line-height:1.6}
@media(max-width:700px){.grid,.two,.formgrid{grid-template-columns:1fr 1fr}}@media(max-width:480px){.grid,.two,.formgrid{grid-template-columns:1fr}}
</style></head><body><header>CARE <span>SIGNAL</span></header><main><div class="eyebrow">01 / CARE MANAGEMENT</div><h1>통합 대시보드</h1><p class="muted">AI 안부 확인 결과를 바탕으로 생활지원사의 돌봄 업무를 돕는 화면입니다.</p>
<div class="grid">
<div class="stat"><small>등록 어르신</small><div class="num">128명</div></div>
<div class="stat"><small>오늘 통화 완료</small><div class="num">96건</div></div>
<div class="stat"><small>주의 확인 필요</small><div class="num" style="color:#d69e2e">7명</div></div>
<div class="stat"><small>긴급 확인 필요</small><div class="num" style="color:#d9534f">2명</div></div></div>
<div class="two"><section class="panel"><h2>오늘 우선 확인 대상</h2><table><tr><th>어르신</th><th>상태</th><th>사유</th></tr>
<tr><td>김OO</td><td><span class="tag red">긴급</span></td><td>연속 미응답</td></tr><tr><td>박OO</td><td><span class="tag warn">주의</span></td><td>식사 응답 변화</td></tr><tr><td>이OO</td><td><span class="tag warn">주의</span></td><td>수면 불편 호소</td></tr></table></section>
<section class="panel"><h2>최근 통화 현황</h2><table><tr><th>시간</th><th>어르신</th><th>결과</th></tr><tr><td>09:10</td><td>최OO</td><td><span class="tag">완료</span></td></tr><tr><td>09:05</td><td>박OO</td><td><span class="tag">완료</span></td></tr><tr><td>08:50</td><td>김OO</td><td><span class="tag red">미응답</span></td></tr></table></section></div>
<p class="note">※ 화면 수치와 대상자는 기능 시연용 가상 데이터입니다.</p></main><script></script></body></html>

[02_어르신_관리.html](https://github.com/user-attachments/files/34558721/02_._.html)
<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>어르신 관리 - CARE SIGNAL</title><style>
*{box-sizing:border-box}body{margin:0;background:#f4f7fb;color:#263449;font-family:Arial,'Malgun Gothic',sans-serif}
header{background:white;padding:22px 5%;border-bottom:1px solid #e5eaf2;font-size:21px;font-weight:800;color:#172b4d}
header span{color:#4776e6}main{max-width:1100px;margin:32px auto;padding:0 20px}
small,.muted{color:#718096}.eyebrow{color:#4776e6;font-size:12px;font-weight:bold;letter-spacing:1px}
h1{margin:8px 0;font-size:29px}h2{font-size:18px;margin:0 0 15px}
.panel,.stat{background:white;border:1px solid #e5eaf2;border-radius:15px;padding:21px;margin-bottom:16px}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:13px}.two{display:grid;grid-template-columns:1fr 1fr;gap:15px}
.num{font-size:29px;font-weight:800;color:#172b4d;margin-top:8px}
table{width:100%;border-collapse:collapse;font-size:14px}th,td{text-align:left;padding:12px 9px;border-bottom:1px solid #e5eaf2}th{color:#718096;background:#fafbfd}
input,select,textarea{padding:11px;border:1px solid #d9e1ec;border-radius:8px;font:inherit;width:100%;background:white}
button{padding:10px 14px;border:0;border-radius:8px;background:#4776e6;color:white;font-weight:bold;cursor:pointer}
button.alt{background:#edf2ff;color:#3459b5}button.del{background:#fff0ef;color:#c44}
.tag{display:inline-block;border-radius:20px;padding:5px 9px;background:#e9f8f1;color:#26966f;font-size:12px;font-weight:bold}
.tag.warn{background:#fff7e5;color:#a87512}.tag.red{background:#fff0ef;color:#d9534f}
.formgrid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.field label{display:block;font-size:12px;color:#718096;margin-bottom:5px}
.note{font-size:12px;color:#718096;line-height:1.6}
@media(max-width:700px){.grid,.two,.formgrid{grid-template-columns:1fr 1fr}}@media(max-width:480px){.grid,.two,.formgrid{grid-template-columns:1fr}}
</style></head><body><header>CARE <span>SIGNAL</span></header><main><div class="eyebrow">02 / CARE MANAGEMENT</div><h1>어르신 관리</h1><p class="muted">AI 안부 확인 결과를 바탕으로 생활지원사의 돌봄 업무를 돕는 화면입니다.</p>
<section class="panel"><h2>어르신 등록 및 수정</h2><div class="formgrid">
<div class="field"><label>성명</label><input id="name" placeholder="예: 김OO"></div><div class="field"><label>연락처</label><input id="phone" placeholder="010-0000-0000"></div>
<div class="field"><label>담당 생활지원사</label><input id="worker" placeholder="담당자 이름"></div><div class="field"><label>정기 통화 시간</label><input id="time" type="time" value="09:00"></div>
<div class="field"><label>거주 지역</label><input id="area" placeholder="예: 대전 OO구"></div><div class="field"><label>특이사항</label><input id="memo" placeholder="생활 지원 참고사항"></div></div>
<p><button onclick="add()">어르신 등록</button> <button class="alt" onclick="clearForm()">초기화</button></p></section>
<section class="panel"><h2>등록된 어르신</h2><input id="search" placeholder="이름 또는 담당자 검색" oninput="render()" style="max-width:320px;margin-bottom:12px">
<table><thead><tr><th>성명</th><th>연락처</th><th>담당자</th><th>통화 시간</th><th>관리</th></tr></thead><tbody id="rows"></tbody></table></section>
<p class="note">※ 입력 정보는 현재 브라우저에서만 임시 관리되며 서버에는 저장되지 않습니다.</p></main><script>
let people=[{name:'김OO',phone:'010-1234-0001',worker:'이생활지원사',time:'09:00'},{name:'박OO',phone:'010-1234-0002',worker:'최생활지원사',time:'10:00'}];
const v=id=>document.getElementById(id).value.trim();
function clearForm(){['name','phone','worker','area','memo'].forEach(id=>document.getElementById(id).value='');document.getElementById('time').value='09:00'}
function add(){let p={name:v('name'),phone:v('phone'),worker:v('worker'),time:v('time')};if(!p.name||!p.phone){alert('성명과 연락처를 입력해 주세요.');return}people.push(p);clearForm();render()}
function edit(i){let p=people[i];['name','phone','worker','time'].forEach(k=>document.getElementById(k).value=p[k]);people.splice(i,1);render()}
function del(i){if(confirm('삭제할까요?')){people.splice(i,1);render()}}
function render(){let q=v('search').toLowerCase();document.getElementById('rows').innerHTML=people.map((p,i)=>({p,i})).filter(x=>(x.p.name+x.p.worker).toLowerCase().includes(q)).map(x=>`<tr><td>${x.p.name}</td><td>${x.p.phone}</td><td>${x.p.worker}</td><td>${x.p.time}</td><td><button class="alt" onclick="edit(${x.i})">수정</button> <button class="del" onclick="del(${x.i})">삭제</button></td></tr>`).join('')}
render();</script></body></html>


[03_통화_기록.html](https://github.com/user-attachments/files/34558730/03_._.html)
<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>통화 기록 - CARE SIGNAL</title><style>
*{box-sizing:border-box}body{margin:0;background:#f4f7fb;color:#263449;font-family:Arial,'Malgun Gothic',sans-serif}
header{background:white;padding:22px 5%;border-bottom:1px solid #e5eaf2;font-size:21px;font-weight:800;color:#172b4d}
header span{color:#4776e6}main{max-width:1100px;margin:32px auto;padding:0 20px}
small,.muted{color:#718096}.eyebrow{color:#4776e6;font-size:12px;font-weight:bold;letter-spacing:1px}
h1{margin:8px 0;font-size:29px}h2{font-size:18px;margin:0 0 15px}
.panel,.stat{background:white;border:1px solid #e5eaf2;border-radius:15px;padding:21px;margin-bottom:16px}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:13px}.two{display:grid;grid-template-columns:1fr 1fr;gap:15px}
.num{font-size:29px;font-weight:800;color:#172b4d;margin-top:8px}
table{width:100%;border-collapse:collapse;font-size:14px}th,td{text-align:left;padding:12px 9px;border-bottom:1px solid #e5eaf2}th{color:#718096;background:#fafbfd}
input,select,textarea{padding:11px;border:1px solid #d9e1ec;border-radius:8px;font:inherit;width:100%;background:white}
button{padding:10px 14px;border:0;border-radius:8px;background:#4776e6;color:white;font-weight:bold;cursor:pointer}
button.alt{background:#edf2ff;color:#3459b5}button.del{background:#fff0ef;color:#c44}
.tag{display:inline-block;border-radius:20px;padding:5px 9px;background:#e9f8f1;color:#26966f;font-size:12px;font-weight:bold}
.tag.warn{background:#fff7e5;color:#a87512}.tag.red{background:#fff0ef;color:#d9534f}
.formgrid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.field label{display:block;font-size:12px;color:#718096;margin-bottom:5px}
.note{font-size:12px;color:#718096;line-height:1.6}
@media(max-width:700px){.grid,.two,.formgrid{grid-template-columns:1fr 1fr}}@media(max-width:480px){.grid,.two,.formgrid{grid-template-columns:1fr}}
</style></head><body><header>CARE <span>SIGNAL</span></header><main><div class="eyebrow">03 / CARE MANAGEMENT</div><h1>통화 기록</h1><p class="muted">AI 안부 확인 결과를 바탕으로 생활지원사의 돌봄 업무를 돕는 화면입니다.</p>
<section class="panel"><h2>통화 기록 조회</h2><div class="two" style="margin-bottom:12px"><input id="q" placeholder="이름 또는 통화 내용 검색" oninput="render()"><select id="f" onchange="render()"><option>전체</option><option>완료</option><option>미응답</option><option>재확인</option></select></div>
<table><thead><tr><th>날짜·시간</th><th>어르신</th><th>결과</th><th>통화 요약</th><th>상세</th></tr></thead><tbody id="rows"></tbody></table><div id="detail" class="panel" style="display:none;margin-top:16px"></div></section>
<p class="note">※ 통화 내역은 기능 시연용 가상 데이터입니다.</p></main><script>
const calls=[['11/09 09:10','최OO','완료','아침 식사를 했고 수면 상태는 양호하다고 응답했습니다.'],['11/09 09:05','박OO','완료','어젯밤 잠을 설쳤고 아침 식사는 아직이라고 응답했습니다.'],['11/09 08:50','김OO','미응답','전화를 받지 않았습니다.'],['11/08 09:00','이OO','재확인','평소보다 대답이 짧아 확인이 필요합니다.']];
function render(){let q=document.getElementById('q').value.toLowerCase(),f=document.getElementById('f').value;document.getElementById('rows').innerHTML=calls.map((c,i)=>({c,i})).filter(x=>(f==='전체'||x.c[2]===f)&&x.c.join(' ').toLowerCase().includes(q)).map(x=>`<tr><td>${x.c[0]}</td><td>${x.c[1]}</td><td>${x.c[2]}</td><td>${x.c[3]}</td><td><button class="alt" onclick="detail(${x.i})">상세 보기</button></td></tr>`).join('')}
function detail(i){let c=calls[i],d=document.getElementById('detail');d.style.display='block';d.innerHTML=`<h2>${c[1]} · ${c[0]}</h2><p>통화 결과: ${c[2]}</p><p>AI 요약: ${c[3]}</p><p>후속 조치: ${c[2]==='완료'?'정기 모니터링':'담당 생활지원사 확인 권고'}</p>`}
render();</script></body></html>



[04_방문_우선순위.html](https://github.com/user-attachments/files/34558735/04_._.html)<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>방문 우선순위 - CARE SIGNAL</title><style>
*{box-sizing:border-box}body{margin:0;background:#f4f7fb;color:#263449;font-family:Arial,'Malgun Gothic',sans-serif}
header{background:white;padding:22px 5%;border-bottom:1px solid #e5eaf2;font-size:21px;font-weight:800;color:#172b4d}
header span{color:#4776e6}main{max-width:1100px;margin:32px auto;padding:0 20px}
small,.muted{color:#718096}.eyebrow{color:#4776e6;font-size:12px;font-weight:bold;letter-spacing:1px}
h1{margin:8px 0;font-size:29px}h2{font-size:18px;margin:0 0 15px}
.panel,.stat{background:white;border:1px solid #e5eaf2;border-radius:15px;padding:21px;margin-bottom:16px}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:13px}.two{display:grid;grid-template-columns:1fr 1fr;gap:15px}
.num{font-size:29px;font-weight:800;color:#172b4d;margin-top:8px}
table{width:100%;border-collapse:collapse;font-size:14px}th,td{text-align:left;padding:12px 9px;border-bottom:1px solid #e5eaf2}th{color:#718096;background:#fafbfd}
input,select,textarea{padding:11px;border:1px solid #d9e1ec;border-radius:8px;font:inherit;width:100%;background:white}
button{padding:10px 14px;border:0;border-radius:8px;background:#4776e6;color:white;font-weight:bold;cursor:pointer}
button.alt{background:#edf2ff;color:#3459b5}button.del{background:#fff0ef;color:#c44}
.tag{display:inline-block;border-radius:20px;padding:5px 9px;background:#e9f8f1;color:#26966f;font-size:12px;font-weight:bold}
.tag.warn{background:#fff7e5;color:#a87512}.tag.red{background:#fff0ef;color:#d9534f}
.formgrid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.field label{display:block;font-size:12px;color:#718096;margin-bottom:5px}
.note{font-size:12px;color:#718096;line-height:1.6}
@media(max-width:700px){.grid,.two,.formgrid{grid-template-columns:1fr 1fr}}@media(max-width:480px){.grid,.two,.formgrid{grid-template-columns:1fr}}
</style></head><body><header>CARE <span>SIGNAL</span></header><main><div class="eyebrow">04 / CARE MANAGEMENT</div><h1>방문 우선순위</h1><p class="muted">AI 안부 확인 결과를 바탕으로 생활지원사의 돌봄 업무를 돕는 화면입니다.</p>
<section class="panel"><h2>오늘 방문 우선순위</h2><p class="muted">통화 결과와 생활 변화 신호를 참고해 확인이 필요한 순서를 제안합니다.</p>
<table><tr><th>순위</th><th>어르신</th><th>점수</th><th>상태</th><th>확인 사유</th><th>권고 조치</th></tr>
<tr><td>1</td><td>김OO</td><td>92점</td><td><span class="tag red">긴급 확인</span></td><td>2회 연속 통화 미응답</td><td>재통화 및 담당자 확인</td></tr>
<tr><td>2</td><td>박OO</td><td>76점</td><td><span class="tag warn">주의</span></td><td>식사 응답 변화</td><td>당일 식사 여부 확인</td></tr>
<tr><td>3</td><td>이OO</td><td>64점</td><td><span class="tag warn">주의</span></td><td>수면 불편 반복 언급</td><td>통화 내용 확인 후 방문 검토</td></tr>
<tr><td>4</td><td>최OO</td><td>18점</td><td><span class="tag">안정</span></td><td>평소와 유사한 응답</td><td>정기 확인 유지</td></tr></table></section>
<section class="panel"><h2>판단 시 유의사항</h2><ul><li>점수는 시연용 예시이며 실제 위험도 판정값이 아닙니다.</li><li>미응답 1회만으로 긴급 상황이라고 단정하지 않습니다.</li><li>AI는 확인 순서를 제안하고 최종 판단은 생활지원사가 합니다.</li></ul></section></main><script></script></body></html>



[05_통화_상세.html](https://github.com/user-attachments/files/34558741/05_._.html)<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>통화 상세 - CARE SIGNAL</title><style>
*{box-sizing:border-box}body{margin:0;background:#f4f7fb;color:#263449;font-family:Arial,'Malgun Gothic',sans-serif}
header{background:white;padding:22px 5%;border-bottom:1px solid #e5eaf2;font-size:21px;font-weight:800;color:#172b4d}
header span{color:#4776e6}main{max-width:1100px;margin:32px auto;padding:0 20px}
small,.muted{color:#718096}.eyebrow{color:#4776e6;font-size:12px;font-weight:bold;letter-spacing:1px}
h1{margin:8px 0;font-size:29px}h2{font-size:18px;margin:0 0 15px}
.panel,.stat{background:white;border:1px solid #e5eaf2;border-radius:15px;padding:21px;margin-bottom:16px}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:13px}.two{display:grid;grid-template-columns:1fr 1fr;gap:15px}
.num{font-size:29px;font-weight:800;color:#172b4d;margin-top:8px}
table{width:100%;border-collapse:collapse;font-size:14px}th,td{text-align:left;padding:12px 9px;border-bottom:1px solid #e5eaf2}th{color:#718096;background:#fafbfd}
input,select,textarea{padding:11px;border:1px solid #d9e1ec;border-radius:8px;font:inherit;width:100%;background:white}
button{padding:10px 14px;border:0;border-radius:8px;background:#4776e6;color:white;font-weight:bold;cursor:pointer}
button.alt{background:#edf2ff;color:#3459b5}button.del{background:#fff0ef;color:#c44}
.tag{display:inline-block;border-radius:20px;padding:5px 9px;background:#e9f8f1;color:#26966f;font-size:12px;font-weight:bold}
.tag.warn{background:#fff7e5;color:#a87512}.tag.red{background:#fff0ef;color:#d9534f}
.formgrid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.field label{display:block;font-size:12px;color:#718096;margin-bottom:5px}
.note{font-size:12px;color:#718096;line-height:1.6}
@media(max-width:700px){.grid,.two,.formgrid{grid-template-columns:1fr 1fr}}@media(max-width:480px){.grid,.two,.formgrid{grid-template-columns:1fr}}
</style></head><body><header>CARE <span>SIGNAL</span></header><main><div class="eyebrow">05 / CARE MANAGEMENT</div><h1>통화 상세</h1><p class="muted">AI 안부 확인 결과를 바탕으로 생활지원사의 돌봄 업무를 돕는 화면입니다.</p>
<section class="panel"><div class="two"><div><h2 style="font-size:24px">박OO 어르신</h2><p class="muted">2026년 11월 9일 오전 09:05 · 통화 2분 18초</p></div><div style="text-align:right"><span class="tag warn">주의 · 담당자 확인 권고</span></div></div>
<div class="grid"><div class="stat"><small>식사</small><div class="num" style="font-size:20px">아직 전</div></div><div class="stat"><small>수면</small><div class="num" style="font-size:20px">불편</div></div><div class="stat"><small>통증</small><div class="num" style="font-size:20px">언급 없음</div></div><div class="stat"><small>통화 결과</small><div class="num" style="font-size:20px">완료</div></div></div></section>
<div class="two"><section class="panel"><h2>AI 통화 요약</h2><p>어르신은 어젯밤 잠을 설쳤다고 이야기했습니다. 통화 시점에는 아침 식사를 아직 하지 않았다고 응답했습니다. 통증이나 별도의 불편 사항은 언급하지 않았습니다.</p><p class="note">AI 요약은 대화 내용을 정리한 참고 정보이며 사실 확인이 필요합니다.</p></section>
<section class="panel"><h2>담당자 확인 사항</h2><label><input type="checkbox" style="width:auto"> 식사 여부 재확인</label><p><label><input type="checkbox" style="width:auto"> 수면 상태 확인</label></p><p><label><input type="checkbox" style="width:auto"> 방문 필요 여부 검토</label></p><textarea rows="3" placeholder="확인 내용 또는 후속 조치 기록"></textarea><p><button onclick="alert('데모 화면에서는 서버에 저장되지 않습니다.')">확인 내용 저장</button></p></section></div>
<section class="panel"><h2>최근 7일 생활 기록</h2><table><tr><th>날짜</th><th>식사</th><th>수면</th><th>특이사항</th></tr>
<tr><td>11/09</td><td>아직 전</td><td>불편</td><td>수면 불편 언급</td></tr><tr><td>11/08</td><td>완료</td><td>보통</td><td>특이사항 없음</td></tr><tr><td>11/07</td><td>완료</td><td>양호</td><td>특이사항 없음</td></tr><tr><td>11/06</td><td>확인 필요</td><td>보통</td><td>식사 응답 누락</td></tr><tr><td>11/05</td><td>완료</td><td>양호</td><td>특이사항 없음</td></tr><tr><td>11/04</td><td>완료</td><td>보통</td><td>특이사항 없음</td></tr><tr><td>11/03</td><td>완료</td><td>양호</td><td>특이사항 없음</td></tr></table></section>
<p class="note">※ 모든 어르신 정보와 통화 내용은 가상 예시입니다.</p></main><script></script></body></html>

