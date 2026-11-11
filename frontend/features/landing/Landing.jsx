import React, { useState } from 'react';
import { prepareEntry, roles } from '../../lib/roles.js';
import Icon from '../../components/Icon.jsx';

export default function Landing({ onEnter }) {
  const [selectedRole, setSelectedRole] = useState('');
  const [studentId, setStudentId] = useState('');
  const [error, setError] = useState('');

  function enter(event) {
    event.preventDefault();
    const entry = prepareEntry(selectedRole, studentId);
    if (entry.error) { setError(entry.error); return; }
    setError('');
    onEnter(entry);
    window.scrollTo(0, 0);
  }

  return <div className="landing">
    <header className="landing-nav">
      <a href="#top" className="brand" aria-label="Tuition Ledger home"><span className="brand-mark">T<span>·</span>L</span><span><strong>Tuition Ledger</strong><small>STUDENT FINANCE WORKSPACE</small></span></a>
      <nav aria-label="Landing navigation"><a href="#how-it-works">The workflow</a><a href="#choose-role">Choose a role <Icon name="arrowUp"/></a></nav>
    </header>
    <main id="top" className="landing-main">
      <section className="hero">
        <div className="hero-copy">
          <div className="eyebrow"><span className="eyebrow-line"/> A clearer way to manage student finance</div>
          <h1>Every detail.<br/><em>In balance.</em></h1>
          <p className="hero-description">From the first fee to the final balance, bring tuition, scholarships, payments, and reconciliation together in one thoughtful workspace.</p>
          <div className="hero-actions"><a href="#choose-role" className="landing-button">Enter the workspace <Icon name="arrowUp"/></a><a href="#how-it-works" className="text-link">Explore how it works <Icon name="arrowDown"/></a></div>
          <div className="hero-footnote"><span>01 / STUDENT FINANCE</span><span>DESIGNED FOR CLARITY</span></div>
        </div>
        <div className="hero-visual" aria-label="Illustration of the student finance workflow">
          <div className="orbit orbit-one"/><div className="orbit orbit-two"/>
          <div className="ledger-illustration"><div className="ledger-top"><span>THE STUDENT LEDGER</span><Icon name="sparkle"/></div><div className="ledger-heading">A little more<br/><em>clarity.</em></div><div className="ledger-rule"/><div className="ledger-row"><span>01</span><strong>Tuition & fees</strong><Icon name="arrowUp"/></div><div className="ledger-row"><span>02</span><strong>Scholarships</strong><Icon name="arrowUp"/></div><div className="ledger-row"><span>03</span><strong>Payments</strong><Icon name="arrowUp"/></div><div className="ledger-row"><span>04</span><strong>Reconciliation</strong><Icon name="arrowUp"/></div><div className="ledger-bottom"><span>ONE CONNECTED VIEW</span><span>INR · ₹</span></div></div>
          <div className="visual-index">A considered view<br/>of every detail <span>: 01</span></div>
        </div>
      </section>
      <div className="landing-ticker" aria-label="Workspace capabilities"><span>ENROLMENT</span><Icon name="sparkle"/><span>FEES & INVOICING</span><Icon name="sparkle"/><span>SCHOLARSHIPS</span><Icon name="sparkle"/><span>PAYMENTS</span><Icon name="sparkle"/><span>RECONCILIATION</span></div>
      <section id="how-it-works" className="story-section">
        <div className="section-rule"><span>THE WORKFLOW</span><span>01 : 03</span></div>
        <div className="story-intro"><div><p className="section-kicker">FINANCE, WITH CONTEXT</p><h2>More than a<br/><em>number.</em></h2></div><p>Understand how a balance came to be. Follow the trail from enrolment and fee schedules through awards, payments, and the decisions behind them.</p></div>
        <div className="story-grid"><article><span>01 / ESTABLISH</span><h3>Start with the essentials.</h3><p>Bring programmes, terms, students, and fee schedules together before creating an invoice.</p></article><article><span>02 / APPLY</span><h3>Make each adjustment count.</h3><p>Assess scholarship eligibility, allocate payments, and record the changes that affect an account.</p></article><article><span>03 / UNDERSTAND</span><h3>See the complete picture.</h3><p>Trace the ledger, review exceptions, and reconcile balances with the underlying records.</p></article></div>
      </section>
      <section id="choose-role" className="entry-section"><div className="entry-heading"><p className="section-kicker">YOUR WORKSPACE AWAITS</p><h2>Make yourself<br/><em>at home.</em></h2><p>Choose how you’ll be using Tuition Ledger. Your workspace will open with the relevant tools for that role.</p><div className="entry-note"><Icon name="sparkle"/><p>This is a role-based preview, not a sign-in. Selecting a role does not verify identity.</p></div></div>
        <form className="role-panel" onSubmit={enter}><div className="role-panel-top"><span>SELECT YOUR ROLE</span><span>02 / GET STARTED</span></div><div className="role-options">{roles.map((role, index)=><button key={role.id} type="button" aria-pressed={selectedRole===role.id} className={`role-option ${selectedRole===role.id?'is-selected':''}`} onClick={()=>{setSelectedRole(role.id);setError('')}}><span className="role-index">0{index+1}</span><span className="role-copy"><strong>{role.label}</strong><small>{role.description}</small></span><span className="role-indicator"><Icon name={selectedRole===role.id?'check':'arrowUp'}/></span></button>)}</div>
          {selectedRole==='learner' && <label className="student-id-label">Student ID <input value={studentId} onChange={e=>setStudentId(e.target.value)} placeholder="STU-000001" autoComplete="off" aria-describedby="student-help"/><small id="student-help">Enter the student ID for the account you want to view.</small></label>}
          {error && <p className="landing-error" role="alert">{error}</p>}
          <button className="enter-button" type="submit">Enter Tuition Ledger <Icon name="arrowUp"/></button>
        </form>
      </section>
    </main>
    <footer className="landing-footer"><span>TUITION LEDGER <Icon name="sparkle"/> STUDENT FINANCE, MADE CLEAR</span><a href="#top">BACK TO TOP <Icon name="arrowTop"/></a></footer>
  </div>;
}
