import { PacketAnimation } from './animation.js';

const $ = id => document.getElementById(id);
const make = (tag, cls, text) => {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
};
const set = (id, value) => { $(id).textContent = value; };
const shorten = value => String(value).length > 32 ? `${String(value).slice(0, 20)}…${String(value).slice(-8)}` : String(value);
const packetTypes = { dh: 'DH 공개값', confirm: '키 확인', app: '응용 메시지' };
const animation = new PacketAnimation(document.querySelector('.network-svg'));
const descriptions = {
  normal: '두 프로세스가 같은 사전 공유키로 공개값을 교환합니다.',
  mismatch: 'Bob에게 다른 무작위 키를 주어 실제 GCM 인증 실패를 확인합니다.',
  cipher: 'Eve가 첫 공개값 암호문의 한 비트를 변경합니다.',
  tag: 'Eve가 첫 공개값 패킷 인증 태그의 한 비트를 변경합니다.',
  invalid_public: '테스트 키로 1을 정상 암호화해 보냅니다. GCM 성공 후 DH 검증에서 거부해야 합니다.',
  malformed: 'Eve가 실제 패킷을 잘못된 JSON 스키마로 교체합니다.',
  replay: '정상 실행을 먼저 완료하고, 같은 키·영속 DB로 이전 패킷을 다시 주입합니다.',
  confirm: 'Eve가 Alice의 HMAC 확인값을 변경합니다. 응용 통신 전에 중단해야 합니다.',
  eve: '별도 TCP 중계기가 여섯 패킷을 관찰하고 임의 키로 실제 복호화를 시도합니다.',
  eve_key: 'Eve에게 교육용으로 K_AB를 제공하여 A·B 접근 여부를 비교합니다. a·b·S를 계산하는 기능은 없습니다.',
  drop: 'Eve가 첫 패킷을 전달하지 않고 실제 TCP 연결을 종료합니다.',
  timeout: 'Eve가 첫 패킷 전달을 중단합니다. 수신 프로세스가 제한 시간 안에 종료해야 합니다.'
};
const lessons = [
  { title: '통신 초기화', event: 'connected', formula: 'Alice → TCP → Bob', description: '서로 다른 운영체제 프로세스가 127.0.0.1에서 TCP로 연결합니다. Alice는 새 세션 ID와 난수를 만듭니다.', security: '초기화 정보는 이후 AAD와 transcript에 결합됩니다.' },
  { title: '공개값 암호화·교환', event: 'decrypted', formula: 'A = gᵃ mod p, B = gᵇ mod p\nC = AES-GCM(K_AB, 공개값, AAD)', description: '개인 지수를 전송하지 않고 공개값의 고정 길이 바이트를 암호화합니다. 수신 후 GCM 인증과 DH 공개값 검증을 완료해야 사용할 수 있습니다.', security: '원본 그림의 두 메시지에 해당합니다. 공개값은 수학적으로 공개 가능한 값이고 K_AB는 비밀입니다.' },
  { title: '공유 비밀 계산', event: 'shared', formula: 'S_A = Bᵃ mod p\nS_B = Aᵇ mod p', description: '각 역할이 자신의 개인 지수 하나와 수신·검증한 공개값으로 계산합니다. 상대방 비밀 지수를 읽지 않습니다.', security: '공유 비밀 S를 AES 키로 직접 사용하지 않습니다.' },
  { title: '세션키 유도', event: 'derived', formula: 'S + 양측 난수 + A·B + transcript\n→ HKDF-SHA-256 → 새 키들', description: '두 DH 패킷 전체의 해시, 공개값, 양측 난수를 반영합니다. 세션 루트와 역할별 확인 키, 방향별 응용 키를 구분합니다.', security: 'K_AB는 공개값 보호에 사용한 기존 키이고 새 세션키는 DH 공유 비밀에서 유도합니다.' },
  { title: '상호 키 확인', event: 'key_confirmed', formula: 'HMAC(K_확인, 역할 ∥ 문맥 ∥ transcript)', description: '각 역할 전용 HMAC 키로 확인값을 생성하고 상대의 확인값을 상수 시간 비교로 검증합니다. 양쪽 검증 성공 후 세션을 수립합니다.', security: '원본 그림에 없는 추가 절차입니다. 이 설계를 검증된 표준 인증 키 교환이라고 주장하지 않습니다.' },
  { title: '암호 메시지 왕복', event: 'complete', formula: 'Alice → AES-GCM(K_A→B) → Bob\nBob → AES-GCM(K_B→A) → Alice', description: '방향마다 다른 응용 키와 새 96비트 nonce를 사용합니다. 수신자는 현재 세션·역할·순번을 확인한 뒤 인증 복호화합니다.', security: '이 구현은 세션당 한 메시지와 한 응답을 처리한 뒤 연결을 닫습니다.' }
];
const testLabels = {T01:'DH·HKDF 수학 검증',T02:'AES 암복호화·nonce',T03:'독립 프로세스·TCP',T04:'공유키 불일치',T05:'암호문·AAD 변조',T06:'인증 태그 변조',T07:'DH 공개값 검증',T08:'형식·프레임 제한',T09:'패킷 재전송 거부',T10:'HMAC 키 확인',T11:'응용 메시지 왕복',T12:'연결 오류·타임아웃',T13:'Eve 도청 비교',T14:'웹 API·접근 제한'};
let state = null, events = [], cursor = 0, playing = true, revealed = false, cleared = false;
let currentRun = null, selectedPacket = -1, lesson = 0, manualLesson = false, polling = false, starting = false;
let lastTick = 0, previousTests = '';
let initialSettingsSynced = false;

