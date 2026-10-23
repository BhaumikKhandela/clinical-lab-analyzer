const paths = {
  overview: 'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
  report: 'M14 2H5v20h14V7z M14 2v6h5 M8 12h8 M8 16h6',
  upload: 'M12 16V3 M7 8l5-5 5 5 M4 15v6h16v-6',
  person: 'M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0 M4 22v-3a8 8 0 0 1 16 0v3',
  image: 'M3 3h18v18H3z M3 17l6-6 5 5 3-3 4 4 M17 7h.01',
  send: 'M22 2 9 15 M22 2l-8 20-5-7-7-5z',
  chat: 'M21 11a9 9 0 0 1-9 9H3l2-5a9 9 0 1 1 16-4 M8 10h8 M8 14h5',
  arrow: 'M4 12h16 M14 6l6 6-6 6',
  plus: 'M12 5v14 M5 12h14',
  chevron: 'm6 9 6 6 6-6',
  check: 'm5 12 4 4L19 6',
  logout: 'M9 3H3v18h6 M8 12h14 M17 7l5 5-5 5',
  shield: 'm12 2 9 4v6c0 5-9 10-9 10S3 17 3 12V6z M8 12l3 3 5-6',
  close: 'm6 6 12 12 M6 18 18 6',
  clock: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0 M12 6v6l4 2',
};
export default function Icon({name, size=20, ...props}) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}><path d={paths[name] || paths.report}/></svg>;
}
