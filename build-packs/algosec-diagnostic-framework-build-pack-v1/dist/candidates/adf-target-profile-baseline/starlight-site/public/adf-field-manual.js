const FIELD_MANUAL_SELECTOR = 'details.adf-preview-manual-step[data-adf-manual-step="true"]';

function resolveFieldManualTarget(hash = window.location.hash) {
  if (!hash || !hash.startsWith('#manual-')) return null;
  const id = decodeURIComponent(hash.slice(1));
  const target = document.getElementById(id);
  if (!target) return null;
  if (target.matches(FIELD_MANUAL_SELECTOR)) return target;
  return target.closest(FIELD_MANUAL_SELECTOR);
}

function openFieldManualTarget(hash = window.location.hash) {
  const details = resolveFieldManualTarget(hash);
  if (details) details.open = true;
}

document.addEventListener('click', (event) => {
  const link = event.target.closest('a[href*="#manual-"]');
  if (!link) return;
  const hash = new URL(link.href, window.location.href).hash;
  window.requestAnimationFrame(() => openFieldManualTarget(hash));
});

window.addEventListener('hashchange', () => {
  window.requestAnimationFrame(() => openFieldManualTarget(window.location.hash));
});

window.addEventListener('DOMContentLoaded', () => {
  window.requestAnimationFrame(() => openFieldManualTarget(window.location.hash));
});
