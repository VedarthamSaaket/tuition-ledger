import React from 'react';
import Table from '../../components/Table.jsx';

export default function AccountView({data, money, load, notice, setInvoice, setSelected, role, refund, refundPayment, setRefundPayment, refundReason, setRefundReason, refundAmount, setRefundAmount, submitting}) {
  function openLedger() {
    notice('Loading ledger…');
    load('/students/' + data.student_id + '/ledger', setInvoice).then(rows => {
      if (rows) notice(rows.length ? `Ledger opened with ${rows.length} entries.` : 'Ledger opened. No entries were recorded.');
    });
  }
  function openInvoice(invoiceId) {
    notice('Opening invoice…');
    setSelected(data.student_id);
    load('/invoices/' + invoiceId, setInvoice).then(value => {
      if (value) notice('Invoice opened below.');
    });
  }
  return <>
    <h2>{data.first_name} {data.last_name}</h2>
    <p>Account balance <strong>{money(data.account.balance)}</strong> · Ledger balance {money(data.ledger_balance)}</p>
    <button onClick={openLedger}>View ledger</button>
    <h3>Invoices</h3>
    <div className="list">{data.enrollments.map(e => e.invoice_id ?
      <button key={e.enrollment_id + e.invoice_id} onClick={() => openInvoice(e.invoice_id)}>
        <span>{e.invoice_id}<small>{e.term_id} · {e.invoice_status}</small></span><b>{money(e.balance)}</b>
      </button> : <p key={e.enrollment_id}>{e.term_id} · Invoice not issued</p>)}</div>
    <h3>Payments</h3><Table rows={data.payments}/>
    {['support_staff','platform_admin'].includes(role) && <>
      <p>Record a refund processed outside this application. No money is transferred by this action.</p>
      <form onSubmit={refund}>
        <select aria-label="Payment to refund" required value={refundPayment} onChange={e => {setSelected(data.student_id); setRefundPayment(e.target.value)}}>
          <option value="">Select payment</option>{data.payments.map(p => <option key={p.payment_id}>{p.payment_id}</option>)}
        </select>
        <select aria-label="Refund reason" value={refundReason} onChange={e => setRefundReason(e.target.value)}>
          <option>OVERPAYMENT</option><option>WITHDRAWAL</option><option>CANCELLATION</option>
        </select>
        <input aria-label="Refund amount in rupees" type="number" min="0.01" step="0.01" required placeholder="Refund amount (₹)" value={refundAmount} onChange={e => setRefundAmount(e.target.value)}/>
        <button disabled={submitting}>Record refund</button>
      </form>
    </>}
  </>;
}
