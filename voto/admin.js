// Painel administrativo — leitura dos apoios (exige login do Supabase Auth).

import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/+esm';
import { SUPABASE_URL, SUPABASE_ANON_KEY } from './config.js';

const isConfigured =
  typeof SUPABASE_URL === 'string' &&
  SUPABASE_URL.startsWith('http') &&
  !SUPABASE_URL.includes('COLE_AQUI') &&
  !SUPABASE_ANON_KEY.includes('COLE_AQUI');

const supabase = isConfigured ? createClient(SUPABASE_URL, SUPABASE_ANON_KEY) : null;

// Pré-visualização do painel antes de configurar o Supabase: admin.html?demo=1
// Fica desligada automaticamente depois que config.js estiver preenchido.
const isDemo = !isConfigured && new URLSearchParams(location.search).has('demo');

const $ = (selector) => document.querySelector(selector);
const TZ = 'America/Sao_Paulo';

const dayKeyFormatter = new Intl.DateTimeFormat('en-CA', {
  timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit'
});
const dayLabelFormatter = new Intl.DateTimeFormat('pt-BR', {
  timeZone: TZ, day: '2-digit', month: '2-digit'
});
const stampFormatter = new Intl.DateTimeFormat('pt-BR', {
  timeZone: TZ, day: '2-digit', month: '2-digit', year: 'numeric',
  hour: '2-digit', minute: '2-digit'
});

const dayKey = (date) => dayKeyFormatter.format(date);

function setStatus(target, message, state = '') {
  const el = $(target);
  el.textContent = message;
  el.className = `status${state ? ` is-${state}` : ''}`;
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (ch) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]
  ));
}

function renderBars(target, items, { fillClass = '', empty = 'Nenhum apoio ainda.' } = {}) {
  const list = $(target);

  if (!items.length) {
    list.innerHTML = `<li class="muted">${empty}</li>`;
    return;
  }

  const max = Math.max(...items.map((item) => item.value), 1);

  list.innerHTML = items.map((item) => `
    <li>
      <span class="bar-label">${escapeHtml(item.label)}</span>
      <span class="bar-value">${item.value}</span>
      <span class="bar-track">
        <span class="bar-fill ${fillClass}" style="width:${Math.max((item.value / max) * 100, item.value ? 4 : 0)}%"></span>
      </span>
    </li>`).join('');
}

/* ---------------- carregamento ---------------- */

// Amostra usada apenas na pré-visualização (?demo=1).
function demoRows() {
  const origins = [null, null, null, 'whatsapp', 'whatsapp', 'amigo', 'grupo-maua'];
  return Array.from({ length: 96 }, (_, i) => ({
    id: `demo-${i}`,
    choice: 'sim',
    referrer: origins[i % origins.length],
    created_at: new Date(Date.now() - Math.floor(i / 7) * 86400000 - i * 900000).toISOString()
  }));
}

async function fetchRows() {
  if (isDemo) return demoRows();

  const { data, error } = await supabase
    .from('responses')
    .select('id,choice,referrer,created_at')
    .order('created_at', { ascending: false })
    .limit(10000);

  if (error) throw error;
  return data ?? [];
}

async function fetchContatos() {
  if (isDemo) {
    return [
      { id: 'd1', telefone: '+5511988887777', bairro: 'Jardim Zaíra', cidade: 'Mauá', referrer: 'amigo', created_at: new Date(Date.now() - 3.6e6).toISOString() },
      { id: 'd2', telefone: null, bairro: 'Vila Magini', cidade: 'Mauá', referrer: null, created_at: new Date(Date.now() - 9e6).toISOString() },
      { id: 'd3', telefone: '+5511966665555', bairro: 'Jardim Zaíra', cidade: 'Mauá', referrer: 'whatsapp', created_at: new Date(Date.now() - 9e7).toISOString() }
    ];
  }

  const { data, error } = await supabase
    .from('contatos')
    .select('id,telefone,bairro,cidade,referrer,created_at')
    .order('created_at', { ascending: false })
    .limit(5000);

  if (error) throw error;
  return data ?? [];
}

