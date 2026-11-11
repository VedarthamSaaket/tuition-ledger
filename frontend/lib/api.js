export async function request(path, options = {}, actorHeaders = {}) {
  let response;
  try {
    response = await fetch('/api' + path, {...options, headers: {...actorHeaders, 'Content-Type':'application/json', ...options.headers}});
  } catch {
    throw new Error('The server could not be reached. Start the API on port 8000, then try again.');
  }
  const text = await response.text();
  let value = null;
  try { value = text ? JSON.parse(text) : null; } catch { value = null; }
  if (!response.ok) {
    const detail = Array.isArray(value?.detail) ? value.detail.map(x=>`${x.loc?.slice(1).join('.') || 'Input'}: ${x.msg}`).join('; ') : value?.detail;
    throw new Error(detail || `Request failed (${response.status}). No change was saved.`);
  }
  if (value === null) throw new Error('The server returned an unreadable response. No change was saved.');
  return value;
}
