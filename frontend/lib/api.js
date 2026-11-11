export async function request(path, options = {}, actorHeaders = {}) {
  const response = await fetch('/api' + path, {...options, headers: {...actorHeaders, 'Content-Type':'application/json', ...options.headers}});
  const value = await response.json();
  if (!response.ok) throw new Error(Array.isArray(value.detail) ? value.detail.map(x=>`${x.loc?.slice(1).join('.') || 'Input'}: ${x.msg}`).join('; ') : value.detail || 'Request failed');
  return value;
}
