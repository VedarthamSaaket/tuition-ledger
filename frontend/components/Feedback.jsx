import React, { useEffect, useState } from 'react';

let pushMessage = null;

export function announce(text, tone = 'info') {
  if (pushMessage) pushMessage({ text, tone });
}

export default function FeedbackHost() {
  const [message, setMessage] = useState(null);

  useEffect(() => {
    pushMessage = (next) => setMessage({ ...next, id: Date.now() + Math.random() });
    return () => { pushMessage = null; };
  }, []);

  useEffect(() => {
    if (!message) return undefined;
    const timer = setTimeout(() => setMessage(null), 7000);
    return () => clearTimeout(timer);
  }, [message]);

  useEffect(() => {
    let timer = null;
    let changed = false;
    const observer = new MutationObserver(() => {
      changed = true;
      if (timer) { clearTimeout(timer); timer = null; }
    });
    observer.observe(document.body, { subtree: true, childList: true, attributes: true, characterData: true });

    function onClick(event) {
      const button = event.target.closest?.('button');
      if (!button || button.disabled || button.closest('.feedback')) return;
      if (button.form && !button.form.checkValidity()) return;
      const label = (button.getAttribute('aria-label') || button.innerText || 'this control').trim().replace(/\s+/g, ' ').slice(0, 60);
      changed = false;
      if (timer) clearTimeout(timer);
      timer = setTimeout(() => {
        timer = null;
        if (!changed && button.isConnected) {
          announce(`“${label}” was selected, but nothing changed. It may already be active, or unavailable for this role or dataset.`, 'warn');
        }
      }, 900);
    }

    document.addEventListener('click', onClick, true);
    return () => {
      observer.disconnect();
      document.removeEventListener('click', onClick, true);
      if (timer) clearTimeout(timer);
    };
  }, []);

  return <div className="feedback-stack" aria-live="polite" aria-atomic="false">
    {message && <div className={`feedback feedback-${message.tone}`} role="status" key={message.id}>
      <span>{message.text}</span>
      <button type="button" aria-label="Dismiss message" onClick={() => setMessage(null)}>×</button>
    </div>}
  </div>;
}
