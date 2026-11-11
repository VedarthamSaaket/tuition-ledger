import React, { useState } from 'react';
import { prepareEntry, roles, SAMPLE_STUDENT_ID } from '../../lib/roles.js';
import Icon from '../../components/Icon.jsx';

export default function Landing({ onEnter }) {
  const [selectedRole, setSelectedRole] = useState('');
  const [studentId, setStudentId] = useState('');
  const [sampleFilled, setSampleFilled] = useState(false);
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
      <nav aria-label="Landing navigation"><a href="#how-to-use">How to use</a><a href="#how-it-works">The workflow</a><a href="#choose-role">Choose a role <Icon name="arrowUp"/></a></nav>
    </header>
    <main id="top" className="landing-main">
      <section className="hero">
        <div className="hero-copy">
          <div className="eyebrow"><span className="eyebrow-line"/> A clearer way to manage student finance</div>
          <h1>Every detail.<br/><em>In balance.</em></h1>
          <p className="hero-description">From the first fee to the final balance, bring tuition, scholarships, payments, and reconciliation together in one thoughtful workspace.</p>
          <div className="hero-actions"><a href="#choose-role" className="landing-button">Enter the workspace <Icon name="arrowUp"/></a><a href="#how-it-works" className="text-link">Explore how it works <Icon name="arrowDown"/></a></div>
          <section id="how-to-use" className="hero-quickstart" aria-label="How to use Tuition Ledger">
            <div className="quickstart-head"><Icon name="sparkle"/><span>HOW TO USE · 3 STEPS</span></div>
            <ol className="quickstart-steps">
              <li><b>01</b><span>Choose a role</span></li>
              <li><b>02</b><span>Enter the workspace</span></li>
              <li><b>03</b><span>Use the left-hand menu</span></li>
            </ol>
            <p className="quickstart-note">Learner sample ID <strong>{SAMPLE_STUDENT_ID}</strong>. This is a role preview, not a sign-in, and no money is moved. <a href="#choose-role">Start now <Icon name="arrowUp"/></a></p>
          </section>
          <div className="hero-footnote"><span>01 / STUDENT FINANCE</span><span>DESIGNED FOR CLARITY</span></div>
        </div>
        <div className="hero-visual" aria-label="Illustration of the student finance workflow">
          <div className="orbit orbit-one"/><div className="orbit orbit-two"/>
          <div className="ledger-illustration"><div className="ledger-top"><span>THE STUDENT LEDGER</span><Icon name="sparkle"/></div><div className="ledger-heading">A little more<br/><em>clarity.</em></div><div className="ledger-rule"/><div className="ledger-row"><span>01</span><strong>Tuition &amp; fees</strong><Icon name="arrowUp"/></div><div className="ledger-row"><span>02</span><strong>Scholarships</strong><Icon name="arrowUp"/></div><div className="ledger-row"><span>03</span><strong>Payments</strong><Icon name="arrowUp"/></div><div className="ledger-row"><span>04</span><strong>Reconciliation</strong><Icon name="arrowUp"/></div><div className="ledger-bottom"><span>ONE CONNECTED VIEW</span><span>INR · ₹</span></div></div>
          <div className="visual-index">A considered view<br/>of every detail <span>: 01</span></div>
        </div>
      </section>
      <div className="landing-ticker" aria-label="Workspace capabilities"><span>ENROLMENT</span><Icon name="sparkle"/><span>FEES &amp; INVOICING</span><Icon name="sparkle"/><span>SCHOLARSHIPS</span><Icon name="sparkle"/><span>PAYMENTS</span><Icon name="sparkle"/><span>RECONCILIATION</span></div>
      <section id="how-it-works" className="story-section">
        <div className="section-rule"><span>THE WORKFLOW</span><span>01 : 03</span></div>
        <div className="story-intro"><div><p className="section-kicker">FINANCE, WITH CONTEXT</p><h2>More than a<br/><em>number.</em></h2></div><p>Understand how a balance came to be. Follow the trail from enrolment and fee schedules through awards, payments, and the decisions behind them.</p></div>
        <div className="story-grid"><article><span>01 / ESTABLISH</span><h3>Start with the essentials.</h3><p>Bring programmes, terms, students, and fee schedules together before creating an invoice.</p></article><article><span>02 / APPLY</span><h3>Make each adjustment count.</h3><p>Assess scholarship eligibility, allocate payments, and record the changes that affect an account.</p></article><article><span>03 / UNDERSTAND</span><h3>See the complete picture.</h3><p>Trace the ledger, review exceptions, and reconcile balances with the underlying records.</p></article></div>
      </section>
      <section id="choose-role" className="entry-section"><div className="entry-heading"><p className="section-kicker">YOUR WORKSPACE AWAITS</p><h2>Make yourself<br/><em>at home.</em></h2><p>Pick the role you want to review. Each workspace opens on its starting view with the right tools already in the left-hand menu. You can switch roles at any time.</p><div className="entry-note"><Icon name="sparkle"/><p>This is a role-based preview, not a sign-in. Selecting a role does not verify identity. No payment is charged or transferred.</p></div></div>
        <form className="role-panel" onSubmit={enter}><div className="role-panel-top"><span>SELECT YOUR ROLE</span><span>02 / GET STARTED</span></div><div className="role-options">{roles.map((role, index)=><button key={role.id} type="button" aria-pressed={selectedRole===role.id} className={`role-option ${selectedRole===role.id?'is-selected':''}`} onClick={()=>{setSelectedRole(role.id);setError('')}}><span className="role-index">0{index+1}</span><span className="role-copy"><strong>{role.label}</strong><small>{role.description}</small><span className="role-start">Opens in {role.views[0]}{selectedRole===role.id ? ` · Menu: ${role.views.join(' · ')}` : ''}</span></span><span className="role-indicator"><Icon name={selectedRole===role.id?'check':'arrowUp'}/></span></button>)}</div>
          {selectedRole==='learner' && <div className="student-id-field">
            <label htmlFor="learner-id">Student ID</label>
            <div className="student-id-row">
              <input id="learner-id" value={studentId} onChange={e=>{setStudentId(e.target.value);setSampleFilled(false)}} placeholder={SAMPLE_STUDENT_ID} autoComplete="off" aria-describedby="student-help"/>
              <button type="button" className="sample-id-button" onClick={()=>{setStudentId(SAMPLE_STUDENT_ID);setError('');setSampleFilled(true)}}>Use sample</button>
            </div>
            <p className="student-id-help" id="student-help"><strong>Sample ID {SAMPLE_STUDENT_ID}</strong> is present in the dataset loaded right now. If the dataset is replaced, enter an existing student ID from that dataset instead.</p>
            {sampleFilled && <p className="sample-filled" role="status">Sample ID filled. Choose Enter Tuition Ledger to continue.</p>}
          </div>}
          <p className="panel-help">Next: choose <strong>Enter Tuition Ledger</strong>. Inside, use the left-hand menu to move around and <strong>Change role</strong> to come back here.</p>
          {error && <p className="landing-error" role="alert">{error}</p>}
          <button className="enter-button" type="submit">Enter Tuition Ledger <Icon name="arrowUp"/></button>
        </form>
      </section>
    </main>
    <footer className="landing-footer"><span>TUITION LEDGER <Icon name="sparkle"/> STUDENT FINANCE, MADE CLEAR</span><a href="#top">BACK TO TOP <Icon name="arrowTop"/></a></footer>
  </div>;
}
