// Samuel Enfermeiro 4001 — página pública.
// Registra apoio ("sim") e compartilha o app. Nenhum dado pessoal é coletado.

import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/+esm';
import { SUPABASE_URL, SUPABASE_ANON_KEY, PUBLIC_APP_URL, INSTAGRAM_URL } from './config.js';

const SUPPORT_KEY = 'samuel4001_apoio';   // evita clique duplicado no mesmo navegador
const REF_KEY = 'samuel4001_ref';         // guarda a origem da visita

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
  if (!isConfigured) {
    // Modo demonstração: funciona antes de configurar o Supabase.
    return { demo: true };
  }

  const { error } = await supabase
    .from('responses')
    .insert({ choice: 'sim', referrer });

  if (error) throw error;
  return { demo: false };
}

supportBtn.addEventListener('click', async () => {
  if (supportBtn.disabled) return;

  supportBtn.disabled = true;
  supportBtn.classList.add('is-loading');
  setFeedback('Registrando seu apoio...');

  try {
    const { demo } = await registerSupport(readReferrer());
    store('localStorage', SUPPORT_KEY, new Date().toISOString());
    markAsSupported({ animateShare: true });
    setFeedback(
      demo
        ? 'Obrigado! Seu apoio foi registrado. (Modo demonstração — configure o Supabase em config.js.)'
        : 'Obrigado! Seu apoio foi registrado.',
      'success'
    );
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
}
