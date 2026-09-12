// Samuel Enfermeiro 4001 — página pública.
// Registra apoio ("sim") e compartilha o app. Nenhum dado pessoal é coletado.

import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/+esm';
import { SUPABASE_URL, SUPABASE_ANON_KEY, PUBLIC_APP_URL, INSTAGRAM_URL } from './config.js';

const SUPPORT_KEY = 'samuel4001_apoio';   // evita clique duplicado no mesmo navegador
const REF_KEY = 'samuel4001_ref';         // guarda a origem da visita
const PHONE_KEY = 'samuel4001_contato';   // marca que este navegador já deixou o número
const ID_KEY = 'samuel4001_apoio_id';     // liga o número ao apoio da mesma pessoa

const CONSENT_TEXT =
  'Só a equipe da campanha usa para falar com você. Nada de propaganda de terceiros.';

const isConfigured =
  typeof SUPABASE_URL === 'string' &&
  SUPABASE_URL.startsWith('http') &&
  !SUPABASE_URL.includes('COLE_AQUI') &&
  !SUPABASE_ANON_KEY.includes('COLE_AQUI');

const supabase = isConfigured ? createClient(SUPABASE_URL, SUPABASE_ANON_KEY) : null;

const supportBtn = document.querySelector('#support');
const shareBtn = document.querySelector('#share');
const feedback = document.querySelector('#feedback');
const instaLink = document.querySelector('#instagram');
const phoneStep = document.querySelector('#phone-step');
const phoneForm = document.querySelector('#phone-form');
const phoneInput = document.querySelector('#phone');
const phoneButton = phoneForm.querySelector('.btn-send');
const supportLabel = supportBtn.querySelector('.btn-label');

/* ---------------- utilidades ---------------- */

function store(type, key, value) {
  try {
    if (value === undefined) return window[type].getItem(key);
    window[type].setItem(key, value);
  } catch {
    return null; // navegação privada / storage bloqueado
  }
}

function setFeedback(message, state = '') {
  feedback.textContent = message;
  feedback.className = `feedback${state ? ` is-${state}` : ''}`;
}

// Só aceita códigos curtos e simples de origem (ex.: whatsapp, amigo, grupo-maua).
function readReferrer() {
  const fromUrl = new URLSearchParams(location.search).get('ref');
  const clean = (fromUrl || '')
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9_-]/g, '')
    .slice(0, 40);

  if (clean) {
    store('sessionStorage', REF_KEY, clean);
    return clean;
  }
  return store('sessionStorage', REF_KEY) || null;
}

