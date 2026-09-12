# 告别挥手：正式第一版与预览历史（Codex，2026-09-12）

## 正式告别第一版：v3已批准并接入正常退出

所有者现已批准下述v3并授权实装/推送；已冻结同SHA的 `farewell_reference_v1.tres`，由独立 `farewell_exit.gd` 在正常关Godot或原Esc出口播放，包含进入衔接、4.1秒告别和退出后的原Core清理。注册表role=exit不加入日常动作。外观仍为1.4；本轮不重启/操作原有窗口，下次启动才加载。完整 [实施与验证记录](../../../../docs/FAREWELL_EXIT.md)、[不可变资产清单](release.json)、`freeze.gd` 和根目录 `verify_farewell.gd` 为接手入口；以下“待审阅/未实装”均为对应历史预览阶段，不再表示正式交付状态。原预览及失败证据继续保留，官模和真人视频不上传。

## 当前 v3：轻摇头与闭眼微笑（待用户审阅，未实装）

所有者基本认可v2手臂，本轮只增加头颈的两次轻微摇晃与挥手期间闭眼微笑。最大头部偏转3.203°，0.8–3.3秒缓入缓出；表情使用官模既有 `笑い=1.0`（闭合笑眼）与 `にやり=0.65`（轻微嘴角笑容），0.6–1.0秒渐入、挥手全段保持、3.16–3.85秒渐出，末态睁眼回正。右臂35轨与已认可v2的124帧逐轨比对通过（最大四元数差8.94e-8），不再改变大臂、肘、小臂、手腕或五指的既定动作。

候选现在包含37个骨骼旋转轨（原右臂35+首/頭2）及2个原生Blend Shape表情轨，共39轨；头和表情均保存到同一个本地TRES，真实GPU预览直接回放该资源，不在截图时单独补表情。493个120Hz结构采样、固定大臂/腕/五指负对照、124帧保存回读、493次非顺序/非关键帧回放、闭眼微笑全段保持与零表情两端检查通过；保存表情最大权重误差2.31e-7。全身及近景各124帧、四朝向关键图与原官模保护门禁通过，仍非全网格零穿模或生产退出验收。

v3证据位于 `D:/UserData/Administrator/Documents/Codex/2026-08-28/https-github-com-summertianyi-anime-agent/work/motion-output/farewell-reference-v3/`，包括 `check01`、`full01`、`near01`、`delivery01/farewell-preview.mp4` 与APNG/联系表/编码报告；两个机位的TRES哈希同为 `aa9684cdf8e8927a601bbed3c47bf6abc38fc7dc4b85b8432f0239889542bea7`。沿用下方复现命令时，在Godot命令前额外设置 `FAREWELL_ARM_BASELINE` 为上轮 `farewell-reference-v2/full01/farewell_preview.tres` 的绝对路径，可重跑已认可手臂对照；不设置则该项被跳过、不作为已验证报告。官模、正式runtime、注册表及项目配置哈希继续与下方记录一致；未实装、未改退出路径、未重启或推送，旧预览完整保留。

## v2：大臂固定，小臂绕肘挥动（手臂已基本认可，历史对照）

所有者否决v1的动作方式：问题不是能否播放，而是上一版将左右摆动分配给了大臂和手腕。本轮仍为离线候选，不实装、不推送。先将右大臂抬到肩高略上7°，抬手完成后固定肩、大臂、肘枢轴、前臂捩转和手腕局部姿态；挥手段只改变右肘弯曲角±23°，让整段小臂和张开的手掌作为整体左右摆动。其余五指伸展、左臂A姿、时序及官模/1.4外观约定不变；依然是视频参考后的人工骨骼适配，不称自动动捕。

新门禁以实际骨骼状态而非单张图判断发力部位：493个120Hz采样中肘枢轴漂移最大1.23e-7米，除肘外右臂局部四元数变化不超过1.27e-7；手腕横向行程14.95厘米，最大肘弯106°，手腕夹角最大5.84°，五指姿态不变。注入4°大臂摆动和4°手腕摆动均被门禁拒绝。保存后124帧回放一致，493次非顺序/非关键帧回放的肘漂移最大1.40e-7米；在3.16秒额外保留精确阶段边界关键帧，防止30Hz烘焙将放手阶段混入固定大臂阶段。首跑因新检查变量缺显式int类型而解析失败，修正后check01又真实检出了边界混入；没有放宽阈值，补关键帧后check02通过。旧失败证据和v1视频均保留。

v2证据根目录为 `D:/UserData/Administrator/Documents/Codex/2026-08-28/https-github-com-summertianyi-anime-agent/work/motion-output/farewell-reference-v2/`，包含 `check01`（边界失败）、`check02`（通过）、`full01` / `near01`（各124帧、36张四朝向图及报告）和 `delivery01/farewell-preview.mp4`（双机位成片，附无损APNG/联系表/编码报告）。TRES两机位哈希一致：`e73510b0f327eab3ef0146dcd4cd30fc1a34cdf2db4d63b61d5df7046e39c80e`。复用上一轮Blender结构取证，官模和正式runtime/注册表/项目配置的下列哈希仍保持不变。只修改本目录候选和归属说明；不把结构与有限多视图检查说成主观自然度通过、真实网格零穿模或生产退出集成通过。

## 历史 v1（动作方式被用户否决，保留对照）

以下为上一轮的历史实现与验证记录，不是当前候选的参数或验收结论。

状态：仅离线预览，等待所有者决定是否实装；未注册 farewell、未修改退出逻辑、未重启正式天依、未提交或推送。动作是根据视频和用户确认人工适配的骨骼动画，不是自动恢复或逐帧一比一动捕。右手（角色正面画面左侧）挥动，五指全程保持官模伸展姿态，左臂保持现有保守 A-pose；不复制视频末尾的随意手指变化。未来应用位置拟为正常退出前的一次告别，需另行批准后接入。

