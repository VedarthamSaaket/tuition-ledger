import React, { useState } from 'react';
import { formatMoney } from '../../lib/money.js';

const setupForms = {
  Program: {path:'/programs', fields:[['name','text'],['level','UG|PG|DIP|CERT'],['department','STEM|BUSINESS|ARTS|HEALTH'],['has_lab','boolean']]},
  Term: {path:'/terms', fields:[['name','text'],['season','FALL|SPRING|SUMMER'],['year','number'],['invoice_date','date'],['start_date','date'],['due_date','date'],['end_date','date']]},
  Student: {path:'/students', fields:[['first_name','text'],['last_name','text'],['email','email'],['program_id','text'],['admit_term_id','text'],['residency','DOMESTIC|INTL'],['income_band','LOW|MEDIUM|HIGH'],['gpa','decimal'],['has_external_cover','boolean'],['staff_dependent','boolean']]},
  'Fee schedule': {path:'/fee-schedules', fields:[['program_id','text'],['term_id','text'],['fee_code','TUITION|TECH|LIBRARY|ACTIVITY|LAB|HEALTH_INSURANCE|INTL_SURCHARGE'],['rate','decimal'],['applies_when','ALL|INTL|FULL_TIME|LAB_PROGRAM|FULL_TIME_NO_COVER'],['effective_from','date'],['effective_to','optional-date']]},
  Enrollment: {path:'/enrollments', fields:[['student_id','text'],['term_id','text'],['credits','number']]},
  Invoice: {fields:[['enrollment_id','text']]},
};
export default function Setup({api}) {
  const [kind,setKind]=useState('Program');
  const [values,setValues]=useState({});
  const [result,setResult]=useState('');
  const [error,setError]=useState('');
  const form=setupForms[kind];
  async function submit(e) {
    e.preventDefault(); setError(''); setResult('');
    const body={};
    for (const [name,type] of form.fields) {
      if (type==='boolean') body[name]=values[name]===true;
      else if (type==='optional-date' && !values[name]) body[name]=null;
      else body[name]=values[name] ?? (type.includes('|') ? type.split('|')[0] : '');
    }
    try {
      const path=kind==='Invoice' ? '/enrollments/'+encodeURIComponent(body.enrollment_id)+'/invoice' : form.path;
      const response=await api(path,{method:'POST', ...(kind==='Invoice' ? {} : {body:JSON.stringify(body)})});
      setResult(response.net_amount == null ? JSON.stringify(response) : `${response.invoice_id} · ${formatMoney(response.net_amount)}`); setValues({});
    } catch(err) {setError(typeof err.message==='string' ? err.message : 'Could not create record');}
  }
  return <div className="panel"><p>Create reference data before enrolling a student and issuing an invoice. Monetary rates are in Indian rupees (₹).</p><label>Record type <select value={kind} onChange={e=>{setKind(e.target.value);setValues({});setResult('');setError('')}}>{Object.keys(setupForms).map(k=><option key={k}>{k}</option>)}</select></label><form className="setup-form" onSubmit={submit}>{form.fields.map(([name,type])=><label key={name}>{name.replaceAll('_',' ')} {name==='rate' && '(₹)'} {type==='boolean' ? <input type="checkbox" checked={values[name]===true} onChange={e=>setValues({...values,[name]:e.target.checked})}/> : type.includes('|') ? <select value={values[name]??type.split('|')[0]} onChange={e=>setValues({...values,[name]:e.target.value})}>{type.split('|').map(option=><option key={option}>{option}</option>)}</select> : <input type={type==='optional-date'?'date':type==='decimal'?'number':type} step={type==='decimal'?'0.01':undefined} required={type!=='optional-date'} value={values[name]??''} onChange={e=>setValues({...values,[name]:e.target.value})}/>}</label>)}<button type="submit">Create {kind.toLowerCase()}</button></form>{result && <p role="status">Created: {result}</p>}{error && <p className="error" role="alert">{error}</p>}</div>;
}
