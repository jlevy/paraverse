import puppeteer from 'puppeteer-core';
import fs from 'node:fs/promises';
import path from 'node:path';
const root=path.resolve(import.meta.dirname,'../..');
const env=await fs.readFile(path.join(root,'.env'),'utf8');
const endpoint=env.match(/^BRIGHT_DATA_BROWSER_WS=(.+)$/m)?.[1]?.trim();
const out=path.join(root,'work/data/attendee-contacts');await fs.mkdir(out,{recursive:true});
const targets=[['technotimlive','https://shop.technotim.com/policies/terms-of-service'],['rishabincloud','https://rishabkumar.com/'],['scottsauber','https://scottsauber.com/about/'],['jessehouwing','https://jessehouwing.net/']];
for(const [handle,url] of targets){
 const file=path.join(out,handle+'-public-page.json');try{await fs.access(file);console.log(handle,'cached');continue}catch{}
 let browser,timer,bytes=0,requests=0;const result={handle,source_url:url,retrieval_method:'Bright Data Browser API',checked_at:new Date().toISOString(),constraints:{maxObservedBytes:5000000,maxRequests:100,maxSeconds:45,blockMedia:true},note:'Observed transfer is not a provider billing measurement.'};
 try{
  browser=await puppeteer.connect({browserWSEndpoint:endpoint,protocolTimeout:30000});timer=setTimeout(()=>browser.close().catch(()=>{}),45000);
  const p=await browser.newPage();const c=await p.createCDPSession();await c.send('Network.enable');
  c.on('Network.dataReceived',e=>{bytes+=e.encodedDataLength||e.dataLength||0;if(bytes>5000000)browser.close().catch(()=>{});});
  await p.setRequestInterception(true);p.on('request',r=>{requests++;if(requests>100||['image','media','font'].includes(r.resourceType()))r.abort().catch(()=>{});else r.continue().catch(()=>{});});
  await p.goto(url,{waitUntil:'domcontentloaded',timeout:30000});
  Object.assign(result,await p.evaluate(()=>({resolved_url:location.href,title:document.title,text:document.body.innerText,mailto:[...document.querySelectorAll('a[href^="mailto:"]')].map(a=>({href:a.getAttribute('href'),label:a.innerText})),contact_links:[...document.querySelectorAll('a[href]')].filter(a=>/contact|about|business/i.test(a.innerText)).map(a=>({text:a.innerText,url:a.href}))})));
  result.status='saved';console.log(handle,JSON.stringify({mailto:result.mailto,emails:result.text.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi),contact_links:result.contact_links}));
 }catch(e){result.status='failed';result.error=String(e.message).replaceAll(endpoint,'[redacted]').replace(/brd-customer-[^\s"']+/g,'[redacted]').slice(0,300);console.log(handle,result.status);}
 finally{clearTimeout(timer);await browser?.close().catch(()=>{});result.observed_bytes=bytes;result.requests=requests;await fs.writeFile(file,JSON.stringify(result,null,2));}
}
