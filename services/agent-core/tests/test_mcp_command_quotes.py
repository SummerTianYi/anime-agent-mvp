"""Codex: portable paths must retain spaces, Unicode and empty arguments."""
import asyncio
import os
import unittest
from unittest.mock import patch

from agent_core.mcp_host import McpHost, McpServer


class McpQuotedCommandTests(unittest.TestCase):
    def parsed(self, command):
        host = McpHost()
        async def start(server):
            server.started = True
        with patch.dict(os.environ, {"ANIME_AGENT_MCP_SERVERS": "fixture="+command}), patch.object(McpServer, "start", start):
            asyncio.run(host.start_from_env())
        return host.servers["fixture"].command

    def test_quoted_portable_executable_and_script(self):
        self.assertEqual(self.parsed('"C:/Test Folder/node.exe" "D:/天依 测试/server.js" --isolated'),
                         ['C:/Test Folder/node.exe', 'D:/天依 测试/server.js', '--isolated'])

    def test_empty_argument_preserved(self):
        self.assertEqual(self.parsed('"C:/Test/node.exe" server.js ""'),
                         ['C:/Test/node.exe', 'server.js', ''])

    def test_existing_unquoted_command_unchanged(self):
        self.assertEqual(self.parsed('C:/Test/node.exe server.js --isolated'),
                         ['C:/Test/node.exe', 'server.js', '--isolated'])

    @unittest.skipUnless(os.name == 'nt', 'Windows command-line escaping')
    def test_backslashes_are_not_posix_escapes(self):
        self.assertEqual(self.parsed(r'"C:\Test Folder\node.exe" "D:\天依\server.js"'),
                         [r'C:\Test Folder\node.exe', r'D:\天依\server.js'])


if __name__ == '__main__':
    unittest.main()
