"""Conference retrieval pins checked DNS answers and retains HTTPS verification."""
import io
import urllib.error
import urllib.request
from email.message import Message
import socket
import ssl
import unittest
from unittest.mock import patch
import conference_service

PUBLIC_IP='93.184.216.34'


def addresses(ip):
 return [(socket.AF_INET,socket.SOCK_STREAM,socket.IPPROTO_TCP,'',(ip,443))]


def wire(body=b'<html>'+b'Conference program details. '*8+b'</html>',status='200 OK',headers='Content-Type: text/html\r\n'):
 return ('HTTP/1.1 '+status+'\r\n'+headers+'Content-Length: '+str(len(body))+'\r\n\r\n').encode()+body


class ConferenceTransportTests(unittest.TestCase):
 def fetch(self,responses,dns,proxies=None):
  self.connected=[];self.sent=[];self.tls=[];self.timeouts=[]
  owner=self
  class Socket:
   def settimeout(self,value):owner.timeouts.append(value)
   def setsockopt(self,*args):pass
   def connect(self,address):owner.connected.append(address)
   def sendall(self,data):owner.sent.append(data)
   def makefile(self,*args):return io.BytesIO(responses.pop(0))
   def close(self):pass
  def wrap(context,sock,*,server_hostname):
   owner.tls.append((server_hostname,context.check_hostname,context.verify_mode));return sock
  with patch('socket.getaddrinfo',side_effect=dns),patch('socket.socket',side_effect=lambda *args:Socket()),patch.object(ssl.SSLContext,'wrap_socket',wrap),patch('urllib.request.getproxies',return_value=proxies or {}):
   return conference_service.fetch_page(dict(url='https://public.example/page',title='Synthetic conference'))

 def test_dns_rebinding_cannot_change_checked_socket_or_tls_identity(self):
  lookups=[]
  def resolve(host,port,*args,**kwargs):
   lookups.append(host);return addresses(PUBLIC_IP if len(lookups)==1 else '127.0.0.1')
  result=self.fetch([wire()],resolve)
  self.assertEqual(self.connected,[(PUBLIC_IP,443)])
  self.assertEqual(lookups,['public.example'])
  self.assertEqual(self.tls,[('public.example',True,ssl.CERT_REQUIRED)])
  self.assertIn(b'Host: public.example\r\n',self.sent[0])
  self.assertNotIn(PUBLIC_IP.encode(),self.sent[0])
  self.assertEqual(result['resolvedURL'],'https://public.example/page')
  self.assertEqual(self.timeouts,[25])

 def test_private_redirect_is_rejected_before_another_socket(self):
  def resolve(host,port,*args,**kwargs):return addresses('169.254.169.254' if host=='metadata.example' else PUBLIC_IP)
  with self.assertRaises(ValueError):self.fetch([wire(b'','302 Found','Location: https://metadata.example/latest\r\n')],resolve)
  self.assertEqual(self.connected,[(PUBLIC_IP,443)])

 def test_redirect_revalidates_same_hostname_dns(self):
  lookups=[]
  def resolve(host,port,*args,**kwargs):
   lookups.append(host);return addresses(PUBLIC_IP if len(lookups)==1 else '127.0.0.1')
  with self.assertRaises(ValueError):self.fetch([wire(b'','302 Found','Location: /next\r\n')],resolve)
  self.assertEqual(self.connected,[(PUBLIC_IP,443)])
  self.assertEqual(lookups,['public.example','public.example'])

 def test_existing_page_type_and_body_limits_remain(self):
  for response in (wire(b'{}',headers='Content-Type: application/json\r\n'),wire(b'x'*2000001)):
   with self.subTest(size=len(response)):
    with self.assertRaises(ValueError):self.fetch([response],lambda *args,**kwargs:addresses(PUBLIC_IP))

 def test_public_redirect_pins_each_new_destination_and_preserves_host(self):
  lookups=[]
  def resolve(host,port,**kwargs):
   lookups.append(host);return addresses(PUBLIC_IP if host=='public.example' else '1.1.1.1')
  result=self.fetch([wire(b'','302 Found','Location: https://other.example/final\r\n'),wire()],resolve,proxies={'https':'http://127.0.0.1:3128'})
  self.assertEqual(lookups,['public.example','other.example'])
  self.assertEqual(self.connected,[(PUBLIC_IP,443),('1.1.1.1',443)])
  self.assertEqual(self.tls,[('public.example',True,ssl.CERT_REQUIRED),('other.example',True,ssl.CERT_REQUIRED)])
  self.assertIn(b'Host: other.example\r\n',self.sent[1])
  self.assertEqual(result['resolvedURL'],'https://other.example/final')

 def test_redirect_credentials_are_dropped_and_loops_are_bounded(self):
  import conference_http
  requests=[];redirects=[];final=object()
  def next_hop(request,*args):
   requests.append(request)
   if len(requests)==3:return final
   headers=Message();headers['Location']='/same' if len(requests)==1 else 'https://other.example/final'
   body=io.BytesIO();redirects.append(body)
   raise urllib.error.HTTPError(request.full_url,302,'redirect',headers,body)
  request=urllib.request.Request('https://public.example/start',headers={'Authorization':'synthetic','Cookie':'synthetic','X-Api-Key':'synthetic','Proxy-Authorization':'synthetic','Host':'wrong.example','User-Agent':'test','Accept':'text/html'})
  with patch('conference_http.socket.getaddrinfo',return_value=addresses(PUBLIC_IP)),patch('conference_http._open_once',side_effect=next_hop):
   self.assertIs(conference_http.open_public_url(request,timeout=1),final)
  self.assertTrue(all({k.lower():v for k,v in r.headers.items()}=={'user-agent':'test','accept':'text/html'} for r in requests))
  self.assertTrue(all(body.closed for body in redirects))
  requests.clear()
  def loop(request,*args):
   requests.append(request);headers=Message();headers['Location']='/loop'
   raise urllib.error.HTTPError(request.full_url,302,'redirect',headers,io.BytesIO())
  with patch('conference_http.socket.getaddrinfo',return_value=addresses(PUBLIC_IP)),patch('conference_http._open_once',side_effect=loop):
   with self.assertRaises(conference_http.UnsafeDestination):conference_http.open_public_url(request,timeout=1)
  self.assertEqual(len(requests),conference_http.MAX_REDIRECTS+1)

 def test_unsafe_initial_forms_and_https_downgrades_never_open_private_socket(self):
  import conference_http
  urls=['https://127.0.0.1/','https://169.254.169.254/','https://[::1]/','https://[::ffff:127.0.0.1]/','https://[64:ff9b::a00:1]/','https://localhost./','https://public.example@other.example/','https://%31%32%37.0.0.1/','https://public.example:8080/','http://public.example/','https://mixed.example/']
  with patch('conference_http.socket.getaddrinfo',return_value=addresses(PUBLIC_IP)+addresses('10.0.0.1')),patch('conference_http._open_once') as opened:
   for url in urls:
    with self.subTest(url=url):
     with self.assertRaises(conference_http.UnsafeDestination):conference_http.open_public_url(urllib.request.Request(url),timeout=1)
   opened.assert_not_called()
  with self.assertRaises(ValueError):self.fetch([wire(b'','302 Found','Location: http://public.example/plain\r\n')],lambda *args,**kwargs:addresses(PUBLIC_IP))
  self.assertEqual(self.connected,[(PUBLIC_IP,443)])
