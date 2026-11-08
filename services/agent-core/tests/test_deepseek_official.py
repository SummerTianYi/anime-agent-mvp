"""Official Flash request controls; synthetic responses, no real credentials."""
import json
import unittest

from agent_core.main import OpenAICompatibleProvider


class OfficialFlashTests(unittest.IsolatedAsyncioTestCase):
    async def request_body(self, base_url, model, with_tools):
        client = OpenAICompatibleProvider(name='deepseek', base_url=base_url,
            model=model, api_key='synthetic-only', timeout_seconds=1)
        requests = []

        def respond(request):
            requests.append(request)
            message = {'role': 'assistant', 'content': '连接正常'}
            if with_tools:
                message = {'role': 'assistant', 'content': None, 'tool_calls': [
                    {'id': 'time-1', 'type': 'function',
                     'function': {'name': 'get_time', 'arguments': '{}'}}]}
            return json.dumps({'choices': [{'message': message}]}).encode()

        client._request = respond
        if with_tools:
            result = await client.complete_with_tools([{'role': 'user', 'content': '时间'}], [])
            self.assertEqual(result['tool_calls'][0]['arguments'], {})
        else:
            self.assertEqual(await client.complete([{'role': 'user', 'content': '你好'}]), '连接正常')
        self.assertEqual(len(requests), 1)
        return json.loads(requests[0].data)

    async def test_official_chat_disables_thinking(self):
        body = await self.request_body('https://api.deepseek.com', 'deepseek-flash', False)
        self.assertEqual(body.get('thinking'), {'type': 'disabled'})

    async def test_official_tool_turn_disables_thinking(self):
        body = await self.request_body('https://api.deepseek.com', 'deepseek-flash', True)
        self.assertEqual(body.get('thinking'), {'type': 'disabled'})

    async def test_other_channels_and_models_preserve_payload(self):
        for base_url, model in [('https://chatapi.weixin.qq.com/openai/v1', 'Deepseek-v4-flash'),
                                ('https://chatapi.weixin.qq.com/openai/v1', 'GLM-5.2'),
                                ('https://api.deepseek.com', 'deepseek-chat'),
                                ('https://api.deepseek.com.example.invalid', 'deepseek-flash')]:
            for with_tools in (False, True):
                with self.subTest(base_url=base_url, model=model, with_tools=with_tools):
                    body = await self.request_body(base_url, model, with_tools)
                    self.assertNotIn('thinking', body)
