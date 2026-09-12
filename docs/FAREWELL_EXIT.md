# 退出告别第一版（Codex，2026-09-12）

所有者批准挥别v3（大臂抬起后固定、小臂绕肘挥动、五指伸展、轻摇头、闭眼微笑），授权实装及推送，同时明确禁止操作当前窗口。本次仅安装供下次启动加载的实现；没有关闭、重启、激活、移动现有Godot窗口，没有向现有Core发测试消息或改它的配置/数据库/语音进程。外观仍为1.4，官模、既有动作与旧版本档案不变。

## 行为与边界

| 项目 | 实现 |
|---|---|
| 正常关闭 | `runtime.gd` 关闭 `SceneTree.auto_accept_quit`，接收窗口关闭通知后进入 `request_exit()`；原Esc退出入口也走同一路径，输入框中的Esc仍遵循原焦点优先规则 |
| 告别 | `farewell_exit.gd` 按原生Animation采样已批准的4.1秒/39轨资源；前0.45秒由当时姿态平滑接入，其后37骨骼轨及2表情轨保持批准值；不再经过会删除表情轨的通用骨骼重映射器 |
| 单一控制权 | 退出中停止旧动画播放器和本地音频播放、隐藏并禁用交互UI，忽略迟到的Core/手动动作；口型、眨眼与重复关窗不覆盖或重启动画 |
| 清理时机 | 动画结束后才 `SceneTree.quit()`；既有 `core_watchdog.ps1` 在Godot进程退出后按项目和代际清理其Core。未改启动器、Core、TTS守护逻辑 |
| 异常退出 | 动画缺失/哈希不符时直接退出并打印 `farewell_unavailable`；引擎仍处理事件但动画无法推进时，8秒独立计时兜底退出。强杀、原生崩溃、事件循环完全卡死、系统强制关机不保证告别 |
| 资源注册与版本 | 注册表中 `farewell` 标为 `role=exit`，仅供定位/未来模型快照收集；不进入普通AnimationPlayer、菜单或Core动作列表。动作修订为 `farewell-1.0`，不改模型版本号 |

## 资产与恢复

动作定位及完整SHA见 [release.json](../apps/avatar-runtime/mocap/farewell/release.json)。正式本地文件是 `apps/avatar-runtime/assets/motions/farewell_reference_v1.tres`，SHA256为 `aa9684cdf8e8927a601bbed3c47bf6abc38fc7dc4b85b8432f0239889542bea7`，与所有者批准预览完全同字节。源资源永久保留在本机 `D:/UserData/Administrator/Documents/Codex/2026-08-28/https-github-com-summertianyi-anime-agent/work/motion-output/farewell-reference-v3/full01/farewell_preview.tres`；官模/视频/动画资源继续本地限定，不上传GitHub。新机器必须取得经授权的资产，GitHub本身并不包含动画二进制。

从仓库根目录运行以下恢复命令（Git Bash；替换源文件绝对地址）；冻结脚本仅接受已批准SHA，拒绝覆盖不同内容。旧模型档案不变，未来快照工具会随注册表收集这一新动作。代码回退应只撤销本次Codex退出集成提交，不回滚整个共享工作树；退出集成撤销后资源可保留归档，不再被调用。

```bash
FAREWELL_APPROVED_TRES="D:/path/to/approved/farewell_preview.tres" ../tools/godot-4.7.2/Godot_v4.7.2-stable_win64_console.exe --headless --path apps/avatar-runtime --script res://mocap/farewell/freeze.gd
```

## 验证及真实限制

