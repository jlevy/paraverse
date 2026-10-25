import puppeteer from 'puppeteer-core';
import fs from 'node:fs/promises';
import path from 'node:path';
const root=path.resolve(import.meta.dirname,'../..');
const env=await fs.readFile(path.join(root,'.env'),'utf8');
const endpoint=env.match(/^BRIGHT_DATA_BROWSER_WS=(.+)$/m)?.[1]?.trim();
if(!endpoint) throw new Error('Browser API connection is not configured');
const out=path.join(root,'work/data/profiles/sam-lambert/browser-test');
await fs.mkdir(out,{recursive:true});
let browser, traffic=0, requests=0, timer, stopped=false;
const result={retrieval_method:'Bright Data Browser API / Puppeteer',source_url:'https://x.com/samlambert',started_at:new Date().toISOString(),posts:[],constraints:{oneNavigation:true,maxRequests:500,maxObservedBytes:10000000,maxSessionSeconds:45,blockMedia:true},note:'Observed response bytes are not a billing measurement.'};
async function stop(reason){ if(stopped)return; stopped=true;result.stop_reason=reason;try{await browser?.close()}catch{} }
try {
 console.log('Connecting to Bright Data Browser API…');
 browser=await puppeteer.connect({browserWSEndpoint:endpoint,protocolTimeout:30000});
 timer=setTimeout(()=>stop('45-second safety cutoff'),45000);
 const page=await browser.newPage();
 const cdp=await page.createCDPSession();
 await cdp.send('Network.enable');
 cdp.on('Network.dataReceived',e=>{traffic+=e.encodedDataLength||e.dataLength||0;if(traffic>10000000)void stop('Observed traffic cutoff');});
 await page.setRequestInterception(true);
 page.on('request',r=>{
   requests++;
   if(requests>500){void r.abort().catch(()=>{});void stop('Request count cutoff');return;}
   if(['image','media','font'].includes(r.resourceType()))void r.abort().catch(()=>{});
   else void r.continue().catch(()=>{});
 });
 await page.goto(result.source_url,{waitUntil:'domcontentloaded',timeout:25000});
 console.log('Profile page opened; checking rendered text…');
 await new Promise(r=>setTimeout(r,5000));
 const seen=new Map();
 for(let i=0;i<3&&!stopped;i++){
   const rendered=await page.evaluate(()=>({url:location.href,title:document.title,text:document.body.innerText,posts:Array.from(document.querySelectorAll('article')).map(e=>({text:e.innerText,url:e.querySelector('a[href*="/status/"]')?.href,date:e.querySelector('time')?.dateTime}))}));
   result.page_url=rendered.url;result.page_title=rendered.title;result.page_text=rendered.text.slice(0,35000);
   for(const p of rendered.posts)seen.set(p.url||p.text,p);
   result.posts=[...seen.values()];
   if(!rendered.posts.length)break;
   await page.evaluate(()=>window.scrollBy(0,1200));
   await new Promise(r=>setTimeout(r,1500));
 }
 await page.screenshot({path:path.join(out,'page.png')}).catch(()=>{});
 result.status='completed';
} catch(e){result.status='failed';result.error=String(e.message).replaceAll(endpoint,'[connection]').replace(/brd-customer-[^\s"']+/g,'[connection]').slice(0,500);}
finally{clearTimeout(timer);await stop(result.stop_reason||'Test complete');result.observed_response_bytes=traffic;result.request_count=requests;result.finished_at=new Date().toISOString();await fs.writeFile(path.join(out,'result.json'),JSON.stringify(result,null,2));console.log(JSON.stringify({status:result.status,posts:result.posts.length,requests,observedBytes:traffic,error:result.error,stop:result.stop_reason,pageText:result.page_text?.slice(0,1500)},null,2));}