| 内容 | 当前实现 / 证据 |
|---|---|
| 源视频 | 本地 `D:/UserData/Administrator/Downloads/VID_20260912_211342.mp4`；SHA256 `6ccea0ee25523836304a201f69c4ce73132c080a9d31afc79c16b7209fa0b652`；不上传真人视频 |
| 时序 | 0–0.2秒待机；0.2–1.0秒抬手；1.0–3.16秒三次挥动；3.16–3.9秒放回；末尾保持至4.1秒。30fps含两端124帧 |
| 骨骼方法 | 复用 thinking/pose.gd 的已检查几何助手，但覆盖 setup/apply，不执行思考接触姿势；35个右肩臂链旋转轨，静态求出抬手姿势，之后固定局部旋转弧插值。肘保持单轴弯曲，前臂滚转分配到既有手捩链，挥手时不切换掌向 |
| 官模保护 | GLB、骨架拓扑、位移/缩放、身体比例、48表情和两条完整17骨长辫子不改；左臂/躯干/腿局部姿态保持。渲染沿用1.4外观、原辫子摆动及轻微笑眼；候选TRES只包含右臂轨，不包含表情和辫子轨 |
| 结构验证 | 493个120Hz采样；五指不收拢及反例注入；原A姿两端一致；最大肘弯89.397°、手腕弯27.280°、每120Hz局部旋转步长2.574°；肘离轴分量4.43e-7；挥手段掌心朝前点积最低1.0 |
| 回放验证 | 候选保存回读124帧一致，最大四元数差2.94e-7；另做493次非顺序跳转/非关键帧插值，最大四元数差0.001933（约0.222°）；五指仍保持伸展 |
| 渲染验证 | 全身和近景各124帧真实Godot OpenGL渲染，另各36张四朝向关键帧；查看进入/挥动/退出的连续采样联系表及侧背视图，未在已查看画面发现明显反折或手掌翻面；不宣称全网格零穿模 |
| 编码验证 | 1440×960 / 30fps MP4回读124帧、末帧4.1秒；960×640 / 15fps APNG共62帧，逐帧RGB哈希完全一致，无GIF调色板降色 |

本地证据根目录为 `D:/UserData/Administrator/Documents/Codex/2026-08-28/https-github-com-summertianyi-anime-agent/work/motion-output/farewell-reference-v1/`：`blend-rig.json` 是使用 Blender 5.2.1 只读打开1.4源Blend导出的751骨结构；`check01` 是首轮结构检查，`stills01` 是初版近景构图，`full01` / `near01` 是最终同步机位的原始帧、TRES和report.json；`delivery01/farewell-preview.mp4` 为成片，旁边保留APNG、静帧、三张联系表和编码报告。两个机位的TRES哈希一致：`2ad243a59e612defb03fed62fa1c4a55d2203fc9fc123de0583840a2c80a03e0`；MP4为 `9d34b515c65a9ee5467897819da1f90c8d393bc098892f017cea33718173a534`。首轮结构和图像通过后仅收紧近景构图并补非关键帧检查，动作本身未经历失败补丁迭代。

## 复现与未验收范围

从本仓根目录在 Git Bash 运行；每次用新输出目录，脚本拒绝覆盖证据。依赖为本机既有Godot 4.7.2、agent-core虚拟环境中的PyAV/Pillow及已导入的本地授权官模/动作资源。以下输出变量须替换为新的绝对路径，最后编码器也要求新目录；`--verify-only` 可与Godot的 `--headless` 配合只检查骨骼，不作为图像证据。

```bash
FAREWELL_OUTPUT="D:/path/to/new-full" ../tools/godot-4.7.2/Godot_v4.7.2-stable_win64_console.exe --path apps/avatar-runtime --script res://mocap/farewell/review.gd -- --animate
FAREWELL_OUTPUT="D:/path/to/new-near" ../tools/godot-4.7.2/Godot_v4.7.2-stable_win64_console.exe --path apps/avatar-runtime --script res://mocap/farewell/review.gd -- --near --animate
services/agent-core/.venv/Scripts/python.exe -X utf8 apps/avatar-runtime/mocap/farewell/encode.py D:/path/to/new-full D:/path/to/new-near D:/path/to/new-delivery
```

尚未验收：所有者主观自然度、真实网格全表面碰撞、任意当前动作向告别的衔接、音频/淡出、退出中的重复请求或中断、Godot/Core生命周期。上述内容均不能由离线预览门禁代替，本轮没有运行生产Core或API测试。后续若获准实装，先对齐退出时长、触发入口及是否淡出，再单独实现正常退出前播放、重复退出幂等、资源异常兜底、超时必退和现有进程清理回归；不能把本候选直接写入正常退出路径就视为完成。当前暂停续作即可保持生产不变，不需要回滚模型。

本轮新代码仅本目录，归属Codex。工作开始/结束核对正式文件SHA256均一致：GLB `df55806d343d149b41c20d0ef074373cafca2379212fd8691e998ea6cddc6e4a`；runtime.gd `656f9f925b33d479d7695ebf08fe5d03ef8249e4bb45182f98c0abbb8d00305a`；motion_registry.json `aac0189c8b1b679cd1f29680da6d3e27df6c710a288934f955cea471c731c2dd`；project.godot `cc0120ba4f5fc8eeb218ea85fd0e26340317054334da63133e6f7637ca32a401`。已有未提交表情内容和其它代理的Core/启动器/认证脚本工作保持原样，不属于此候选。
