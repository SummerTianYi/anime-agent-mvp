# 后台续作证据索引

本文件和同目录 FOLLOWUP 是新增材料；原报告/STATE/成绩不改。所有JSON是合成后台证据或历史来源映射，不代表本轮Godot显示、声音、真实服务或部署验收。

| 文件 | 用途与判据 |
|---|---|
| [修前](evidence/followup-mechanism-before.json) / [修后](evidence/followup-mechanism-after.json) | 相同4个测试方法：2交付失败及2类型子例错误消失，正常尾页保持；源hash区分版本 |
| [Core全套](evidence/followup-core-full.json) | 实际候选399项、0失败/错误/跳过；含既有确认、防重、Gmail/method、路径及Core语音回归 |
| [独立对抗](evidence/followup-independent.json) | 15用例、100断言；明确保留两个A4反例，不可只看checks_passed |
| [Python与导出审查](evidence/followup-python-review.json) | 9项隔离验证、5项TTS日志恢复、两个runner HIGH修前/修后、双向导出隐私复核与最终hash |
| [模型摘要](evidence/followup-model-summary.json) | 26传输，DS17/GLM9，18例/60条重开消息；逐例首请求hash一致，0重复案例 |
| [完整合成模型链](evidence/followup-models.json) | 输入/system/schema、raw content/tool_calls/finish_reason、最终答复、票据/回执和重开记录；不含私有推理。calls index 6与15为GLM假待办，24为GLM超时；每例关联request_id/session_id |
| [保存与发布范围](evidence/followup-preservation.json) | 原候选SHA/干净状态、生产HEAD/dirty计数、基线推送和扫描范围；非进程健康或数据库身份取证 |
| [TTS固定证据](https://github.com/SummerTianYi/anime-agent-tts/blob/969f4e293a8abbf4b8f153e8551b2fbff93098bf/docs/evidence/batch01-followup.json) | 43项通过，侧车源码与ea5基线相同，日志hash及首次错误Python环境记录 |

业务源码固定在 `1582e479ff0849ce2e6274418dc3ebccc55e49db`，主仓后续仅文档/取证脚本增量。源码SHA256按本机读取字节记录；Git自动换行规范化可能令重新checkout后的字节hash不同，应同时按Git提交内容核对，不误当业务变更。

## 可复现命令

使用已安装项目依赖的Python，在独立工作区执行；不要启动Godot、ASGI监听或TTS服务。`--data-dir` 和 `--output` 必须使用新的专用合成路径。followup_regressions、非resume的followup_models及export_followup自动拒绝覆盖；followup_independent没有该检查，调用者须保证其输出是新路径。示例以本轮目录为基准，后续复现改为新的尾缀。

```bash
export PYTHONUTF8=1
CORE_PY="C:/Users/26052/Documents/Codex/2026-10-12/tianyi-repair-batch-01/services/agent-core/.venv/Scripts/python.exe"
ROOT="C:/Users/26052/Documents/Codex/2026-10-12/tianyi-repair-batch01-followup"
REPRO="$ROOT/docs/assessments/root-cause-repair/batch-01/repro"

# 定向回归；--source-root可选择接手基线工作树作修前复现，测试取当前脚本所在工作树
"$CORE_PY" "$REPRO/followup_regressions.py" --source-root "$ROOT" \
  --data-dir D:/TianyiRepair/batch-01-followup-20261012/replay-new \
  --output D:/TianyiRepair/batch-01-followup-20261012/replay-new.json

# 全套：在上面的命令增加 --pattern 'test_*.py' 并更换输出/数据路径
# 独立只读审查：内存库+audit guard；不要用python -O
"$CORE_PY" "$REPRO/followup_independent.py" --source-root "$ROOT" \
  --output D:/TianyiRepair/batch-01-followup-20261012/independent-new.json

# 取证投影、外部工具拒绝：纯合成，不调用模型
"$CORE_PY" "$REPRO/check_followup_projection.py"
```

固定模型运行器是 [followup_models.py](repro/followup_models.py)。参数为 `--source-root`、`--private-config`（现有私有dotenv，仅读取模型连接信息）、`--data-dir`、`--output`。默认运行已登记三场景/三遍/两模型，最多96次传输，真实工具服务全部替身。`--resume`只允许同源码/schema追加此前不存在的case，既有失败或中断case不重试。本轮已完成固定组，**不要为了改变成绩重新运行**。当前脚本的隔离/投影修正经过确定性复验，原固定模型组没有为此重跑。

公开导出使用 [export_followup.py](repro/export_followup.py)，只读取显式指定的本轮私有JSON，白名单投影请求与响应，拒绝覆盖现有导出。它不是任意未来日志的通用脱敏器；当前快照另经人工和独立审查。

独立审查复现程序：[followup_independent.py](repro/followup_independent.py)。主回归行为测试：[test_followup_delivery.py](../../../../services/agent-core/tests/test_followup_delivery.py)（仓内实际位置为根 `services/agent-core/tests/test_followup_delivery.py`）。

本轮对象仅有独立本地合成数据库/记录及替身中的Issue#1，后者不是实际GitHub写入。所有合成历史和失败记录保留；没有清理旧邮件、标签、仓库对象、生产文件或记忆。原测试对象与真实服务证据继续见 [TEST_OBJECTS](TEST_OBJECTS.md) 和 [原REPORT](REPORT.md)。