| 检查 | 结果 / 证据 |
|---|---|
| 原批准动作 | 原v3的493次120Hz采样、124帧回读、493次非顺序回放、固定大臂/腕/五指反例和双机位GPU片已通过；本次直接固定其SHA，不重做姿势 |
| 退出衔接 | `verify_farewell.gd`：待机、倾听、思考、旋转、打招呼、说话、生气七组，3444采样、4968269断言通过；最大120Hz相邻旋转2.8361°，无起始帧跳变；通过重复关窗、迟到事件、单一动画写入者、完整笑眼/微笑、恰好一次退出检查。断言数不是代码覆盖率或真实网格碰撞证明 |
| Windows实机第一轮 | 独立副本原CMD启动、独立Mock Core及动态端口；待机与思考中发送定向WM_CLOSE，实际渲染并播完后Godot/Core/会话守护全部退出。证据 `farewell-exit-JlrfW8/e2e-224113` |
| Windows实机第二轮 | 连续三次WM_CLOSE、倾听、旋转、说话、暂停、time_scale=0、缺失资源、损坏资源8项通过。正常片段77–79个真实进程帧，两个故障停滞场景均走8秒兜底；无资源则直接退出。证据 `farewell-exit-JlrfW8/e2e-224501` |
| 干净提交兼容性 | 移除本地尚未提交的表情实现，仅用HEAD+告别补丁，重跑3444采样门禁并实机启动/关窗通过（78帧）；无未提交表情依赖。证据 `farewell-exit-JlrfW8/e2e-225247` |
| 现有能力回归 | 220项隔离Mock Core单测、14项启动逻辑测试、Godot输入/动作/保守待机/会话UI/工具卡/强度档通过；现有本地表情4207帧/204019断言也通过；桌面TypeScript/Vite构建、官模与既有idle/pirouette资产SHA检查通过 |
| 当前窗口保护 | 三轮实机测试记录并持有6个已有Godot/Core/守护进程句柄，前后及各步骤核验仍存活；测试只向新建副本的窗口句柄发送WM_CLOSE，不调用全局按键、不移动焦点，不截图其他应用 |
| 交接命令复演 | 新增准备器从正式目录创建全新隔离副本后，3444采样门禁、冻结工具同SHA幂等/错误源拒绝及原CMD正常关窗再通过（78帧，Godot/Core/守护全部清理）；证据 `C:/Users/26052/AppData/Local/Temp/codex-farewell-afaz7gym/e2e-230240`。冻结源必须用绝对路径，Godot切换项目目录后相对源路径被拒绝；文档一致性守卫通过 |

证据根为 `D:/UserData/Administrator/Documents/Codex/2026-08-28/https-github-com-summertianyi-anime-agent/work/farewell-exit-JlrfW8/`。各实机目录包含 `protected.json`、`results.json`、各场景原CMD/Avatar日志、逐帧JSON与真实Viewport PNG；耗时列包含CIM/端口核验与Core清理，不能当作动画长度。测试窗口禁焦点、非置顶且放在屏幕外；仅替换测试窗口布局，实际运行生产 `_ready` / `_process` / 退出代码、原CMD及原Core守护。没有操作当前窗口进行生产重启验收，没有真实语音/Provider调用，也没有独立子代理审查，人工主审与上述故障注入不冒充这些项目。

真实失败记录：初始版本没有退出控制器，新增门禁返回 `FAREWELL_RED`；测试脚本一处Mesh类型推断解析失败，补显式类型后通过。第一轮连续关闭测试在每次事件之间执行慢CIM查询，第三次请求送出前窗口已正常退出，导致测试失败；改为先核验所有权再连续投递定向WM_CLOSE，第二轮真实通过，未修改动作或放宽重复退出规则。Git Bash继承的PSModulePath使资产检查找不到Get-FileHash，清除仅该检查子进程的变量后原检查通过，未修改系统配置。

## 重跑（不碰正在使用的窗口）

先通过下面的准备器生成新副本，再将输出绝对路径作为 `--repo`。准备器复制已授权本地资产和独立缓存，不复制生产 `.env`；测试单独创建Mock配置、数据/用户目录、Core虚拟环境与测试端口，且父目录不得存在TTS项目，避免启动器触发真实语音守护。正常Godot窗口关闭通路按[官方窗口退出说明](https://docs.godotengine.org/en/stable/classes/class_scenetree.html#class-scenetree-property-auto-accept-quit)接管；禁焦点使用[官方窗口设置](https://docs.godotengine.org/en/stable/classes/class_projectsettings.html#class-projectsettings-property-display-window-size-no-focus)。

```bash
services/agent-core/.venv/Scripts/python.exe -X utf8 scripts/tests/prepare_farewell_fixture.py --source "D:/path/to/anime-agent-mvp"
services/agent-core/.venv/Scripts/python.exe -X utf8 scripts/tests/test_farewell_exit.py --source "D:/path/to/anime-agent-mvp" --repo "D:/path/from/prepare/fixture"
# 结构门禁也在上述独立副本运行；headless不代替Windows/GPU验收。
AGENT_CORE_WS_URL=ws://127.0.0.1:1/ws ../tools/godot-4.7.2/Godot_v4.7.2-stable_win64_console.exe --headless --path "D:/path/from/prepare/fixture/apps/avatar-runtime" --script res://verify_farewell.gd
```