async function api(path, body) {
  const response = await fetch(path, body === undefined ? {} : { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || '백엔드 요청에 실패했습니다.');
  return data;
}
function error(message = '') {
  set('error', message);
  $('error').classList.toggle('hidden', !message);
}
function showTab(name) {
  for (const button of document.querySelectorAll('[data-tab]')) {
    const active = button.dataset.tab === name;
    button.classList.toggle('active', active);
    button.setAttribute('aria-selected', String(active));
  }
  for (const content of document.querySelectorAll('.tab-content')) content.classList.toggle('hidden', content.id !== `tab-${name}`);
}
for (const button of document.querySelectorAll('[data-tab]')) button.addEventListener('click', () => showTab(button.dataset.tab));

function modeChanged() {
  const small = $('mode').value === 'small';
  set('param-p', small ? '23' : '2048비트 MODP');
  set('param-g', small ? '5' : '2');
  set('param-check', small ? '범위 (학습용 전체 군)' : '범위 + q 부분군');
  set('mode-notice', small ? '수학 학습 전용 · a=6, b=15. 작은 수는 쉽게 역산할 수 있으므로 실제 보안에 사용하면 안 됩니다.' : '개인 지수는 안전한 난수로 생성합니다. 큰 수 모드도 교육용 설계입니다.');
  $('mode-notice').classList.toggle('warning', small);
}
$('mode').addEventListener('change', modeChanged);
$('scenario').addEventListener('change', () => set('scenario-help', descriptions[$('scenario').value]));
const scenarioNames = Object.fromEntries([...$('scenario').options].map(o => [o.value, o.textContent]));
Object.entries(descriptions).forEach(([key, description], index) => {
  const card = make('article', 'attack-card');
  card.append(make('span', 'attack-number', `${String(index + 1).padStart(2,'0')} / ${['normal','eve','eve_key'].includes(key) ? '관찰' : '거부 실험'}`), make('h3', '', scenarioNames[key]), make('p', '', description));
  const button = make('button', 'button compact', '이 실험 실행 ↗');
  button.addEventListener('click', () => { $('scenario').value = key; set('scenario-help', description); startRun(); });
  card.append(button); $('attack-grid').append(card);
});
lessons.forEach((item, index) => {
  const button = make('button', 'stage-button');
  button.append(make('span', '', String(index + 1).padStart(2,'0')), document.createTextNode(item.title));
  button.addEventListener('click', () => { lesson = index; manualLesson = true; renderLesson(); });
  $('stage-buttons').append(button);
});

function resetView() {
  events = []; cursor = 0; selectedPacket = -1; lesson = 0; revealed = false; manualLesson = false;
  animation.stop();
  set('reveal', '작은 수 계산값 공개');
  renderRecords();
}
async function startRun() {
  if (starting || state?.running || state?.testing) return;
  error(); starting = true; $('start').disabled = true;
  try {
    const result = await api('/api/runs', {mode:$('mode').value, scenario:$('scenario').value, message:$('message').value});
    resetView(); currentRun = result.run_id; cleared = false; playing = true; state = null;
    showTab('experiment');
    await poll();
  } catch (err) { error(err.message); }
  finally { starting = false; updateButtons(); }
}
$('start').addEventListener('click', startRun);
$('clear').addEventListener('click', () => {
  if (state?.running || state?.testing) return;
  cleared = true; currentRun = null; resetView(); state = null; renderResult();
  set('backend-status','화면 초기화 · 새 실행 준비');
  set('process-fact','Alice · Bob 독립 실행'); set('run-label','실행 대기'); updateButtons();
});
$('previous').addEventListener('click', () => { playing = false; animation.stop(); cursor = Math.max(0, cursor - 1); renderRecords(); });
$('next').addEventListener('click', () => { playing = false; animation.stop(); advanceRecord(); });
$('play').addEventListener('click', () => {
  if (cursor === events.length && !state?.running && events.length) { animation.stop(); cursor = 0; playing = true; }
  else playing = !playing;
  if (!playing) animation.stop(); renderRecords();
});
$('reveal').addEventListener('click', () => {
  revealed = !revealed; set('reveal', revealed ? '작은 수 계산값 가리기' : '작은 수 계산값 공개'); renderRecords();
});
function advanceRecord() {
  if (cursor >= events.length) return;
  const event = events[cursor++];
  if (event.event === 'sending') {
    const type = event.data.packet.header.type;
    animation.transfer(event.actor, packetTypes[type], Number($('speed').value));
  }
  if (!manualLesson) {
    const index = lessons.findIndex(item => item.event === event.event);
    if (index >= 0) lesson = Math.max(lesson, index);
  }
  renderRecords();
}
setInterval(() => {
  const now = performance.now();
  if (playing && cursor < events.length && now - lastTick > 600 / Number($('speed').value)) {
    lastTick = now; advanceRecord();
  }
}, 60);

function renderRecords() {
  const visible = events.slice(0, cursor);
  for (const role of ['Alice','Bob']) {
    const prefix = role.toLowerCase();
    const own = visible.filter(e => e.actor === role);
    const last = name => own.findLast(e => e.event === name);
    const priv = last('private'), pub = last('public'), peer = last('decrypted'), shared = last('shared');
    const ready = last('established'), failed = last('failed');
    set(`${prefix}-pid`, own.length ? `· ${own[0].pid}` : '');
    set(`${prefix}-private`, priv ? (revealed && priv.data.value != null ? priv.data.value : `비공개 · ${priv.data.bits}비트`) : '••••••');
    for (const [name, event] of [['public',pub],['peer',peer]]) {
      const element = $(`${prefix}-${name}`);
      element.textContent = event ? shorten(event.data.value) : name === 'public' ? '계산 전' : '수신 전';
      element.title = event ? String(event.data.value) : '';
    }
    set(`${prefix}-shared`, shared ? revealed && shared.data.value != null ? String(shared.data.value) : '계산 완료 · 비공개' : '계산 전');
    set(`${prefix}-key`, ready ? '상호 확인 완료 · 비공개' : failed ? '수립 중단' : last('derived') ? '유도 완료 · 확인 대기' : '미수립');
    set(`${prefix}-status`, failed ? `거부 · ${failed.data.code}` : ready ? '세션 수립' : own.length ? '실행 중' : '대기 중');
    $(`${prefix}-status`).classList.toggle('bad', Boolean(failed));
    set(`${prefix}-operation`, own.at(-1)?.message || '실험을 시작하면 실제 연산 기록이 표시됩니다.');
  }
  const eve = visible.filter(e => e.actor === 'Eve');
  $('eve-status').classList.toggle('hidden', !eve.length);
  const eved = eve.findLast(e => ['eve_blocked','eve_decrypted','modified'].includes(e.event));
  set('eve-result', eved ? eved.event === 'eve_blocked' ? 'GCM 복호화 거부 · K_AB 없음' : eved.event === 'eve_decrypted' ? '키 제공 → 공개값 접근 가능' : '실제 패킷 변경·전달 중단' : '네트워크 관찰 중');
  set('record-count', `기록 ${cursor} / ${events.length}`);
  $('event-progress').max = Math.max(1, events.length); $('event-progress').value = cursor;
  set('play', cursor === events.length && events.length && !state?.running ? '기록 다시 재생' : playing ? '기록 일시정지' : '기록 재생');
  $('previous').disabled = cursor === 0;
  $('next').disabled = cursor >= events.length;
  renderPackets(visible); renderLesson(); renderLogs(visible);
}
function renderPackets(visible) {
  const packets = visible.filter(e => e.event === 'sending' && ['Alice','Bob'].includes(e.actor));
  const latest = packets.at(-1)?.data.packet.header;
  const transferStatus = $('transfer-status');
  if (latest) {
    transferStatus.dataset.sender = latest.sender.toLowerCase();
    transferStatus.textContent = `최근 송신 · ${latest.sender} → ${latest.sender === 'Alice' ? 'Bob' : 'Alice'} · ${packetTypes[latest.type]}`;
  } else {
    delete transferStatus.dataset.sender;
    transferStatus.textContent = '패킷 송신 기록 대기';
  }
  if (selectedPacket < 0 || selectedPacket >= packets.length) selectedPacket = packets.length - 1;
  const container = $('packet-list'); container.replaceChildren();
  packets.forEach((event,index) => {
    const head = event.data.packet.header;
    const chip = make('button',`packet-chip${index === selectedPacket ? ' active' : ''}`,`${index + 1} · ${head.sender} · ${packetTypes[head.type]}`);
    chip.addEventListener('click', () => { selectedPacket = index; renderPackets(visible); });
    container.append(chip);
  });
  const selected = packets[selectedPacket];
  $('packet-json').textContent = selected ? JSON.stringify(selected.data.packet, null, 2) : '실제 송신을 시도한 패킷의 인증 header, nonce, 암호문과 태그를 확인할 수 있습니다.';
  set('packet-type', selected ? `${selected.actor} → ${selected.actor === 'Alice' ? 'Bob' : 'Alice'}` : '패킷 대기');
  $('copy-packet').disabled = !selected;
}
$('copy-packet').addEventListener('click', async () => {
  try { await navigator.clipboard.writeText($('packet-json').textContent); set('copy-packet','복사됨'); setTimeout(() => set('copy-packet','복사'),1200); }
  catch { error('클립보드 접근이 차단되었습니다. 패킷 텍스트를 선택해 복사하세요.'); }
});
function renderLesson() {
  const item = lessons[lesson];
  const visible = events.slice(0,cursor);
  set('lesson-step',`단계 ${String(lesson + 1).padStart(2,'0')}`);
  set('lesson-title',item.title); set('lesson-description',item.description);
  set('lesson-security',item.security); set('lesson-formula',item.formula);
  const event = visible.findLast(e => e.event === item.event && ['Alice','Bob'].includes(e.actor));
  const sensitive = event && ['private','shared'].includes(event.event);
  set('lesson-result', event ? `${event.actor} · ${sensitive && !revealed ? '계산 완료 (값 비공개)' : event.data.formula || event.message}` : '아직 해당 단계의 실제 실행 기록이 없습니다.');
  [...$('stage-buttons').children].forEach((button,index) => {
    button.classList.toggle('active',index === lesson);
    button.classList.toggle('done',visible.some(e => e.event === lessons[index].event));
  });
}
function renderLogs(visible) {
  const container = $('event-log'); container.replaceChildren();
  for (const event of visible.slice(-150)) {
    const row = make('div',`log-entry ${event.actor.toLowerCase()} ${event.level}`);
    row.append(make('time','',new Date(event.time).toLocaleTimeString('ko-KR',{hour12:false})),make('strong','',event.actor),make('p','',event.message));
    container.append(row);
  }
  set('log-count',`${visible.length}개 이벤트`);
  if (playing) container.scrollTop = container.scrollHeight;
}
function result(id, text, kind) { set(id,text); $(id).className = kind || ''; }
function renderResult() {
  const summary = state?.summary;
  result('result-process',summary ? summary.independent_processes ? '분리 확인' : '확인 실패' : '—', summary?.independent_processes ? 'good' : '');
  result('result-key',summary ? summary.key_match ? '상호 확인 성공' : '미수립' : '—',summary?.key_match ? 'good' : '');
  result('result-message',summary ? summary.roundtrip ? '양방향 원문 일치' : '진행 중단' : '—',summary?.roundtrip ? 'good' : '');
  result('result-scenario',summary ? summary.passed ? summary.success ? '정상 완료' : '기대대로 거부' : '검증 실패' : state?.running ? '실제 실행 중' : '실행 대기',summary ? summary.passed ? 'good' : 'bad' : '');
  $('failure-detail').classList.toggle('hidden',!summary?.failures?.length);
  set('failure-detail',summary?.failures?.map(f => `${f.actor} / ${f.code} · ${f.reason}`).join('\n') || '');
  $('failure-detail').classList.toggle('warning',Boolean(summary?.passed));
  const chats = state?.events?.filter(e => e.event === 'app_received') || [];
  $('chat-results').replaceChildren();
  for (const event of chats) {
    const message = make('div',`chat-message ${event.actor.toLowerCase()}`);
    message.append(make('small','',`${event.actor === 'Bob' ? 'Alice → Bob' : 'Bob → Alice'} · 실제 인증 복호화 결과`),make('p','',event.data.text));
    $('chat-results').append(message);
  }
}
function renderTests(tests) {
  const signature = JSON.stringify([tests?.time,state?.testing,state?.test_exit,state?.test_error]);
  if (signature === previousTests) return;
  previousTests = signature;
  const failure = state?.test_error || (state?.test_exit != null && state.test_exit !== 0 ? `검증이 종료 코드 ${state.test_exit}로 끝났습니다.` : '');
  if (state?.testing || state?.test_error) tests = null;
  set('test-total',state?.testing ? '실행 중…' : state?.test_error ? '검증 실행 실패' : tests ? `${tests.passed}개 통과 / ${tests.failed}개 실패` : failure ? '검증 실패' : '미실행');
  set('test-time',state?.testing ? '독립 프로세스와 TCP를 포함한 실제 pytest 검증을 실행하고 있습니다.' : tests ? `${failure ? failure + ' ' : ''}실행 시각 ${new Date(tests.time).toLocaleString('ko-KR')} · 종료 코드 ${tests.exit_code} · Python ${tests.python} · cryptography ${tests.cryptography}` : failure || '테스트를 실행한 경우에만 통과 결과를 표시합니다.');
  $('test-total').classList.toggle('bad', Boolean(failure) && !state?.testing);
  $('test-grid').replaceChildren();
  for (const [id,label] of Object.entries(testLabels)) {
    const rows = tests?.tests?.filter(t => t.code === id) || [];
    const passed = rows.length && rows.every(r => r.outcome === 'passed');
    const failed = rows.some(r => r.outcome === 'failed');
    const node = make('div','test-item');
    node.append(make('span','',id),document.createTextNode(label),make('i',failed ? 'bad' : '',state?.testing ? '…' : passed ? '✓' : failed ? '✕' : '—'));
    node.title = failed ? rows.filter(r => r.outcome === 'failed').map(r => r.reason).join('\n') : `${rows.length}개 실제 검사`;
    $('test-grid').append(node);
  }
}
function updateButtons() {
  const busy = starting || Boolean(state?.running) || Boolean(state?.testing);
  $('start').disabled = busy; $('clear').disabled = busy; $('run-tests').disabled = busy;
  for (const button of document.querySelectorAll('.attack-card button')) button.disabled = busy;
  set('start',state?.running ? '실제 TCP 실행 중…' : '▶ 실험 시작');
  set('run-tests',state?.testing ? '검증 실행 중…' : '전체 검증 실행');
}
async function poll() {
  if (polling) return;
  polling = true;
  try {
    const data = await api('/api/state');
    if (cleared) { state = {...data,summary:null,events:[]}; renderTests(data.tests); updateButtons(); return; }
    if (currentRun !== data.run_id) { resetView(); currentRun = data.run_id; }
    const changed = events.length !== data.events.length;
    state = data; events = data.events;
    const summary = data.summary;
    if (!initialSettingsSynced && summary) {
      $('mode').value = summary.mode; $('scenario').value = summary.scenario; modeChanged();
      set('scenario-help',descriptions[summary.scenario]); initialSettingsSynced = true;
    }
    set('run-label',currentRun ? `${summary?.mode === 'small' ? '작은 수 · ' : ''}${currentRun.slice(0,8)}` : '실행 대기');
    set('backend-status',data.running ? '실제 TCP 실행 중' : data.testing ? '자동화 검증 실행 중' : summary ? summary.success ? '실제 통신 완료' : summary.passed ? '공격·오류 거부 확인' : '실행 오류' : '실행 준비');
    $('backend-status').classList.toggle('error',Boolean(summary && !summary.passed));
    if (summary?.pids) set('process-fact',`Alice ${summary.pids.Alice || '—'} · Bob ${summary.pids.Bob || '—'}`);
    if (changed) renderRecords();
    renderResult(); renderTests(data.tests); updateButtons();
  } catch (err) { error(`실험실 서버에 연결할 수 없습니다. 실행 창을 다시 열어주세요. ${err.message}`); }
  finally { polling = false; }
}
$('run-tests').addEventListener('click',async () => {
  try { error(); await api('/api/tests',{}); await poll(); }
  catch (err) { error(err.message); }
});
$('download').addEventListener('click',async () => {
  if (!currentRun || cleared) { error('먼저 실험을 실행하세요.'); return; }
  try {
    const data = await api(`/api/export?run=${currentRun}`);
    const blob = new Blob([JSON.stringify({summary:data.summary,events:data.events},null,2)],{type:'application/json;charset=utf-8'});
    const url = URL.createObjectURL(blob);
    const link = make('a'); link.href = url; link.download = `DH-실행기록-${currentRun.slice(0,8)}.json`; link.click();
    setTimeout(() => URL.revokeObjectURL(url),1000);
  } catch (err) { error(err.message); }
});
modeChanged(); renderRecords(); renderResult(); renderTests(null); poll();
setInterval(poll,700);
