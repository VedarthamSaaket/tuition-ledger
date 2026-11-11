import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

function App() {
  const [role, setRole] = useState('platform_admin');
  const [studentId, setStudentId] = useState('');
  const [page, setPage] = useState('Dashboard');
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState('');
  const [invoice, setInvoice] = useState(null);
  const [amount, setAmount] = useState('');
  const [scheme, setScheme] = useState('SCHEME-NEED');
  const [refundPayment, setRefundPayment] = useState('');
  const [refundAmount, setRefundAmount] = useState('');
  const [refundReason, setRefundReason] = useState('OVERPAYMENT');
  const headers = {'X-Role': role, ...(studentId ? {'X-Student-Id': studentId} : {})};
  async function api(path, options = {}) {
    const response = await fetch('/api' + path, {...options, headers: {...headers, 'Content-Type':'application/json'}});
    const value = await response.json();
    if (!response.ok) throw new Error(value.detail || 'Request failed');
    return value;
  }
  async function load(path, setter = setData) { try { setError(''); setter(await api(path)); } catch(e) { setError(e.message); } }
  useEffect(() => {
    setData(null); setInvoice(null); setError('');
    if (page === 'Dashboard') load('/summary');
    if (page === 'Students') load('/students?limit=50');
    if (page === 'Fees') load('/fee-schedules');
    if (page === 'Exceptions') load('/reconciliation/runs');
    if (page === 'My account' && studentId) load('/students/' + encodeURIComponent(studentId));
  }, [page, role, studentId]);
  async function run() { try { const result = await api('/reconciliation/runs', {method:'POST'}); await load('/reconciliation/runs/' + result.run_id + '/exceptions'); } catch(e) {setError(e.message)} }
  async function pay(e) { e.preventDefault(); try { await api('/payments', {method:'POST',body:JSON.stringify({invoice_id:invoice.invoice_id,amount,method:'CARD'})}); setAmount(''); await load('/invoices/' + invoice.invoice_id, setInvoice); await load('/students/' + selected); } catch(e) {setError(e.message)} }
  async function action(path, body) { try { const result = await api(path, {method:'POST', ...(body ? {body:JSON.stringify(body)} : {})}); setMessage(JSON.stringify(result)); await load('/invoices/' + invoice.invoice_id, setInvoice); await load('/students/' + selected); } catch(e) {setError(e.message)} }
  async function refund(e) { e.preventDefault(); try { await api('/refunds', {method:'POST',body:JSON.stringify({payment_id:refundPayment,amount:refundAmount,reason:refundReason})}); setRefundAmount(''); await load('/students/' + selected); if(invoice) await load('/invoices/' + invoice.invoice_id,setInvoice); } catch(e) {setError(e.message)} }
  const money = n => '$' + Number(n || 0).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});
  return <><header><div><strong>Tuition Ledger</strong><small>Student finance workspace</small></div><div className="roles"><label>Demo role <select value={role} onChange={e=>setRole(e.target.value)}>{['platform_admin','academic_admin','support_staff','instructor','learner'].map(x=><option key={x}>{x}</option>)}</select></label>{role==='learner' && <input placeholder="Student ID" value={studentId} onChange={e=>setStudentId(e.target.value)}/>}</div></header>
  <div className="notice">Demo only · Role selection is not authentication. Synthetic data only.</div><main><nav>{['Dashboard','Students','My account','Fees','Exceptions'].map(x=><button className={page===x?'active':''} onClick={()=>setPage(x)} key={x}>{x}</button>)}</nav><section><h1>{page}</h1>{error && <p className="error">{error}</p>}{message && <p role="status">{message}</p>}
  {page==='Dashboard' && data && <><div className="cards">{[['Students',data.students],['Invoices',data.invoices],['Net billed',money(data.net_billed)],['Outstanding',money(data.outstanding)]].map(([a,b])=><article key={a}><span>{a}</span><strong>{b}</strong></article>)}</div><h2>Invoices by term</h2><Table rows={data.by_term}/></>}
  {page==='Students' && <><form onSubmit={e=>{e.preventDefault();load('/students?q='+encodeURIComponent(query))}}><input placeholder="Search name, ID or email" value={query} onChange={e=>setQuery(e.target.value)}/><button>Search</button></form>{data?.items && <div className="list">{data.items.map(s=><button key={s.student_id} onClick={()=>{setSelected(s.student_id);load('/students/'+s.student_id)}}><span>{s.first_name} {s.last_name}<small>{s.student_id} · {s.program}</small></span><b>{money(s.balance)}</b></button>)}</div>}</>}
  {(page==='My account' || page==='Students') && data?.account && <><h2>{data.first_name} {data.last_name}</h2><p>Account balance <strong>{money(data.account.balance)}</strong> · Ledger balance {money(data.ledger_balance)}</p><button onClick={()=>load('/students/'+data.student_id+'/ledger',setInvoice)}>View ledger</button><h3>Invoices</h3><div className="list">{data.enrollments.map(e=><button key={e.invoice_id} onClick={()=>{setSelected(data.student_id);load('/invoices/'+e.invoice_id,setInvoice)}}><span>{e.invoice_id}<small>{e.term_id} · {e.invoice_status}</small></span><b>{money(e.balance)}</b></button>)}</div><h3>Payments</h3><Table rows={data.payments}/>{['support_staff','platform_admin'].includes(role) && <form onSubmit={refund}><select required value={refundPayment} onChange={e=>{setSelected(data.student_id);setRefundPayment(e.target.value)}}><option value="">Select payment</option>{data.payments.map(p=><option key={p.payment_id}>{p.payment_id}</option>)}</select><select value={refundReason} onChange={e=>setRefundReason(e.target.value)}><option>OVERPAYMENT</option><option>WITHDRAWAL</option><option>CANCELLATION</option></select><input type="number" min="0.01" step="0.01" required placeholder="Refund amount" value={refundAmount} onChange={e=>setRefundAmount(e.target.value)}/><button>Issue refund</button></form>}</>}
  {Array.isArray(invoice) && <div className="panel"><h2>Ledger</h2><Table rows={invoice}/></div>}
  {invoice?.invoice_id && <div className="panel"><h2>Invoice {invoice.invoice_id}</h2><p>{invoice.status} · Balance {money(invoice.balance)}</p><Table rows={invoice.lines}/>{['learner','support_staff','platform_admin'].includes(role) && <form onSubmit={pay}><input type="number" min="0.01" step="0.01" required placeholder="Payment amount" value={amount} onChange={e=>setAmount(e.target.value)}/><button>Record payment</button></form>}{['academic_admin','platform_admin'].includes(role) && <><form onSubmit={e=>{e.preventDefault();action('/scholarship-assessments',{invoice_id:invoice.invoice_id,scheme_id:scheme})}}><select value={scheme} onChange={e=>setScheme(e.target.value)}>{['SCHEME-NEED','SCHEME-MERIT-UG','SCHEME-MERIT-PG','SCHEME-STEM','SCHEME-INTL','SCHEME-WAIVER-HARDSHIP','SCHEME-WAIVER-STAFF'].map(s=><option key={s}>{s}</option>)}</select><button>Assess scholarship</button></form><button onClick={()=>action('/enrollments/'+invoice.enrollment_id+'/withdraw')}>Withdraw enrollment</button></>}{role==='platform_admin' && <button onClick={()=>action('/invoices/'+invoice.invoice_id+'/late-fee')}>Assess late fee</button>}<h3>Decision history</h3><Table rows={invoice.decisions}/><h3>Events</h3><Table rows={invoice.events}/></div>}
  {page==='Fees' && data && <Table rows={data}/>} {page==='Exceptions' && <><button onClick={run}>Run reconciliation</button>{data && <Table rows={data}/>}</>}
  </section></main></>;
}
function Table({rows}) { if (!rows?.length) return <p>No records.</p>; const cols=Object.keys(rows[0]).slice(0,8); return <div className="table"><table><thead><tr>{cols.map(c=><th key={c}>{c.replaceAll('_',' ')}</th>)}</tr></thead><tbody>{rows.slice(0,100).map((row,i)=><tr key={i}>{cols.map(c=><td key={c}>{typeof row[c]==='object'?JSON.stringify(row[c]):String(row[c]??'—')}</td>)}</tr>)}</tbody></table></div> }
createRoot(document.getElementById('root')).render(<App/>);