// +5511988887777 -> (11) 98888-7777
function formatPhone(raw) {
  const d = String(raw || '').replace(/\D/g, '').replace(/^55/, '');
  if (d.length === 11) return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
  if (d.length === 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`;
  return raw;
}

async function loadDashboard() {
  setStatus('#dash-status', 'Atualizando...');

  const [rows, contatos] = await Promise.all([fetchRows(), fetchContatos()]);
  const today = dayKey(new Date());

  // ---- KPIs ----
  const counts = new Map();
  const sources = new Map();

  for (const row of rows) {
    const date = new Date(row.created_at);
    const key = dayKey(date);
    counts.set(key, (counts.get(key) || 0) + 1);

    const origin = row.referrer || 'direto';
    sources.set(origin, (sources.get(origin) || 0) + 1);
  }

  const weekKeys = new Set(
    Array.from({ length: 7 }, (_, i) => dayKey(new Date(Date.now() - i * 86400000)))
  );

  $('#kpi-total').textContent = rows.length;
  $('#kpi-today').textContent = counts.get(today) || 0;
  $('#kpi-week').textContent = [...weekKeys].reduce((sum, key) => sum + (counts.get(key) || 0), 0);
  $('#kpi-friends').textContent = sources.get('amigo') || 0;
  $('#kpi-phones').textContent = contatos.filter((c) => c.telefone).length;
  $('#kpi-bairros').textContent = contatos.filter((c) => c.bairro).length;

  // ---- Apoios por dia (últimos 14 dias) ----
  const byDay = Array.from({ length: 14 }, (_, i) => {
    const date = new Date(Date.now() - i * 86400000);
    const key = dayKey(date);
    return {
      label: key === today ? `${dayLabelFormatter.format(date)} (hoje)` : dayLabelFormatter.format(date),
      value: counts.get(key) || 0
    };
  }).filter((item, index) => index === 0 || item.value > 0);

  renderBars('#by-day', byDay, { empty: 'Nenhum apoio nos últimos dias.' });

  // ---- Origem dos apoios ----
  const labels = { direto: 'Direto', amigo: 'Amigo', whatsapp: 'WhatsApp' };
  const bySource = [...sources.entries()]
    .sort((a, b) => b[1] - a[1])
    .map(([origin, value]) => ({ label: labels[origin] || origin, value }));

  renderBars('#by-source', bySource, { fillClass: 'navy' });

  // ---- CRM: cidade -> bairro -> pessoas ----
  renderCrm(contatos);

  // ---- Tabela ----
  const latest = rows.slice(0, 300);
  $('#table-count').textContent = rows.length > latest.length
    ? `Mostrando os ${latest.length} mais recentes de ${rows.length}`
    : `${rows.length} registro(s)`;

  $('#rows').innerHTML = latest.map((row) => `
    <tr>
      <td>${stampFormatter.format(new Date(row.created_at))}</td>
      <td>${escapeHtml(labels[row.referrer || 'direto'] || row.referrer)}</td>
      <td>${row.choice === 'sim' ? 'Sim' : escapeHtml(row.choice)}</td>
    </tr>`).join('') || '<tr><td colspan="3">Nenhum apoio ainda.</td></tr>';

  setStatus(
    '#dash-status',
    isDemo
      ? 'Pré-visualização com dados de exemplo. Configure o Supabase em config.js para ver os apoios reais.'
      : `Atualizado às ${new Date().toLocaleTimeString('pt-BR')}.`,
    isDemo ? '' : 'success'
  );
}

/* ---------------- CRM de votos ---------------- */

// Agrupa sem diferenciar maiúsculas/acentos ("jardim zaira" = "Jardim Zaíra").
const chave = (t) => String(t || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();

const SEM_CIDADE = 'sem-cidade';
const SEM_BAIRRO = 'sem-bairro';

const crm = { pessoas: [], cidade: 'todas', bairro: null, busca: '' };

function renderCrm(contatos) {
  crm.pessoas = contatos.map((c) => ({
    cidade: c.cidade || 'Cidade não informada',
    cidadeKey: c.cidade ? chave(c.cidade) : SEM_CIDADE,
    bairro: c.bairro || 'Bairro não informado',
    bairroKey: c.bairro ? chave(c.bairro) : SEM_BAIRRO,
    telefone: c.telefone,
    created_at: c.created_at
  }));

  // Se a cidade escolhida sumiu da base, volta para "Todas".
  if (crm.cidade !== 'todas' && !crm.pessoas.some((p) => p.cidadeKey === crm.cidade)) {
    crm.cidade = 'todas';
    crm.bairro = null;
  }

  const cidades = new Set(crm.pessoas.filter((p) => p.cidadeKey !== SEM_CIDADE).map((p) => p.cidadeKey));
  const bairros = new Set(crm.pessoas.filter((p) => p.bairroKey !== SEM_BAIRRO).map((p) => `${p.cidadeKey}|${p.bairroKey}`));
  $('#crm-resumo').textContent = `${crm.pessoas.length} pessoa(s) · ${cidades.size} cidade(s) · ${bairros.size} bairro(s)`;

  drawCrm();
}

function agrupar(lista, campoKey, campoNome) {
  const mapa = new Map();
  for (const p of lista) {
    const item = mapa.get(p[campoKey]) || { key: p[campoKey], label: p[campoNome], value: 0 };
    item.value += 1;
    mapa.set(p[campoKey], item);
  }
  // "não informado" sempre por último
  return [...mapa.values()].sort((x, y) =>
    (x.key === SEM_CIDADE || x.key === SEM_BAIRRO) - (y.key === SEM_CIDADE || y.key === SEM_BAIRRO) || y.value - x.value
  );
}

function drawCrm() {
  // ---- cidades (chips) ----
  const cidades = agrupar(crm.pessoas, 'cidadeKey', 'cidade');
  const chip = (key, nome, n) => `
    <button class="chip" type="button" role="tab" data-cidade="${escapeHtml(key)}"
            aria-selected="${crm.cidade === key}">
      <strong>${escapeHtml(nome)}</strong><small>${n} voto(s)</small>
    </button>`;

  $('#crm-cidades').innerHTML = crm.pessoas.length
    ? chip('todas', 'Todas', crm.pessoas.length) + cidades.map((c) => chip(c.key, c.label, c.value)).join('')
    : '<p class="muted">Ninguém informou cidade ou bairro ainda.</p>';

  const naCidade = crm.cidade === 'todas' ? crm.pessoas : crm.pessoas.filter((p) => p.cidadeKey === crm.cidade);
  const nomeCidade = crm.cidade === 'todas' ? 'todas as cidades' : (naCidade[0]?.cidade || '');

  // ---- bairros da cidade (clicáveis) ----
  // Em "Todas", o mesmo nome de bairro em cidades diferentes fica separado.
  const comChave = naCidade.map((p) => ({
    ...p,
    bKey: crm.cidade === 'todas' ? `${p.cidadeKey}|${p.bairroKey}` : p.bairroKey,
    bNome: crm.cidade === 'todas' && p.bairroKey !== SEM_BAIRRO ? `${p.bairro} · ${p.cidade}` : p.bairro
  }));
  const bairros = agrupar(comChave, 'bKey', 'bNome');

  $('#crm-bairros-titulo').textContent = `Bairros — ${nomeCidade}`;
  const max = Math.max(1, ...bairros.map((b) => b.value));
  $('#crm-bairros').innerHTML = bairros.map((b) => `
    <li role="button" tabindex="0" data-bairro="${escapeHtml(b.key)}" aria-pressed="${crm.bairro === b.key}">
      <span class="bar-label">${escapeHtml(b.label)}</span>
      <span class="bar-value">${b.value}</span>
      <span class="bar-track"><span class="bar-fill" style="width:${Math.max((b.value / max) * 100, 4)}%"></span></span>
    </li>`).join('') || '<li class="muted">Nenhum bairro informado.</li>';

  // ---- pessoas ----
  const buscaTexto = chave(crm.busca);
  const buscaDigitos = crm.busca.replace(/\D/g, '');
  const pessoas = comChave
    .filter((p) => !crm.bairro || p.bKey === crm.bairro)
    .filter((p) => !buscaTexto
      || chave(p.bairro).includes(buscaTexto)
      || (buscaDigitos.length >= 3 && String(p.telefone || '').includes(buscaDigitos)))
    .sort((x, y) => new Date(y.created_at) - new Date(x.created_at));

  const bairroSel = crm.bairro ? bairros.find((b) => b.key === crm.bairro)?.label : null;
  $('#crm-pessoas-titulo').textContent = `Pessoas — ${bairroSel || nomeCidade} (${pessoas.length})`;

  $('#crm-pessoas').innerHTML = pessoas.map((p) => {
    let fone = '—';
    if (p.telefone) {
      const link = `https://wa.me/${String(p.telefone).replace(/\D/g, '')}`;
      fone = `<a href="${escapeHtml(link)}" target="_blank" rel="noopener noreferrer">${escapeHtml(formatPhone(p.telefone))}</a>`;
    }
    const lugar = crm.cidade === 'todas' ? `${p.bairro} · ${p.cidade}` : p.bairro;
    return `
    <tr>
      <td>${escapeHtml(lugar)}<span class="quando">${stampFormatter.format(new Date(p.created_at))}</span></td>
      <td>${fone}</td>
    </tr>`;
  }).join('') || '<tr><td colspan="2">Ninguém encontrado.</td></tr>';
}

