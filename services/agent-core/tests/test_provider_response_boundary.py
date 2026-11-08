"""Inject network response bytes into actual adapters, then actual chat handling."""
import copy
import json
import unittest

import test_harness_v1_review as fixture


def encode(value):
    return json.dumps(value, ensure_ascii=False).encode('utf-8')


def response(dialect, content=None, calls=()):
    if dialect == 'openai':
        return encode({'choices': [{'message': {'role': 'assistant', 'content': content,
            'tool_calls': [{'id': c['id'], 'type': 'function',
                            'function': {'name': c['name'], 'arguments': c['arguments']}} for c in calls]}}]})
    blocks = [] if content is None else [{'type': 'text', 'text': content}]
    return encode({'content': blocks + [{'type': 'tool_use', 'id': c['id'], 'name': c['name'],
                                         'input': c['arguments']} for c in calls]})


def call(arguments, name='get_time', id='synthetic-call'):
    return {'id': id, 'name': name, 'arguments': arguments}


class ProviderResponseBoundaryTests(fixture.IndependentReviewTests):
    def provider(self, dialect, replies):
        cls = self.core.OpenAICompatibleProvider if dialect == 'openai' else self.core.AnthropicCompatibleProvider
        provider = cls(name='synthetic-' + dialect, base_url='https://example.invalid/v1',
                       model='synthetic', api_key='synthetic-test-key', timeout_seconds=3)
        self.wire_requests = []
        queue = list(replies)

        def wire(request):
            self.wire_requests.append(json.loads(request.data))
            if not queue:
                raise AssertionError('unexpected retry/fallback')
            return queue.pop(0)

        provider._request = wire
        return provider

    async def rejected(self, dialect, raw, tools=True):
        provider = self.provider(dialect, [raw])
        with self.assertRaises(self.core.ProviderError) as raised:
            if tools:
                await provider.complete_with_tools([{'role': 'user', 'content': '合成测试'}], self.core.tools_schema)
            else:
                await provider.complete([{'role': 'user', 'content': '合成测试'}])
        self.assertNotIn('DO_NOT_LEAK', str(raised.exception))
        self.assertNotIn('Traceback', str(raised.exception))
        self.assertEqual(len(self.wire_requests), 1)

    async def test_invalid_bytes_and_top_level_both_adapters_both_methods(self):
        for dialect in ('openai', 'anthropic'):
            for tools in (False, True):
                for raw in (b'', b'\xff', b'{"DO_NOT_LEAK":', b'null', b'[]', b'42', b'{}'):
                    with self.subTest(dialect=dialect, tools=tools, raw=raw):
                        await self.rejected(dialect, raw, tools)

    async def test_openai_message_and_choices_shapes(self):
        payloads = [ {'choices': value} for value in (None, {}, [], 'bad', [None], [{'message': None}],
                     [{'message': []}], [{'message': 'DO_NOT_LEAK'}]) ]
        for payload in payloads:
            for tools in (False, True):
                with self.subTest(payload=payload, tools=tools):
                    await self.rejected('openai', encode(payload), tools)

    async def test_empty_and_bad_text_not_normal_response(self):
        for dialect in ('openai', 'anthropic'):
            for tools in (False, True):
                for content in (None, '', '  ', 7, False, {'text': 'DO_NOT_LEAK'}):
                    with self.subTest(dialect=dialect, tools=tools, content=content):
                        await self.rejected(dialect, response(dialect, content), tools)

    async def test_bad_openai_text_blocks(self):
        for blocks in ([None], ['DO_NOT_LEAK'], [{'text': None}], [{'text': 17}], [{}]):
            for tools in (False, True):
                with self.subTest(blocks=blocks, tools=tools):
                    await self.rejected('openai', response('openai', blocks), tools)

    async def test_bad_anthropic_blocks(self):
        for blocks in (None, {}, 'DO_NOT_LEAK', [None], [7], [{}], [{'type': 'text', 'text': None}],
                       [{'type': 'unknown', 'text': 'DO_NOT_LEAK'}], [{'type': 'thinking', 'thinking': 'internal'}]):
            for tools in (False, True):
                with self.subTest(blocks=blocks, tools=tools):
                    await self.rejected('anthropic', encode({'content': blocks}), tools)

    async def test_invalid_tool_arguments_never_become_empty_object(self):
        for dialect in ('openai', 'anthropic'):
            for arguments in ('{DO_NOT_LEAK', '', 'null', '[]', '[1]', '42', None, [], 7, False,
                              '{"value":NaN}', '{"value":Infinity}', '{"x":1,"x":2}'):
                with self.subTest(dialect=dialect, arguments=arguments):
                    await self.rejected(dialect, response(dialect, calls=[call(arguments)]))

    async def test_bad_tool_envelopes(self):
        for calls in (False, {}, 'DO_NOT_LEAK', [None], [7], [{'id': 'x', 'function': None}],
                      [{'id': 'x', 'function': {'name': 'get_time'}}]):
            with self.subTest(calls=calls):
                await self.rejected('openai', encode({'choices': [{'message': {'content': None, 'tool_calls': calls}}]}))
        for dialect in ('openai', 'anthropic'):
            for bad in (call({}, name=None), call({}, name=4), call({}, name=''), call({}, id=None),
                        call({}, id=7), call({}, id='')):
                with self.subTest(dialect=dialect, bad=bad):
                    await self.rejected(dialect, response(dialect, calls=[bad]))

    async def test_duplicate_call_ids_rejected_before_any_call(self):
        for dialect in ('openai', 'anthropic'):
            with self.subTest(dialect=dialect):
                await self.rejected(dialect, response(dialect, calls=[call({}), call({})]))

    async def test_normal_chat_both_methods(self):
        for dialect in ('openai', 'anthropic'):
            provider = self.provider(dialect, [response(dialect, '收到'), response(dialect, '正常聊天')])
            self.assertEqual(await provider.complete([{'role': 'user', 'content': '你好'}]), '收到')
            result = await provider.complete_with_tools([{'role': 'user', 'content': '你好'}], self.core.tools_schema)
            self.assertEqual(result['content'], '正常聊天')
            self.assertEqual(result['tool_calls'], [])

    async def test_existing_text_blocks_and_thinking_compatible(self):
        samples = [('openai', response('openai', [{'type': 'text', 'text': '第一'}, {'text': '第二'}])),
                   ('anthropic', encode({'content': [{'type': 'thinking', 'thinking': 'internal'},
                       {'type': 'redacted_thinking', 'data': 'opaque'}, {'type': 'text', 'text': '第一'},
                       {'type': 'text', 'text': '第二'}]}))]
        for dialect, raw in samples:
            provider = self.provider(dialect, [raw])
            self.assertEqual(await provider.complete([{'role': 'user', 'content': '你好'}]), '第一第二')

    async def test_empty_body_valid_zero_argument_tool_is_normal(self):
        for dialect in ('openai', 'anthropic'):
            for args in ({}, '{}'):
                provider = self.provider(dialect, [response(dialect, calls=[call(args)])])
                result = await provider.complete_with_tools([{'role': 'user', 'content': '时间'}], self.core.tools_schema)
                self.assertEqual(result['content'], '')
                self.assertEqual(result['tool_calls'], [call({})])
                self.assertEqual(len(self.wire_requests), 1)

    async def test_handle_chat_bad_response_no_new_action_no_fallback(self):
        for dialect in ('openai', 'anthropic'):
            self.core.provider = self.provider(dialect, [b'\xff'])
            before = copy.deepcopy(self.book.records)
            await self.chat('请调用工具处理合成任务', 'bad-' + dialect)
            self.assertEqual(self.book.records, before)
            self.assertEqual(self.effects, [])
            self.assertIn('模型答复未能完成', self.latest_reply())
            self.assertNotIn('Mock', self.latest_reply())
            self.assertEqual(len(self.wire_requests), 1)

    async def test_handle_chat_mixed_valid_and_corrupt_batch_no_partial_effect(self):
        for dialect in ('openai', 'anthropic'):
            for broken in ('{bad', [], None):
                self.core.provider = self.provider(dialect, [response(dialect, calls=[
                    call(fixture.SEND_ARGS, 'mcp__fixture__send_email', 'first'), call(broken, id='second')])])
                before = copy.deepcopy(self.book.records)
                await self.chat('请调用工具处理合成任务', f'mixed-{dialect}-{broken}')
                self.assertEqual(self.book.records, before)
                self.assertEqual(self.effects, [])
                self.assertEqual(len(self.wire_requests), 1)
                self.assertIn('模型答复未能完成', self.latest_reply())

    async def test_schema_invalid_tail_prevents_front_half_proposal(self):
        for dialect in ('openai', 'anthropic'):
            self.core.provider = self.provider(dialect, [response(dialect, calls=[
                call(fixture.SEND_ARGS, 'mcp__fixture__send_email', 'first'),
                call({'path': 42, 'content': 'bad'}, 'write_file', 'second')]), response(dialect, fixture._reply('参数有误'))])
            before = copy.deepcopy(self.book.records)
            await self.chat('请调用工具处理合成任务', 'schema-' + dialect)
            self.assertEqual(self.book.records, before)
            self.assertEqual(self.effects, [])

    async def completion_failure(self, dialect, unknown=False):
        self.core.provider = self.provider(dialect, [response(dialect, calls=[
            call(fixture.SEND_ARGS, 'mcp__fixture__send_email')]), b'{broken'])
        await self.chat('请调用合成发送服务', 'propose-' + dialect)
        pending = self.book.pending(self.sid)
        self.assertEqual(len(pending), 1)
        self.assertEqual(self.effects, [])
        if unknown:
            async def uncertain(name, arguments):
                self.effects.append((name, copy.deepcopy(arguments)))
                raise TimeoutError('synthetic lost receipt')
            self.core._execute_authorized_tool = uncertain
        await self.chat('确认', 'confirm-' + dialect, confirmation=self.book.ticket(pending[0]))
        self.assertEqual(len(self.effects), 1)
        self.assertEqual(pending[0]['status'], 'unknown' if unknown else 'succeeded')
        self.assertIn('结果未知' if unknown else '连接器已接受发送', self.latest_reply())
        self.assertNotIn('尚未执行', self.latest_reply())
        self.assertEqual(len(self.wire_requests), 2)
        print('PROVIDER_BOUNDARY_OBSERVATION ' + json.dumps({'case': self._testMethodName,
            'dialect': dialect, 'status': pending[0]['status'], 'effects': len(self.effects),
            'answer': self.latest_reply(), 'wire_requests': len(self.wire_requests)}, ensure_ascii=False))

    async def test_openai_bad_supplement_keeps_success_receipt(self):
        await self.completion_failure('openai')

    async def test_anthropic_bad_supplement_keeps_success_receipt(self):
        await self.completion_failure('anthropic')

    async def test_openai_bad_supplement_keeps_unknown(self):
        await self.completion_failure('openai', unknown=True)

    async def test_anthropic_bad_supplement_keeps_unknown(self):
        await self.completion_failure('anthropic', unknown=True)

    async def test_actual_handle_chat_normal_wire_text(self):
        for dialect in ('openai', 'anthropic'):
            self.core.provider = self.provider(dialect, [response(dialect, json.dumps({
                'decision': {'mode': 'chat'}, 'reply': '你好，来聊音乐吧。'}, ensure_ascii=False))])
            await self.chat('你好', 'normal-' + dialect)
            self.assertEqual(self.latest_reply(), '你好，来聊音乐吧。')
            self.assertEqual(self.effects, [])


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(ProviderResponseBoundaryTests(name) for name in ProviderResponseBoundaryTests.__dict__
                              if name.startswith('test_'))
