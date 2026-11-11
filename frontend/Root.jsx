import React, { useState } from 'react';
import App from './App.jsx';
import Landing from './features/landing/Landing.jsx';

export default function Root() {
  const [entry, setEntry] = useState(null);
  return entry ? <App role={entry.role} studentId={entry.studentId} onChangeRole={()=>{setEntry(null);window.scrollTo(0,0);}}/> : <Landing onEnter={setEntry}/>;
}
