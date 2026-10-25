import importlib
import io
import json
import unittest
import urllib.error
from unittest.mock import patch

import luma_mcp


class Response(io.BytesIO):
    def __init__(self, payload=None, *, session=None, sse=None, status=200):
        super().__init__((sse if sse is not None else json.dumps(payload or {})).encode())
        self.headers = {'Content-Type': 'text/event-stream' if sse is not None else 'application/json'}
        if session is not None:
            self.headers['Mcp-Session-Id'] = session
        self.status = status


class MCPTransportTests(unittest.TestCase):
    def setUp(self):
        importlib.reload(luma_mcp)
        self.calls = []
        self.token = patch.object(luma_mcp, 'access_token', return_value='synthetic-token')
        self.token.start()
        self.addCleanup(self.token.stop)

    def server(self, req, timeout):
        message = json.loads(req.data)
        self.calls.append((message, dict((key.lower(), value) for key, value in req.header_items())))
        if message['method'] == 'initialize':
            return Response({'jsonrpc': '2.0', 'id': message['id'], 'result': {
                'protocolVersion': '2025-03-26', 'capabilities': {'tools': {}},
                'serverInfo': {'name': 'Synthetic MCP', 'version': '1'}}}, session='session-one')
        if message['method'] == 'notifications/initialized':
            return Response(status=202)
        self.assertEqual([entry[0]['method'] for entry in self.calls[:2]],
                         ['initialize', 'notifications/initialized'])
        return Response({'jsonrpc': '2.0', 'id': message['id'], 'result': {
            'structuredContent': {'ok': True}}})

    def test_initializes_then_reuses_authenticated_session(self):
        with patch.object(luma_mcp.urllib.request, 'urlopen', side_effect=self.server):
            self.assertEqual(luma_mcp.tool('list_events', {}), {'ok': True})
            luma_mcp.tool('get_event', {'id': 'synthetic'})
        self.assertEqual([c[0]['method'] for c in self.calls],
                         ['initialize', 'notifications/initialized', 'tools/call', 'tools/call'])
        params = self.calls[0][0]['params']
        self.assertEqual(params['protocolVersion'], '2025-03-26')
        self.assertEqual(params['capabilities'], {})
        self.assertTrue(params['clientInfo']['name'])
        self.assertTrue(params['clientInfo']['version'])
        self.assertNotIn('mcp-session-id', self.calls[0][1])
        self.assertNotIn('id', self.calls[1][0])
        for _, headers in self.calls[1:]:
            self.assertEqual(headers['mcp-session-id'], 'session-one')
            self.assertEqual(headers['mcp-protocol-version'], '2025-03-26')
        ids = [c[0]['id'] for c in self.calls if 'id' in c[0]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_stateless_server_still_gets_initialization(self):
        def server(req, timeout):
            response = self.server(req, timeout)
            response.headers.pop('Mcp-Session-Id', None)
            return response
        with patch.object(luma_mcp.urllib.request, 'urlopen', side_effect=server):
            luma_mcp.tool('list_events', {})
        self.assertEqual(self.calls[0][0]['method'], 'initialize')
        self.assertTrue(all('mcp-session-id' not in headers for _, headers in self.calls))

    def test_expired_session_reinitializes_and_retries_read_only_once(self):
        failed = False
        def server(req, timeout):
            nonlocal failed
            message = json.loads(req.data)
            if message['method'] == 'tools/call' and not failed:
                failed = True
                self.calls.append((message, dict((k.lower(), v) for k, v in req.header_items())))
                raise urllib.error.HTTPError(req.full_url, 404, 'Expired', {}, None)
            return self.server(req, timeout)
        with patch.object(luma_mcp.urllib.request, 'urlopen', side_effect=server):
            self.assertEqual(luma_mcp.tool('list_events', {}), {'ok': True})
        self.assertEqual([c[0]['method'] for c in self.calls], [
            'initialize', 'notifications/initialized', 'tools/call',
            'initialize', 'notifications/initialized', 'tools/call'])
        self.assertNotIn('mcp-session-id', self.calls[3][1])

    def test_side_effect_tools_never_replayed_after_expiry_timeout_or_server_error(self):
        for name in ['create_event', 'invite_guests']:
            for failure in [404, 503, 'timeout']:
                with self.subTest(name=name, failure=failure):
                    self.setUp()
                    def server(req, timeout):
                        message = json.loads(req.data)
                        if message['method'] == 'tools/call':
                            self.calls.append((message, {}))
                            if failure == 'timeout':
                                raise TimeoutError('Synthetic interrupted delivery')
                            raise urllib.error.HTTPError(req.full_url, failure, 'Synthetic failure', {}, None)
                        return self.server(req, timeout)
                    with patch.object(luma_mcp.urllib.request, 'urlopen', side_effect=server):
                        with self.assertRaises((ValueError, TimeoutError, urllib.error.HTTPError)):
                            luma_mcp.tool(name, {})
                    self.assertEqual(sum(c[0]['method'] == 'tools/call' for c in self.calls), 1)
                    self.assertEqual(self.calls[0][0]['method'], 'initialize')

    def test_new_token_does_not_reuse_old_session(self):
        with patch.object(luma_mcp.urllib.request, 'urlopen', side_effect=self.server):
            luma_mcp.tool('list_events', {})
            luma_mcp.access_token.return_value = 'another-synthetic-token'
            luma_mcp.tool('list_events', {})
        self.assertEqual(sum(c[0]['method'] == 'initialize' for c in self.calls), 2)
        self.assertNotIn('mcp-session-id', self.calls[3][1])

    def test_unsupported_protocol_prevents_tool_execution(self):
        def server(req, timeout):
            message = json.loads(req.data)
            self.calls.append((message, {}))
            return Response({'jsonrpc': '2.0', 'id': message['id'], 'result': {
                'protocolVersion': 'unsupported', 'capabilities': {}}})
        with patch.object(luma_mcp.urllib.request, 'urlopen', side_effect=server):
            with self.assertRaises(ValueError):
                luma_mcp.tool('create_event', {})
        self.assertEqual([c[0]['method'] for c in self.calls], ['initialize'])

    def test_sse_ignores_notifications_and_other_request_ids(self):
        def server(req, timeout):
            message = json.loads(req.data)
            if message['method'] != 'tools/call':
                return self.server(req, timeout)
            self.calls.append((message, {}))
            events = [
                {'jsonrpc': '2.0', 'method': 'notifications/progress'},
                {'jsonrpc': '2.0', 'id': 'other', 'result': {}},
                {'jsonrpc': '2.0', 'id': message['id'], 'result': {'structuredContent': {'ok': True}}},
            ]
            return Response(sse=''.join('event: message\ndata: ' + json.dumps(event) + '\n\n' for event in events))
        with patch.object(luma_mcp.urllib.request, 'urlopen', side_effect=server):
            self.assertEqual(luma_mcp.tool('get_event', {}), {'ok': True})

    def test_mismatched_response_id_is_not_success(self):
        def server(req, timeout):
            message = json.loads(req.data)
            if message['method'] != 'tools/call':
                return self.server(req, timeout)
            return Response({'jsonrpc': '2.0', 'id': 'wrong', 'result': {'structuredContent': {'ok': True}}})
        with patch.object(luma_mcp.urllib.request, 'urlopen', side_effect=server):
            with self.assertRaises(ValueError):
                luma_mcp.tool('create_event', {})


if __name__ == '__main__':
    unittest.main()
