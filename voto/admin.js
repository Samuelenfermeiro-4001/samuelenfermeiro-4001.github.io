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

  // ---- Votos por bairro e por cidade ----
  // Agrupa sem diferenciar maiúsculas/acentos ("jardim zaira" = "Jardim Zaíra").
  const chave = (t) => String(t || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
  const porBairro = new Map();
  const porCidade = new Map();

  for (const c of contatos) {
    if (c.bairro) {
      const k = `${chave(c.bairro)}|${chave(c.cidade)}`;
      const atual = porBairro.get(k) || { label: c.cidade ? `${c.bairro} · ${c.cidade}` : c.bairro, value: 0 };
      atual.value += 1;
      porBairro.set(k, atual);
    }
    if (c.cidade) {
      const k = chave(c.cidade);
      const atual = porCidade.get(k) || { label: c.cidade, value: 0 };
      atual.value += 1;
      porCidade.set(k, atual);
    }
  }

  const ordena = (m) => [...m.values()].sort((x, y) => y.value - x.value);
  renderBars('#by-bairro', ordena(porBairro).slice(0, 15), { empty: 'Ninguém informou o bairro ainda.' });
  renderBars('#by-cidade', ordena(porCidade).slice(0, 10), { fillClass: 'navy', empty: 'Ninguém informou a cidade ainda.' });

  // ---- Números e bairros deixados ----
  $('#phones-count').textContent = contatos.length ? `${contatos.length} registro(s)` : '';

  $('#phone-rows').innerHTML = contatos.map((c) => {
    let fone = '—';
    if (c.telefone) {
      const link = `https://wa.me/${String(c.telefone).replace(/\D/g, '')}`;
      fone = `<a href="${escapeHtml(link)}" target="_blank" rel="noopener noreferrer">${escapeHtml(formatPhone(c.telefone))}</a>`;
    }
    return `
    <tr>
      <td>${stampFormatter.format(new Date(c.created_at))}</td>
      <td>${escapeHtml(c.bairro || '—')}</td>
      <td>${escapeHtml(c.cidade || '—')}</td>
      <td>${fone}</td>
      <td>${escapeHtml(labels[c.referrer || 'direto'] || c.referrer)}</td>
    </tr>`;
  }).join('') || '<tr><td colspan="5">Ninguém deixou bairro ou número ainda.</td></tr>';

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
