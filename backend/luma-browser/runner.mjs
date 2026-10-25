import { chromium } from 'playwright';
import { createInterface } from 'node:readline';
import { mkdirSync } from 'node:fs';
import { homedir } from 'node:os';
const dir = `${homedir()}/Library/Application Support/CommonGround/LumaBrowser`;
mkdirSync(dir, {recursive:true, mode:0o700});
let context;
async function page() {
  if (!context) {
    context = await chromium.launchPersistentContext(dir, {channel:'chrome',headless:false,viewport:null,args:['--no-first-run']});
    context.on('close',()=>{context=undefined});
  }
  return context.pages().find(p=>new URL(p.url()).hostname==='luma.com') || await context.newPage();
}
for await (const line of createInterface({input:process.stdin})) {
 try {
  const cmd=JSON.parse(line); const p=await page();
  if(cmd.action==='open') {await p.goto('https://luma.com/create'); await p.bringToFront(); console.log(JSON.stringify({status:'login',message:'Sign in to Luma in the Paraverse browser, then return here.'}));}
  else {console.log(JSON.stringify({status:'blocked',message:'Luma form setup is awaiting sign-in verification. No event was created.'}));}
 } catch(e) {console.log(JSON.stringify({status:'error',message:'Could not open Luma. Close other Paraverse Luma browser windows and retry.'}));}
}