$('#crm-cidades').addEventListener('click', (event) => {
  const botao = event.target.closest('[data-cidade]');
  if (!botao) return;
  crm.cidade = botao.dataset.cidade;
  crm.bairro = null;
  drawCrm();
});

function escolherBairro(alvo) {
  const item = alvo.closest('[data-bairro]');
  if (!item) return;
  crm.bairro = crm.bairro === item.dataset.bairro ? null : item.dataset.bairro;
  drawCrm();
}

$('#crm-bairros').addEventListener('click', (event) => escolherBairro(event.target));
$('#crm-bairros').addEventListener('keydown', (event) => {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault();
    escolherBairro(event.target);
  }
});

$('#crm-busca').addEventListener('input', (event) => {
  crm.busca = event.target.value;
  drawCrm();
});

function showDashboard() {
  $('#login-view').classList.add('hidden');
  $('#dash-view').classList.remove('hidden');
  $('#logout').classList.remove('hidden');
  return loadDashboard();
}

const reportError = (error) => {
  console.error(error);
  setStatus('#dash-status', error?.message || 'Erro ao carregar os apoios.', 'error');
};

/* ---------------- eventos ---------------- */

$('#login-form').addEventListener('submit', async (event) => {
  event.preventDefault();

  if (!isConfigured) {
    setStatus('#login-status', 'Configure SUPABASE_URL e SUPABASE_ANON_KEY em config.js.', 'error');
    return;
  }

  setStatus('#login-status', 'Entrando...');

  const { error } = await supabase.auth.signInWithPassword({
    email: $('#email').value.trim(),
    password: $('#password').value
  });

  if (error) {
    setStatus('#login-status', 'E-mail ou senha inválidos.', 'error');
    return;
  }

  setStatus('#login-status', '');
  showDashboard().catch(reportError);
});

$('#refresh').addEventListener('click', () => loadDashboard().catch(reportError));

$('#logout').addEventListener('click', async () => {
  await supabase?.auth.signOut();
  location.reload();
});

/* ---------------- sessão existente ---------------- */

if (isDemo) {
  showDashboard().catch(reportError);
} else if (isConfigured) {
  const { data } = await supabase.auth.getSession();
  if (data.session) showDashboard().catch(reportError);
} else {
  setStatus('#login-status', 'Configure SUPABASE_URL e SUPABASE_ANON_KEY em config.js.', 'error');
}
