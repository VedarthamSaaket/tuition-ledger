import { test } from 'node:test';
import { deepStrictEqual, strictEqual } from 'node:assert';
import { tableColumns, tablePage } from './table.js';

test('includes late columns and records beyond the first hundred', () => {
  const rows = Array.from({length: 125}, (_, i) => ({id: i, ...(i === 124 ? {explanation: 'last finding'} : {})}));
  deepStrictEqual(tableColumns(rows), ['id', 'explanation']);
  const last = tablePage(rows, 2);
  strictEqual(last.pages, 3);
  strictEqual(last.rows.at(-1).explanation, 'last finding');
  strictEqual(tablePage(rows, 99).current, 2);
});
