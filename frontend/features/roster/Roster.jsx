import React, { useEffect, useState } from 'react';
import Table from '../../components/Table.jsx';
import Icon from '../../components/Icon.jsx';

export default function Roster({ api }) {
  const [programs, setPrograms] = useState([]);
  const [terms, setTerms] = useState([]);
  const [program, setProgram] = useState('');
  const [term, setTerm] = useState('');
  const [roster, setRoster] = useState(null);
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    Promise.all([api('/programs'), api('/terms')]).then(([programRows, termRows]) => {
      if (cancelled) return;
      setPrograms(programRows); setTerms(termRows);
      setProgram(programRows[0]?.program_id || ''); setTerm(termRows.at(-1)?.term_id || '');
    }).catch(err => { if (!cancelled) setError(err.message); });
    return () => { cancelled = true; };
  }, []);

  async function submit(event) {
    event.preventDefault(); setError(''); setStatus('Loading roster…');
    try {
      const rows = await api(`/roster?program_id=${encodeURIComponent(program)}&term_id=${encodeURIComponent(term)}`);
      setRoster(rows);
      setStatus(rows.length ? `${rows.length} enrolled learner${rows.length === 1 ? '' : 's'} shown.` : 'No learners are enrolled for that programme and term.');
    } catch (err) { setRoster(null); setStatus(''); setError(err.message); }
  }

  return <div className="panel roster-panel"><p className="panel-kicker">ACADEMIC RECORDS</p><h2>Class roster</h2><p>Choose a programme and term to see enrolled learners.</p>
    <form onSubmit={submit} className="roster-form"><label>Programme<select value={program} onChange={e=>setProgram(e.target.value)} required><option value="" disabled>Select programme</option>{programs.map(p=><option key={p.program_id} value={p.program_id}>{p.name}</option>)}</select></label><label>Term<select value={term} onChange={e=>setTerm(e.target.value)} required><option value="" disabled>Select term</option>{terms.map(t=><option key={t.term_id} value={t.term_id}>{t.name}</option>)}</select></label><button disabled={!program || !term}>View roster <Icon name="arrowUp"/></button></form>
    {status && <p role="status">{status}</p>}{error && <p className="error" role="alert">{error}</p>}{roster && <Table rows={roster}/>}
  </div>;
}
