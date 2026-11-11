import React from 'react';

const paths = {
  arrowUp: <><path d="M5 19 19 5M7 5h12v12"/></>,
  arrowDown: <><path d="M12 3v17M5 13l7 7 7-7"/></>,
  arrowRight: <><path d="M4 12h16M13 5l7 7-7 7"/></>,
  arrowTop: <><path d="M12 21V4M5 11l7-7 7 7"/></>,
  check: <path d="m5 12 5 5L20 7"/>,
  sparkle: <><path d="M12 2.5 13.8 9l6.7 3-6.7 2.8L12 21.5l-1.8-6.7L3.5 12l6.7-3L12 2.5Z"/><path d="M19 2v4M17 4h4"/></>,
};

export default function Icon({ name, className = '' }) {
  return <svg className={`icon ${className}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">{paths[name]}</svg>;
}
