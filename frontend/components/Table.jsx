import React, { useEffect, useState } from 'react';
import { tableColumns, tablePage } from '../lib/table.js';
import { formatMoney, isMoneyField } from '../lib/money.js';

export default function Table({rows}) {
  const [page, setPage] = useState(0);
  useEffect(() => setPage(0), [rows]);
  if (!rows?.length) return <p>No records.</p>;
  const cols = tableColumns(rows);
  const {pages, current, rows: visible} = tablePage(rows, page);
  return <><div className="table"><table><thead><tr>{cols.map(c=><th key={c} scope="col">{c.replaceAll('_',' ')}{isMoneyField(c) ? ' (₹)' : ''}</th>)}</tr></thead><tbody>{visible.map((row,i)=><tr key={i}>{cols.map(c=><td key={c}>{isMoneyField(c) ? formatMoney(row[c]) : typeof row[c]==='object' && row[c]!==null?JSON.stringify(row[c]):String(row[c]??'—')}</td>)}</tr>)}</tbody></table></div><div className="pagination"><button type="button" disabled={current===0} onClick={()=>setPage(current-1)}>Previous</button><span>Page {current+1} of {pages} · {rows.length} records</span><button type="button" disabled={current>=pages-1} onClick={()=>setPage(current+1)}>Next</button></div></>;
}
