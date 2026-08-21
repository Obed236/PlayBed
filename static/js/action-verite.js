(() => {
  const countSelect = document.querySelector('[data-player-count]');
  const rows = [...document.querySelectorAll('[data-player-row]')];
  const syncRows = () => {
    const count = Number(countSelect?.value || 2);
    rows.forEach((row, index) => {
      const active = index < count;
      row.hidden = !active;
      row.querySelectorAll('input').forEach((input) => { input.required = active; });
    });
  };
  countSelect?.addEventListener('change', syncRows);
  syncRows();

  const codeInput = document.getElementById('roomCode');
  codeInput?.addEventListener('input', () => {
    codeInput.value = codeInput.value.replace(/\D/g, '').slice(0, 4);
  });

  document.addEventListener('click', async (event) => {
    const button = event.target.closest('[data-copy-code]');
    if (!button) return;
    const code = button.dataset.copyCode;
    try {
      await navigator.clipboard.writeText(code);
      const previous = button.textContent;
      button.textContent = `${code} ✓`;
      setTimeout(() => { button.textContent = previous; }, 1500);
    } catch {
      // Le code reste visible pour une copie manuelle.
    }
  });

  const room = document.querySelector('[data-av-room]');
  if (!room) return;
  const stateUrl = room.dataset.stateUrl;
  let version = room.dataset.roomVersion;
  let polling = false;

  const poll = async () => {
    if (polling || document.hidden) return;
    polling = true;
    try {
      const response = await fetch(stateUrl, { headers: { 'Accept': 'application/json' }, cache: 'no-store' });
      if (response.status === 404) {
        window.location.href = '/action-verite';
        return;
      }
      if (!response.ok) return;
      const data = await response.json();
      if (data.updated_at && data.updated_at !== version) {
        version = data.updated_at;
        window.location.reload();
      }
    } catch {
      // Une coupure réseau temporaire ne doit pas interrompre la partie.
    } finally {
      polling = false;
    }
  };

  setInterval(poll, 2000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) poll(); });
})();
