import { test } from 'node:test';
import { strictEqual } from 'node:assert';
import { formatMoney, isMoneyField } from './money.js';

test('formats rupees with Indian grouping and paise', () => {
  strictEqual(formatMoney('1234567.5'), '₹12,34,567.50');
  strictEqual(formatMoney(0), '₹0.00');
  strictEqual(formatMoney(null), '—');
  strictEqual(isMoneyField('award_amount'), true);
  strictEqual(isMoneyField('credits'), false);
});