function appUrl() {
  const base = (PUBLIC_APP_URL || '').trim() || `${location.origin}${location.pathname}`;
  return base
    .replace(/[?#].*$/, '')
    .replace(/index\.html$/, ''); // link mais limpo para o WhatsApp
}

function shareUrl() {
  const url = new URL(appUrl(), location.href);
  url.searchParams.set('ref', 'amigo'); // permite medir os acessos vindos de indicação
  return url.toString();
}

function markAsSupported({ animateShare } = {}) {
  supportLabel.textContent = '✓ APOIO REGISTRADO';
  supportBtn.classList.remove('is-loading');
  supportBtn.classList.add('is-done');
  supportBtn.disabled = true;
  supportBtn.setAttribute('aria-disabled', 'true');
  if (animateShare) shareBtn.classList.add('is-next');
}

/* ---------------- registro do apoio ---------------- */

async function registerSupport(referrer) {
  // O id é gerado aqui para ligar o número ao apoio sem precisar ler a base.
  const id = crypto.randomUUID();

  if (!isConfigured) {
    // Modo demonstração: funciona antes de configurar o Supabase.
    return { demo: true, id };
  }

  const { error } = await supabase
    .from('responses')
    .insert({ id, choice: 'sim', referrer });

  if (error) throw error;
  return { demo: false, id };
}

/* ---------------- número de WhatsApp (opcional) ---------------- */

// Guarda só dígitos e mostra (11) 99999-9999 enquanto a pessoa digita.
function formatPhone(value) {
  const d = value.replace(/\D/g, '').slice(0, 11);
  if (d.length <= 2) return d.length ? `(${d}` : '';
  if (d.length <= 6) return `(${d.slice(0, 2)}) ${d.slice(2)}`;
  if (d.length <= 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`;
  return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
}

function showPhoneStep() {
  if (store('localStorage', PHONE_KEY)) return; // este navegador já deixou
  phoneStep.hidden = false;
  // A arte encolhe para o campo caber na mesma tela, sem rolagem.
  document.body.classList.add('is-compact');
}

function closePhoneStep(message) {
  phoneStep.classList.add('is-done');
  phoneStep.innerHTML = `<h2>${message}</h2>`;
}

phoneInput.addEventListener('input', () => {
  phoneInput.value = formatPhone(phoneInput.value);
});

phoneForm.addEventListener('submit', async (event) => {
  event.preventDefault();

  const digits = phoneInput.value.replace(/\D/g, '');

  if (digits.length < 10 || digits.length > 11) {
    setFeedback('Confira o número: é DDD + o número, como (11) 99999-9999.', 'error');
    phoneInput.focus();
    return;
  }

  phoneButton.disabled = true;
  setFeedback('Enviando seu número...');

  const payload = {
    response_id: store('localStorage', ID_KEY) || null,
    telefone: `+55${digits}`,
    consentimento: true,
    texto_consentimento: CONSENT_TEXT,
    referrer: readReferrer()
  };

  try {
    if (isConfigured) {
      const { error } = await supabase.from('contatos').insert(payload);
      // 23505 = número já cadastrado. Para a pessoa, é sucesso do mesmo jeito.
      if (error && error.code !== '23505') throw error;
    }

    store('localStorage', PHONE_KEY, '1');
    closePhoneStep('Número recebido, obrigado! 💙');
    setFeedback('Agora indique para um amigo — é o que mais ajuda a campanha.', 'success');
    shareBtn.classList.add('is-next');
  } catch (error) {
    console.error(error);
    phoneButton.disabled = false;
    setFeedback('Não foi possível enviar agora. Tente novamente em alguns segundos.', 'error');
  }
});

supportBtn.addEventListener('click', async () => {
  if (supportBtn.disabled) return;

  supportBtn.disabled = true;
  supportBtn.classList.add('is-loading');
  setFeedback('Registrando seu apoio...');

  try {
    const { demo, id } = await registerSupport(readReferrer());
    store('localStorage', SUPPORT_KEY, new Date().toISOString());
    store('localStorage', ID_KEY, id);
    markAsSupported({ animateShare: true });
    setFeedback(
      demo
        ? 'Obrigado! Seu apoio foi registrado. (Modo demonstração — configure o Supabase em config.js.)'
        : 'Obrigado! Seu apoio foi registrado.',
      'success'
    );
    showPhoneStep();
  } catch (error) {
    console.error(error);
    supportBtn.disabled = false;
    supportBtn.classList.remove('is-loading');
    setFeedback('Não foi possível registrar agora. Toque novamente em alguns segundos.', 'error');
  }
});

/* ---------------- compartilhamento ---------------- */

function shareText(url) {
  return [
    'Quero te apresentar o Samuel Enfermeiro 💙',
    '',
    'Eu conheço ele e conheço a história dele: é gente como a gente. Agora está candidato a Deputado Federal.',
    '',
    `Dá uma olhada — se eu conheço, quero que você conheça também: ${url}`
  ].join('\n');
}

shareBtn.addEventListener('click', async () => {
  const url = shareUrl();
  const text = shareText(url);

  if (navigator.share) {
    try {
      await navigator.share({ title: 'Samuel Enfermeiro 4001', text });
      return;
    } catch (error) {
      if (error?.name === 'AbortError') return; // a pessoa fechou o menu
    }
  }

  window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank', 'noopener,noreferrer');
});

/* ---------------- estado inicial ---------------- */

readReferrer();

// O link do Instagram só aparece se estiver configurado em config.js.
const instaUrl = (INSTAGRAM_URL || '').trim();
if (instaUrl) {
  instaLink.href = instaUrl;
  instaLink.hidden = false;
} else {
  instaLink.remove();
}

if (store('localStorage', SUPPORT_KEY)) {
  markAsSupported();
  setFeedback('Seu apoio já está registrado. Agora indique para um amigo.', 'success');
  showPhoneStep();
} else {
  phoneStep.hidden = true;
}
