export function tableColumns(rows) {
  return [...new Set(rows.flatMap(row => Object.keys(row)))];
}

export function tablePage(rows, page, pageSize = 50) {
  const pages = Math.max(1, Math.ceil(rows.length / pageSize));
  const current = Math.min(Math.max(page, 0), pages - 1);
  return {pages, current, rows: rows.slice(current * pageSize, (current + 1) * pageSize)};
}
