import puppeteer from 'puppeteer-core';
import fs from 'node:fs/promises';
const out=new URL('../../work/data/official/speaker-photos/',import.meta.url);await fs.mkdir(out,{recursive:true});
const browser=await puppeteer.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
try {
 const page=await browser.newPage(); const pending=[];const network=[];
 page.on('response',r=>{if(/json/i.test(r.headers()['content-type']||''))pending.push((async()=>{try{const body=await r.json();network.push({url:r.url(),request:r.request().postData(),body});}catch{}})());});
 await page.goto('https://reg.githubuniverse.com/flow/github/universe26/attendee-portal/page/speakers',{waitUntil:'networkidle2',timeout:60000});
 await new Promise(r=>setTimeout(r,4000));
 await fs.writeFile(new URL('speakers-rendered.html',out),await page.content());
 console.log((await page.evaluate(()=>document.body.innerText)).slice(0,6500));
 console.log('BUTTONS',await page.$$eval('button',els=>els.map(x=>x.innerText)));
 await Promise.allSettled(pending);await fs.writeFile(new URL('source-responses.json',out),JSON.stringify(network,null,2));
 console.log('RESPONSES',network.map(x=>({url:x.url,keys:Object.keys(x.body)})));
}finally{await browser.close()}
