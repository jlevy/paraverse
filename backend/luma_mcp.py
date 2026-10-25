"""Authenticated Streamable HTTP MCP client with explicit side-effect boundaries."""
import hashlib
import json
import threading
import urllib.error
import urllib.request

from luma_oauth import access_token

PROTOCOL_VERSION = '2025-03-26'
_READ_ONLY = {'get_event', 'list_calendars', 'list_events', 'search_events'}
_ALLOWED = _READ_ONLY | {'create_event', 'invite_guests'}


class _MCPClient:
    def __init__(self):
        self.lock = threading.Lock()
        self.token_fingerprint = None
        self.session_id = None
        self.initialized = False
        self.request_id = 0

    @staticmethod
    def _result(message, request_id):
        if not isinstance(message, dict) or message.get('id') != request_id:
            raise ValueError('Luma returned an unrelated MCP response.')
        if 'error' in message or not isinstance(message.get('result'), dict):
            raise ValueError('Luma could not complete this operation.')
        return message['result']

    def _post(self, token, method, params=None, *, notification=False):
        payload = {'jsonrpc': '2.0', 'method': method}
        if params is not None:
            payload['params'] = params
        if not notification:
            self.request_id += 1
            payload['id'] = self.request_id
        headers = {
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/event-stream',
            'MCP-Protocol-Version': PROTOCOL_VERSION,
        }
        if self.session_id is not None:
            headers['Mcp-Session-Id'] = self.session_id
        request = urllib.request.Request('https://mcp.luma.com', data=json.dumps(payload).encode(), headers=headers)
        with urllib.request.urlopen(request, timeout=60) as response:
            if notification:
                if response.status != 202:
                    raise ValueError('Luma did not accept MCP initialization.')
                return None
            if method == 'initialize':
                session_id = response.headers.get('Mcp-Session-Id')
                if session_id is not None and (not session_id or any(not 0x21 <= ord(c) <= 0x7e for c in session_id)):
                    raise ValueError('Luma returned an invalid MCP session.')
                self.session_id = session_id
            if response.headers.get('Content-Type', '').split(';')[0].strip() == 'text/event-stream':
                # Process complete events as they arrive; a stream need not close after its response.
                data, size = [], 0
                for raw_line in response:
                    size += len(raw_line)
                    if size > 8 * 1024 * 1024:
                        raise ValueError('Luma returned an oversized MCP response.')
                    line = raw_line.decode().rstrip('\r\n')
                    if line.startswith('data:'):
                        data.append(line[5:].removeprefix(' '))
                    elif not line and data:
                        message = json.loads('\n'.join(data))
                        data = []
                        if isinstance(message, dict) and message.get('id') == payload['id']:
                            return self._result(message, payload['id'])
                raise ValueError('Luma did not return the requested MCP response.')
            body = response.read(8 * 1024 * 1024 + 1)
            if len(body) > 8 * 1024 * 1024:
                raise ValueError('Luma returned an oversized MCP response.')
            return self._result(json.loads(body), payload['id'])

    def _initialize(self, token):
        self.initialized = False
        self.session_id = None
        try:
            result = self._post(token, 'initialize', {
                'protocolVersion': PROTOCOL_VERSION, 'capabilities': {},
                'clientInfo': {'name': 'Paraverse', 'version': '1.0.0'},
            })
            if result.get('protocolVersion') != PROTOCOL_VERSION:
                raise ValueError('Luma negotiated an unsupported MCP protocol.')
            self._post(token, 'notifications/initialized', notification=True)
            self.initialized = True
        except Exception:
            self.session_id = None
            raise

    def call(self, method, params=None):
        with self.lock:
            token = access_token()
            fingerprint = hashlib.sha256(token.encode()).digest()
            if fingerprint != self.token_fingerprint:
                self.initialized = False
                self.session_id = None
                self.token_fingerprint = fingerprint
            if not self.initialized:
                self._initialize(token)
            try:
                return self._post(token, method, params or {})
            except urllib.error.HTTPError as error:
                if error.code != 404 or self.session_id is None:
                    raise
                # A session-specific 404 definitively expires the session. Reconnect,
                # but never replay event creation or invitations: delivery is uncertain.
                self._initialize(token)
                if method == 'tools/call' and (params or {}).get('name') in _READ_ONLY:
                    return self._post(token, method, params)
                raise ValueError('Luma session expired. Check the operation in Luma before trying again.') from error


_client = _MCPClient()


def call(method, params=None):
    return _client.call(method, params)


def tool(name, arguments):
    if name not in _ALLOWED:
        raise ValueError('Unsupported Luma operation.')
    result = call('tools/call', {'name': name, 'arguments': arguments})
    if result.get('isError'):
        raise ValueError('Luma rejected the event operation.')
    if result.get('structuredContent'):
        return result['structuredContent']
    return json.loads(next(c['text'] for c in result.get('content', []) if c.get('type') == 'text'))
