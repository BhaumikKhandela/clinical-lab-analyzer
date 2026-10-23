/** Static integration checks; never calls a backend or bypasses a real session. */
import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const server=await createServer({root,server:{middlewareMode:true,ws:false},appType:'custom'});
const memory=new Map();
globalThis.window={localStorage:{getItem:k=>memory.get(k)??null,setItem:(k,v)=>memory.set(k,v),removeItem:k=>memory.delete(k)}};
try {
  const {default:App}=await server.ssrLoadModule('/src/App.jsx');
  const auth=await server.ssrLoadModule('/src/auth.js');
  const signedOut=renderToStaticMarkup(React.createElement(App));
  assert.ok(signedOut.includes('Sign in to your workspace'));
  assert.ok(!signedOut.includes('health-nav-item'));
  auth.startSession({token:'isolated-layout-verification',username:'UI validation',role:'ADMIN'});
  const shell=renderToStaticMarkup(React.createElement(App));
  for(const label of ['Report library','Save a report','Save an image','Share a report','Manage accounts','Sign out','Choose a PDF','Enter values manually']) assert.ok(shell.includes(label),label);
  assert.ok(shell.includes('hidden=""'),'Inactive views must remain hidden');
  const {default:Results}=await server.ssrLoadModule('/src/components/ResultsDisplay.jsx');
  const data={summary:{critical:1,warning:0,normal:1,unknown:0},results:{critical:[{test_name:'Synthetic Assay A',value:4,unit:'U/L',status:'Critical',reference_range:'10-20 U/L',explanation:'Synthetic source explanation.',next_steps:'Synthetic next step.',sources:[{title:'Fixture source',url:'https://example.invalid/source'}]}],normal:[{test_name:'Synthetic Assay B',value:15,unit:'U/L',status:'Normal',reference_range:'10-20 U/L'}]},errors:[]};
  const findings=renderToStaticMarkup(React.createElement(Results,{data,reportName:'Layout fixture — not patient data'}));
  for(const value of ['Synthetic Assay A','4','U/L','10-20','Synthetic source explanation.','Synthetic next step.','Fixture source','Filter findings']) assert.ok(findings.includes(value),value);
  const {default:Chat}=await server.ssrLoadModule('/src/components/ChatPanel.jsx');
  const chat=renderToStaticMarkup(React.createElement(Chat,{threadId:'isolated-layout-fixture'}));
  assert.ok(chat.includes('Discuss this report')&&chat.includes('inert=""'));
  assert.equal(renderToStaticMarkup(React.createElement(Chat,{})),'');
  for(const name of ['Evaluations.jsx','Evaluations.css']){
    const previous=execFileSync('git',['show',`HEAD:frontend/src/${name}`],{cwd:root,encoding:'utf8'});
    assert.equal(await readFile(path.join(root,'src',name),'utf8'),previous,`Evaluation Studio must remain unchanged: ${name}`);
  }
  if(process.argv.includes('--snapshots')){
    const html=body=>`<!doctype html><html><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/><link rel="stylesheet" href="/src/App.css"/></head><body style="margin:0"><p style="position:fixed;z-index:1000;bottom:0;left:0;font:10px sans-serif;background:#fff;padding:4px">ISOLATED LAYOUT TEST — NOT A LIVE PATIENT SESSION</p>${body}</body></html>`;
    await writeFile(path.join(root,'.ui-review.html'),html(shell));
    await writeFile(path.join(root,'.ui-report-review.html'),html(`<div class="app"><main class="app__main">${findings}</main></div>`));
  }
  console.log('UI checks passed: signed-out/access gating, authenticated navigation, mounted views, source findings, chat state, Evaluation Studio unchanged.');
}finally{delete globalThis.window;await server.close();}
