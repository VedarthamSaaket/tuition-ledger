const format = new Intl.NumberFormat('en-IN', {
  style: 'currency', currency: 'INR', minimumFractionDigits: 2, maximumFractionDigits: 2,
});

export function formatMoney(value) {
  const amount = Number(value);
  return value == null || value === '' || !Number.isFinite(amount) ? 'Not available' : format.format(amount);
}

const monetaryFields = new Set([
  'rate', 'cap', 'amount', 'balance', 'ledger_balance', 'running_balance', 'unit_amount', 'net_amount',
  'amount_allocated', 'amount_unapplied', 'amount_refunded', 'allocated', 'unapplied', 'unapplied_credit',
  'total_charges', 'total_credits', 'total_reversals', 'total_billed', 'total_paid', 'total_refunded',
  'net_billed', 'collected', 'total_collected', 'outstanding', 'outstanding_receivable', 'credit_owed',
  'credit_balances_owed', 'total_scholarships_and_waivers', 'late_fee_amount', 'eligible_fee_base',
  'award_amount', 'awarded', 'detected_value', 'expected_value', 'reversal', 'invoice_balance',
]);

export function isMoneyField(name) {
  return monetaryFields.has(name);
}

export function formatMoneyFields(record) {
  return Object.fromEntries(Object.entries(record).map(([name, value]) => [name, isMoneyField(name) ? formatMoney(value) : value]));
}
