import React, { useEffect, useRef, useState } from 'react';
import AccountView from './features/accounts/AccountView.jsx';
import InvoiceView from './features/billing/InvoiceView.jsx';
import Setup from './features/setup/Setup.jsx';
import Table from './components/Table.jsx';
import { request } from './lib/api.js';
import { formatMoney, formatMoneyFields } from './lib/money.js';

export default function App() {
  const [role, setRole] = useState('platform_admin');
  const [studentId, setStudentId] = useState('');
  const [page, setPage] = useState('Dashboard');
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [query, setQuery] = useState('');
  const [studentOffset, setStudentOffset] = useState(0);
  const [selected, setSelected] = useState('');
  const [invoice, setInvoice] = useState(null);
  const [amount, setAmount] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('BANK_TRANSFER');
  const [scheme, setScheme] = useState('SCHEME-NEED');
  const [refundPayment, setRefundPayment] = useState('');
  const [refundAmount, setRefundAmount] = useState('');
  const [refundReason, setRefundReason] = useState('OVERPAYMENT');
  const paymentAttempt = useRef(null);
  const refundAttempt = useRef(null);
  const [submitting, setSubmitting] = useState(false);
  const headers = {'X-Role': role, ...(studentId ? {'X-Student-Id': studentId} : {})};
  async function api(path, options = {}) {
    return request(path, options, headers);
  }
  async function load(path, setter = setData) { try { setError(''); setter(await api(path)); } catch(e) { setError(e.message); } }
  useEffect(() => {
    setData(null); setInvoice(null); setError('');
    if (page === 'Dashboard') load('/summary');
    if (page === 'Students') { setStudentOffset(0); load('/students?limit=50'); }
    if (page === 'Fees') load('/fee-schedules');
    if (page === 'Exceptions') load('/reconciliation/runs');
    if (page === 'My account' && studentId) load('/students/' + encodeURIComponent(studentId));
  }, [page, role, studentId]);
  async function run() { try { const result = await api('/reconciliation/runs', {method:'POST'}); await load('/reconciliation/runs/' + result.run_id + '/exceptions'); } catch(e) {setError(e.message)} }
  async function pay(e) { e.preventDefault(); if(submitting) return; setSubmitting(true); const payload=JSON.stringify({invoice_id:invoice.invoice_id,amount,method:paymentMethod}); if(!paymentAttempt.current || paymentAttempt.current.payload!==payload) paymentAttempt.current={payload,key:crypto.randomUUID()}; try { await api('/payments', {method:'POST',headers:{'Idempotency-Key':paymentAttempt.current.key},body:payload}); paymentAttempt.current=null; setAmount(''); setMessage('Payment recorded. No transfer was initiated by this application.'); await load('/invoices/' + invoice.invoice_id, setInvoice); await load('/students/' + selected); } catch(e) {setError(e.message)} finally {setSubmitting(false)} }
  async function action(path, body) { try { const result = await api(path, {method:'POST', ...(body ? {body:JSON.stringify(body)} : {})}); setMessage(JSON.stringify(formatMoneyFields(result))); await load('/invoices/' + invoice.invoice_id, setInvoice); await load('/students/' + selected); } catch(e) {setError(e.message)} }
  async function refund(e) { e.preventDefault(); if(submitting) return; setSubmitting(true); const payload=JSON.stringify({payment_id:refundPayment,amount:refundAmount,reason:refundReason}); if(!refundAttempt.current || refundAttempt.current.payload!==payload) refundAttempt.current={payload,key:crypto.randomUUID()}; try { await api('/refunds', {method:'POST',headers:{'Idempotency-Key':refundAttempt.current.key},body:payload}); refundAttempt.current=null; setRefundAmount(''); await load('/students/' + selected); if(invoice?.invoice_id) await load('/invoices/' + invoice.invoice_id,setInvoice); } catch(e) {setError(e.message)} finally {setSubmitting(false)} }
  const money = formatMoney;
  return <><header><div><strong>Tuition Ledger</strong><small>Student finance workspace</small></div><div className="roles"><label>Demo role <select value={role} onChange={e=>setRole(e.target.value)}>{['platform_admin','academic_admin','support_staff','instructor','learner'].map(x=><option key={x}>{x}</option>)}</select></label>{role==='learner' && <input placeholder="Student ID" value={studentId} onChange={e=>setStudentId(e.target.value)}/>}</div></header>
  <div className="notice">Role selection is not authentication. Protect access at the deployment boundary.</div><main><nav>{['Dashboard','Students','My account','Setup','Fees','Exceptions'].map(x=><button className={page===x?'active':''} onClick={()=>setPage(x)} key={x}>{x}</button>)}</nav><section><h1>{page}</h1>{error && <p className="error">{error}</p>}{message && <p role="status">{message}</p>}
  {page==='Dashboard' && data && <><div className="cards">{[['Students',data.students],['Invoices',data.invoices],['Net billed',money(data.net_billed)],['Outstanding',money(data.outstanding)]].map(([a,b])=><article key={a}><span>{a}</span><strong>{b}</strong></article>)}</div><h2>Invoices by term</h2><Table rows={data.by_term}/></>}
  {page==='Students' && <><form onSubmit={e=>{e.preventDefault();setStudentOffset(0);load('/students?limit=50&offset=0&q='+encodeURIComponent(query))}}><input placeholder="Search name, ID or email" value={query} onChange={e=>setQuery(e.target.value)}/><button>Search</button></form>{data?.items && <><div className="list">{data.items.map(s=><button key={s.student_id} onClick={()=>{setSelected(s.student_id);load('/students/'+s.student_id)}}><span>{s.first_name} {s.last_name}<small>{s.student_id} · {s.program}</small></span><b>{money(s.balance)}</b></button>)}</div><div className="pagination"><button disabled={studentOffset===0} onClick={()=>{const n=Math.max(0,studentOffset-50);setStudentOffset(n);load('/students?limit=50&offset='+n+'&q='+encodeURIComponent(query))}}>Previous</button><span>Showing {studentOffset+1}–{Math.min(studentOffset+50,data.total)} of {data.total}</span><button disabled={studentOffset+50>=data.total} onClick={()=>{const n=studentOffset+50;setStudentOffset(n);load('/students?limit=50&offset='+n+'&q='+encodeURIComponent(query))}}>Next</button></div></>}</>}
  {(page==='My account' || page==='Students') && data?.account && <AccountView data={data} money={money} load={load} setInvoice={setInvoice} setSelected={setSelected} role={role} refund={refund} refundPayment={refundPayment} setRefundPayment={setRefundPayment} refundReason={refundReason} setRefundReason={setRefundReason} refundAmount={refundAmount} setRefundAmount={setRefundAmount} submitting={submitting}/>}
  {Array.isArray(invoice) && <div className="panel"><h2>Ledger</h2><Table rows={invoice}/></div>}
  {invoice?.invoice_id && <InvoiceView invoice={invoice} money={money} role={role} pay={pay} amount={amount} setAmount={setAmount} paymentMethod={paymentMethod} setPaymentMethod={setPaymentMethod} submitting={submitting} scheme={scheme} setScheme={setScheme} action={action}/>}
  {page==='Setup' && (['academic_admin','platform_admin'].includes(role) ? <Setup api={api} /> : <p>Academic administrator access is required.</p>)}
  {page==='Fees' && data && <Table rows={data}/>} {page==='Exceptions' && <><button onClick={run}>Run reconciliation</button><button onClick={()=>load('/reconciliation/runs')}>View recent runs</button>{Array.isArray(data) && data.some(row=>row.run_id && row.exceptions_found !== undefined) && <div className="list">{data.map(row=><button key={row.run_id} onClick={()=>load('/reconciliation/runs/'+encodeURIComponent(row.run_id)+'/exceptions')}><span>{row.run_id}<small>{row.started_at}</small></span><b>{row.exceptions_found} findings</b></button>)}</div>}{data && <Table rows={data}/>}</>}
  </section></main></>;
}
