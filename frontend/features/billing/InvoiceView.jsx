import React from 'react';
import Table from '../../components/Table.jsx';

export default function InvoiceView({invoice, money, role, pay, amount, setAmount, paymentMethod, setPaymentMethod, submitting, scheme, setScheme, action}) {
  return <div className="panel">
    <h2>Invoice {invoice.invoice_id}</h2>
    <p>{invoice.status} · Balance {money(invoice.balance)}</p>
    <Table rows={invoice.lines}/>
    {['support_staff','platform_admin'].includes(role) && <>
      <p>Record a payment already received outside this application. No transfer or card charge is initiated.</p>
      <form onSubmit={pay}>
        <input type="number" min="0.01" step="0.01" required aria-label="Payment amount in rupees" placeholder="Payment amount (₹)" value={amount} onChange={e=>setAmount(e.target.value)}/>
        <select aria-label="Payment method" value={paymentMethod} onChange={e=>setPaymentMethod(e.target.value)}><option>BANK_TRANSFER</option><option>CARD</option><option>CHEQUE</option><option>SPONSOR</option></select>
        <button disabled={submitting}>Record received payment</button>
      </form>
    </>}
    {['academic_admin','platform_admin'].includes(role) && <>
      <form onSubmit={e=>{e.preventDefault();action('/scholarship-assessments',{invoice_id:invoice.invoice_id,scheme_id:scheme})}}>
        <select value={scheme} onChange={e=>setScheme(e.target.value)}>{['SCHEME-NEED','SCHEME-MERIT-UG','SCHEME-MERIT-PG','SCHEME-STEM','SCHEME-INTL','SCHEME-WAIVER-HARDSHIP','SCHEME-WAIVER-STAFF'].map(s=><option key={s}>{s}</option>)}</select>
        <button>Assess scholarship</button>
      </form>
      <button onClick={()=>action('/enrollments/'+invoice.enrollment_id+'/withdraw')}>Withdraw enrollment</button>
    </>}
    {role==='platform_admin' && <button onClick={()=>action('/invoices/'+invoice.invoice_id+'/late-fee')}>Assess late fee</button>}
    <h3>Decision history</h3><Table rows={invoice.decisions}/>
    <h3>Events</h3><Table rows={invoice.events}/>
  </div>;
}
