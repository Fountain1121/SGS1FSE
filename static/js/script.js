// script.js
(function () {
  // small debounce util
  function debounce(fn, wait) {
    let t;
    return function () {
      const ctx = this, args = arguments;
      clearTimeout(t);
      t = setTimeout(() => fn.apply(ctx, args), wait);
    };
  }

  async function saveToServer(section, qid, answer) {
    try {
      const res = await fetch('/save_answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ section, question_id: Number(qid), answer })
      });
      const data = await res.json();
      if (data.status === 'ok') {
        setSaveStatus(`Saved ${new Date(data.saved_at).toLocaleTimeString()}`);
      } else {
        setSaveStatus('Save failed (server).', true);
      }
    } catch (err) {
      console.warn("Server save failed:", err);
      setSaveStatus('Offline. Saved locally.', true);
      // localStorage fallback is used below
    }
  }

  function setSaveStatus(msg, isError) {
    const el = document.getElementById('save-status');
    if (!el) return;
    el.textContent = msg;
    el.style.color = isError ? '#b91c1c' : '#374151';
  }

  // SECTION A: radio autosave
  document.querySelectorAll('.question-block').forEach(block => {
    const qid = block.dataset.qid;
    // radios
    block.querySelectorAll('input[type=radio]').forEach(r => {
      r.addEventListener('change', function () {
        const ans = this.value;
        // save to server, and localStorage fallback
        saveToServer('A', qid, ans);
        try {
          localStorage.setItem(`exam::${CURRENT_STUDENT}::A::${qid}`, ans);
        } catch (e) { /* ignore */ }
      });
    });
  });

  // SECTION B: textarea autosave with debounce
  document.querySelectorAll('textarea').forEach(area => {
    const parent = area.closest('.question-block');
    if (!parent) return;
    const qid = parent.dataset.qid;
    const debounced = debounce(function () {
      const val = area.value;
      saveToServer('B', qid, val);
      try {
        localStorage.setItem(`exam::${CURRENT_STUDENT}::B::${qid}`, val);
      } catch (e) { /* ignore */ }
    }, 800);
    area.addEventListener('input', debounced);
  });

  // On load: restore from localStorage if server-saved wasn't loaded (the templates render server-saved)
  window.addEventListener('load', () => {
    document.querySelectorAll('.question-block').forEach(block => {
      const qid = block.dataset.qid;
      const section = block.closest('form') && block.closest('form').id === 'section-a-form' ? 'A' : 'B';
      try {
        const key = `exam::${CURRENT_STUDENT}::${section}::${qid}`;
        const val = localStorage.getItem(key);
        if (val !== null) {
          if (section === 'A') {
            const radio = block.querySelector(`input[type=radio][value="${val}"]`);
            if (radio) radio.checked = true;
          } else {
            const ta = block.querySelector('textarea');
            if (ta && !ta.value) ta.value = val;
          }
        }
      } catch (e) {
        // ignore localStorage errors
      }
    });
  });

  // optional: warn user before leaving if they haven't submitted
  window.addEventListener('beforeunload', function (e) {
    // You can customize detection of "unsaved" state; currently always warns
    e.preventDefault();
    e.returnValue = '';
  });
})();
