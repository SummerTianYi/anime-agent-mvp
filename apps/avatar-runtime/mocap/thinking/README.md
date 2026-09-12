# 思考动作第一版：正式接入（Codex，2026-09-12）

当前状态：所有者批准带发束回位的 review11，并授权实装及推送；正式注册 `think`，菜单「思考」或 agent 从其他状态进入 thinking 时触发9.5秒单次动画。身体74条与发束34条纯旋转轨合为一个 Animation，进退均包含在内；自动触发不抢录音或已有手动动作，回复状态/口型立即生效、不等待身体收势。每轮完成后回原待机，不无限保持托腮。模型仍为1.4、703骨、48表情，所有历史模型/动作保留。**下方“未实装/待确认”均为历史试验记录，当前交付状态以本节为准**；这不是全指自动动捕或通用防穿模系统。

## 正式交付定位与复现

仓库根目录为 `D:/UserData/Administrator/Documents/Codex/2026-08-28/https-github-com-summertianyi-anime-agent/work/anime-agent-mvp`；下表 `../` 相对该根目录。官模、源视频、TRES与渲染图因授权范围仅本地保存，不随 GitHub 推送；新机器须先取得这些受限资产，不能宣称仅 clone 即可显示人物。交接代码不依赖本地尚未提交的表情增强实现。

| 文件/位置 | 作用与不可变校验 |
|---|---|
| `apps/avatar-runtime/assets/motions/thinking_reference_v1.tres` | 正式108轨/9.5秒资源；SHA256 `7637d1210c52fd4fcaff4d40f517eab578a9cfc4c9dec46b1e75c370a56e9f09` |
| `../motion-output/thinking-hair-return-v1/final-detail/thinking_preview.tres` | 批准的身体来源；SHA256 `6b6e4a15c1f531a5a727408adbee77b84306c038b5953708922c57345c3a9eb2` |
| `../motion-output/thinking-hair-return-v1/review11/hair_return_preview.tres` | 批准的完整34骨发束来源；SHA256 `1f77d1eb52b7066d09ea8b711efe72781ecfc50575414bff1f24c6bd45849e51` |
| `freeze.gd` | 验证两个来源SHA后逐轨合并，不重新求解/重采样；目标已存在时拒绝覆盖，保存后逐键回读 |
| `verify_integration.gd` |1141帧120Hz来源和正式播放器一致性、703骨位置/缩放/非控制骨、发束相位、重复触发、录音抢占、重置、缺素材和手动动作优先级；负对照拒绝改变的旋转 |
| `render_integration.gd` | 隔离Core/持久化，调用实际菜单按钮、正式每帧处理和AnimationPlayer完成信号；301帧完整GPU渲染、16个多朝向样本和29268次旋转比对 |
| `../motion-output/thinking-release-v1/` | `before`为实装前本地代码，`integration-*.json`、`render-*`及回归日志为本次证据；最终有效报告见末尾验收追加 |

复现合并：在 Git Bash 中设置 `THINKING_APPROVED_ROOT` 为上述 `thinking-hair-return-v1` **绝对目录**，运行 `../tools/godot-4.7.2/Godot_v4.7.2-stable_win64_console.exe --headless --path apps/avatar-runtime --script res://mocap/thinking/freeze.gd`。资产已安装则只核对SHA，不重复构建。验证沿用同一个来源变量，脚本换为 `verify_integration.gd`；可用 `THINKING_REPORT` 指定不存在的绝对JSON路径。GPU测试另设新绝对目录 `THINKING_OUTPUT`，使用 `--display-driver windows` 和 `render_integration.gd`。所有验证使用真实模型/播放器，不调用外部LLM，不修改生产会话。

运行时只读烘焙轨，不引用 `strand_physics.gd` 等离线求解脚本。发束在0.2–9.3秒由已批准轨道完整控制，首尾各0.2秒混合到实际运行时待机时钟；非思考动作继续原摆动代码，不新增全局碰撞参数。显式重置/其他动作中断会释放骨姿态，保证无残留，但这不等于每一种临时中断都具备无碰撞自然过渡。下文记录的1.29–1.31秒接触偏硬和代理碰撞的局限仍保留，不能因本轮状态机测试通过就声称真实网格处处零穿模。

回退单个动作时移除注册表 `think` 条目并重启，状态触发会安全回退为原表情/待机；菜单按钮仍存在但缺资源仅报告不可用。完整代码回退应只撤销本次 Codex 思考提交的相关差异，保留随后其他 agent 的改动；禁止拿含其他本地表情修改的 `before/runtime.gd` 整文件覆盖新的工作树。正式TRES、批准的身体/头发来源及旧失败预览均保留，不改1.0–1.4模型档案。

## 下一批：两段低接触风险录制

优先把现有程序式「点头确认」与「挥手」升级成真人节奏的短动捕，不新增复杂手脸接触。点头片建议总长6–8秒：A姿2秒、自然轻点1–2次、回A姿2秒，躯干稳定、头部约10–15°。告别挥手总长8–10秒：A姿2秒、一手在肩外侧抬起，掌心大致朝镜头小幅摆2–3次、自然落回A姿停2秒；另一臂离开裙子，不翻腕、不横穿胸前/辫子。固定机位、全身和双手始终入镜、上传原片。没有收到新视频前不假称已完成这两段动捕；复现边界仍是角色比例适配后先预览，再由所有者验收。

## 已对齐的动作

### 本次正式接入验收结果（Codex）

`thinking-release-v1/integration-final.json`及仅含拟提交代码的隔离副本 `clean-integration.json` 均通过：1141帧、2651216断言；`render-final/report.json`通过301帧真实逐帧渲染、16视图、29268旋转对照，菜单按钮及真正AnimationPlayer结束信号生效。另有220项隔离Mock Core回归、桌面TypeScript/Vite构建、原倾听97483检查、表情4207帧/204019断言，以及motion/text/session/effort/tool UI守卫与文档一致性通过。没有启动子代理，干净副本是同一代理自审，不称独立第三方审查。

初次门禁先因未注册 `think` 正确变红；01/02报告中手臂旋转比对失败来自q/-q等价表示，按原预览已有的归一化/同半球分量误差检查修正，并保留0.01rad错误旋转负对照，未改变批准动作或放宽动作幅度。发束首轮逐字相等也改用原浮点容差。GPU工具首轮的虚函数签名错误、误实例化SceneTree守卫导致旁支日志均修正，旧报告保留，最终只认 `render-final`。补测防止自动thinking抢占手动程序式点头；非思考摆动保留原计算值。

**生产启动尚有独立阻塞**：2026-09-12约18:27，正常关闭旧Godot（PID6520）后原Core进程3948/26340确实退出；使用原根CMD重启时，Core在 `memory.sweep_empty_sessions()` 报 `sqlite3.DatabaseError: database disk image is malformed`，未进入新Godot启动阶段。证据 `thinking-release-v1/restart.log` 及 `%LOCALAPPDATA%/AnimeAgent/logs/core-20260912-182739-216-5356.stderr.log`；本次未修改storage/Core/启动器、未删库、未改为空库、未宣称正常启动通过。动作文件已安装，需先取得数据恢复授权再恢复生产启动。不要通过重做动作或改模型来处理SQLite损坏。

视频参考为 `D:/UserData/Administrator/Downloads/VID_20260912_160405.mp4`（SHA256 `43dae532bc26f22d14ce1e961cbd0f3ca1864470a3681efbdb858c5505c641dd`，原片约9.62秒）。保留镜头右侧手托下巴、另一手轻托肘部、略抬头并左右看的设计；后续两张近照明确改为拇指与食指张开，其余三指收拢，手型保持、不搓下巴、不循环翻腕。原片另一手在腹前，本候选按所有者新要求改为托肘。进入约0.3–1.65秒、思考保持至7秒、8.6秒回到保守A姿，预览结束9.5秒。两次轻眨眼和原有长辫子摆动仅在离线预览中应用。

此为**视频参考＋人工角色接触适配**，不是原始视频自动恢复的逐帧全指动捕。关键姿势根据真实运行时骨长、手掌平面和肘关节轴建立；头部参考节奏和被遮挡的接触深度经人工适配。静态接触姿势使用两骨IK，过渡使用固定局部四元数插值，前臂轴向旋转分配到官模已有手捩骨链，不通过伸缩骨头或修改网格完成。下半身保持原姿，未重做布料/头发物理。

## 文件与复现

| 文件 | 用途 |
|---|---|
| `inspect_blend.py` | Blender只读结构检查，不保存源Blend；751源骨与运行时703骨是既有导入差异 |
| `probe.gd` | 实际运行时骨架、材质面边界与脸部中心采样；原A姿不满足手靠近脸条件，返回1是预期负对照 |
| `pose.gd` | 独立候选的接触姿势与连续旋转轨迹；未被正式入口引用 |
| `verify.gd` | 120Hz全程骨位移/缩放/非控制骨/首尾/手型/肘轴/腕弯/连续性检查 |
| `preview.gd` | 离线场景生成独立TRES、回读286帧比对后，用真正AnimationPlayer渲染全身/近景/多朝向 |
| `encode.py` | 本地PyAV编码30fps MP4、15fps无损RGB APNG及并排预览；不上传视频、不调用生成式图像服务 |

从仓库根目录在Git Bash运行，`THINKING_OUTPUT`必须使用尚不存在的**绝对目录**（防止覆盖既有结果），Godot路径按本机布局。例：

```bash
THINKING_REPORT='D:/your-output/check.json' ../tools/godot-4.7.2/Godot_v4.7.2-stable_win64_console.exe --headless --path apps/avatar-runtime --script res://mocap/thinking/verify.gd
THINKING_OUTPUT='D:/your-output/full' ../tools/godot-4.7.2/Godot_v4.7.2-stable_win64_console.exe --display-driver windows --path apps/avatar-runtime --script res://mocap/thinking/preview.gd -- --animate
THINKING_OUTPUT='D:/your-output/detail' ../tools/godot-4.7.2/Godot_v4.7.2-stable_win64_console.exe --display-driver windows --path apps/avatar-runtime --script res://mocap/thinking/preview.gd -- --near --animate
services/agent-core/.venv/Scripts/python.exe apps/avatar-runtime/mocap/thinking/encode.py 'D:/your-output/full' 'D:/your-output/detail' 'D:/your-output/delivery'
```

实际本地证据根目录：`D:/UserData/Administrator/Documents/Codex/2026-08-28/https-github-com-summertianyi-anime-agent/work/motion-output/thinking-reference-v1`。`review01–06`是静态迭代，只有06使用最终拇指食指手型和当前接触参数；`final-full3`/`final-detail`是保存、回读验证后的最终双机位源帧，`delivery`为成片。`final-full`/`final-full2`是下面说明的失败回读尝试，不能作为通过证据。原始视频、官模、渲染帧和TRES都只在本地，不进Git。

## 验证与明确边界

最终参数的 `check06.json`：1141个120Hz时间采样通过；最大单步旋转1.3093°，最大折肘145°，最大腕弯30.9063°，肘轴外分量低于0.000001，托肘的掌部骨参考点至肘骨中心最大3.7721cm（这是考虑外表面厚度的粗略定位，不是网格间真实空隙）。骨位移、缩放、非控制骨和首尾原姿不变；负对照确实拒绝张开的中指。保存后的74轨旋转TRES全286帧回读与作者姿势比对通过；已检查正面、±55°及背面关键帧，并生成全程双机位30fps预览。没有修改生产文件，因此未重启Core/TTS、未调用LLM、未执行生产聊天测试；本轮不冒领其它agent并行更新的204项Core基线。

原官模GLB SHA256始终为 `df55806d343d149b41c20d0ef074373cafca2379212fd8691e998ea6cddc6e4a`；本轮前后runtime SHA256为 `42253ddc95c7726adacdef27a286b56b65bfb1d981f0b9e1967e42bf6427b415`，注册表为 `72dce8be89d9ca91fb8b07d4916dd8ac3a9c3419da65c3afb668480731eba8d1`。这些是本轮未实装的证据，不应阻止其它agent今后合法修改。

初始探针遗漏输出环境变量已纠正；早期整掌姿势遮脸/偏远、托肘掌向与卷指方向不合适，经过真实侧面渲染纠正；所有者追加两指手型后收拢其余三指。初次回读检查采用acos(dot)且未处理四元数符号等价，在几乎相同的q/-q上产生0.002184rad假误差；改为单位化、符号对齐后的四分量距离门禁0.00002，**不是放宽姿态误差**，全帧重新通过。初次断言遗留的离线预览进程已通过该执行会话终止，正式天依没有关闭。

目前只是动作/观感候选：手指与下巴的精确表面贴合、托肘附近长辫子与袖口交叠、任意朝向与其它动作混合、随时中断/语音状态衔接，均未宣称完成物理或生产验收。尤其长辫子仍沿用现有摆动，不应把角度与数值门禁通过等同为全身零穿模。下一步先由所有者看成片决定手型、节奏和自然度，再决定是否继续接触精修或授权实装。

## Codex 追加：辫子绕臂独立预览（2026-09-12，未实装）

所有者指出辫子穿臂后，本轮只为思考动作增加 `hair_pose.gd`、`preview_hair.gd`、`verify_hair.gd`，并给原编码器增加可选 `--hair-comparison`，默认行为不变。沿用已核对的Blender骨架与运行时双侧各17段完整骨链，在原摆动之后调整旋转：托肘一侧向前绕过手臂，托下巴一侧向外绕开前臂，下段逐渐转向垂落方向，动作结束恢复原路径；身体、手型、两指、头部节奏和正式文件不改。它是确定性的动作配套路径，不是有真实接触力的通用物理系统，侧面仍可能有“架起”的观感，需所有者看动画决定。不得把输出的 `thinking_preview.tres` 单独安装当作此版本——该文件仍仅含74条身体轨道，辫子层由预览入口在其后执行，尚未烘焙或接入正式状态机。

| 项目 | 实际结果与边界 |
|---|---|
| 完整预览 | 9.53秒、286帧、30fps；同机位左旧右新MP4，另有143帧15fps无损RGB APNG；近景与全身各32张多朝向检查图 |
| 结构检查 | 571个60Hz采样；骨段长度最大误差0.000000313m，骨位移/缩放及非辫子骨保持在浮点容差内，最大单步辫子旋转0.5871°；首尾恢复原摆动 |
| 有限碰撞检查 | 手臂胶囊半径32/35mm、发束半径14mm，旧版最小代理间隙−45.85mm，新版+2.54mm；关闭修正的负对照返回1，新版返回0。此数值不是网格实际距离，不覆盖手指、腕饰、躯干、发束自碰撞及任意新动作 |
| 真实回读 | 身体TRES286帧回读一致；编码后MP4帧数/时长验证，无损APNG全帧RGB回读一致；首尾与旧渲染最大单通道差1/255 |
| 不变项 | runtime、motion_registry与官模GLB哈希均与上一节相同；无生产重启、Core/API调用、子代理、commit或push |

本地证据根目录为 `D:/UserData/Administrator/Documents/Codex/2026-08-28/https-github-com-summertianyi-anime-agent/work/motion-output/thinking-hair-preview-v1`；`final-detail`为最终源帧，`full-check`为全身多朝向，`final-check.json`与`negative-control.json`为验证，`delivery/thinking-hair-comparison.mp4`为交付预览。旧成片仍完整保留在 `thinking-reference-v1`。初试发梢回拉形成不自然的弯曲，已改为下段渐进垂落；缩小前移后R侧代理检查重新失败，恢复该侧必要让位、保留另一侧较小前移后通过，不隐藏失败报告。原始网格接触与自然度尚未完成正式验收。

复现：将上文GPU命令的入口改为 `res://mocap/thinking/preview_hair.gd`（近景用 `--near --animate`）；验证改为 `res://mocap/thinking/verify_hair.gd`，传入新的 `THINKING_REPORT`，加 `-- --baseline` 为预期失败负对照。编码器两输入分别传旧 `final-detail` 和本轮 `final-detail`，另加 `--hair-comparison`。代理距离使用Godot [Geometry3D线段最近点](https://docs.godotengine.org/en/4.7/classes/class_geometry3d.html#class-geometry3d-method-get-closest-points-between-segments)，不是三角面穿透检测。

## Codex 追加：接触与垂落物理试验（2026-09-12，仍未实装）

所有者认为上一版像被架起，本轮仅增加离线发束试验，不修改身体动作、手型、官模、runtime、注册表，不启动生产Core、不commit/push。采用`blender-motion-state-inspection`流程复用前述不可变源模型结构报告，并检查连续骨段、保存回读、多朝向真实Godot渲染；不是生成式效果图。当前供审阅的是 `review07-hybrid`，**不等于通过正式实装验收**：接触瞬间仍偏硬，尚无实际网格碰撞或发束自碰撞证明。

`strand_physics.gd`为两条17节点发束的独立位置约束试验，240Hz、64次长度/弯曲/空间线段碰撞迭代，重力9.81m/s²、速度阻尼8/s；归一化粒子质量和弯曲柔度属于效果参数，未按真实发丝标定。手臂、掌部、手环和胸前用跟随骨架的胶囊/球代理，未加不可见托板。前1.2秒沿用整理好的动画路径，之后仅前3个连接节点跟随动画发根，其余中心线由重力和接触决定；旋转映射仍借用现有骨架朝向参考，非完整扭转弹性模型。它是**动画引导＋近似物理**，不是全程无引导模拟、不是逐根发丝或双向布料仿真，也没有专门的库仑摩擦/连续时间碰撞检测。正式待机没有被本轮自然下垂姿势替换。

| 文件/证据 | 用途与实际结果 |
|---|---|
| `physics_preview.gd` | 离线模拟、34条纯旋转轨烘焙120Hz、重新加载并全1141帧比较；另存身体TRES不变；支持`HAIR_CLIP`复用已保存模拟，渲染时读该资源 |
| `spring_audit.gd` | 独立AnimationPlayer回放发束轨；检查所有703骨位移/缩放/非发束旋转、上臂/前臂代理距离和方向连续性。名称沿用早期试验；退出码0只证明结构，不证明自然度 |
| `check07.json` | 1141采样结构通过：骨位移0，最大缩放误差0.000000400、非发束旋转误差0.000000358；最小手臂代理间隙−0.069mm，超过2mm的代理穿入帧0 |
| `no-contact-check.json` | 相同动作/发根/重力，关闭全部碰撞：最小手臂代理间隙−43.30mm，718帧超过2mm。开关确实改变接触结果，不是只改显示或统计口径 |
| 动态与未过项 | 有碰撞时R侧末端从7秒到9.5秒下降47.84mm，无碰撞仅2.46mm；有碰撞最大局部旋转步长9.9045°/120Hz，中心线方向8.8380°，集中在1.29–1.31秒接触区，仍偏硬，不能宣称自然度已通过 |
| 范围限制 | 代理测试不是皮肤/袖口/细发丝三角网格间距；胸前代理在初始引导姿势可有约5.1mm重叠。无全身、发束互碰、任意动作、临时中断/混合状态验收；首尾身体回原姿，但发束末态是模拟结果，不应直接拼接生产待机 |

本地证据根目录：`D:/UserData/Administrator/Documents/Codex/2026-08-28/https-github-com-summertianyi-anime-agent/work/motion-output/thinking-hair-physics-v1`。`review07-hybrid/hair_spring_preview.tres`是当前发束候选（旧文件名保留，不代表仍用原生SpringBone），`hair-replay.json`为回读误差，`solver-diagnostics.json`含求解点/真实骨段映射误差；`final-detail`为286帧近景，`full-check`为32个全身多朝向样本，`delivery/thinking-hair-contact-preview.mp4`比较上一版固定路径与本轮混合模拟，旧版本全部保留。

失败路线也保留：`thinking-hair-spring-v1`的原生SpringBone尝试曾有24.36°单步折跳及22.28mm代理穿入，未采用；其独立源脚本已移到该本地证据目录`native-experiment.gd`，不留在当前预览执行链。位置约束试验`review01–04`证明固定到第4节点会与抬手袖口冲突，缩短固定段后减轻但会落入臂内；`review05–06`的引导切换又错误恢复了发根旧朝向，转动整条下游发束而产生串边/甩动，不能用作候选。07保留引导的连接坐标系后才消除该衔接错误。不得重复放大碰撞体或用固定大弧线掩盖这些失败。

复现入口为`res://mocap/thinking/physics_preview.gd`，环境`THINKING_OUTPUT`仍要求新绝对目录；`--near --animate`输出近景完整动画，`--audit-only --no-collisions`输出无碰撞负对照，`--unguided`仅用于全程自由模拟实验。验证使用`SPRING_CLIP='绝对发束TRES路径' THINKING_REPORT='新JSON绝对路径'`及`spring_audit.gd`。编码器两输入为上一版`thinking-hair-preview-v1/final-detail`与本轮`final-detail`，增加`--physics-comparison`。方法参考[XPBD原论文](https://mmacklin.com/xpbd.pdf)，本实现只是带柔度的发束距离约束子集，不能据此声称实现了完整论文系统。最短后续工作是先审阅完整动画的接触转折，再局部处理接触前后的速度/曲率连续性，并测真实袖口与发丝边界；禁止绕过未通过项直接安装。

## Codex 追加：思考结束后辫子回位（2026-09-12，仅预览）

所有者指出退出后辫子留在身后，根因为上一物理试验只结束了身体动画，没有将发束模拟末态交还原待机。新增回位门禁先对旧 `review07-hybrid` 复现失败：9.3–9.5秒相对同时间待机，完整骨链点位最大偏离371.75mm、局部旋转56.41°。这不是官模结构损坏，也不能靠只重置最后一帧解决。最新候选是本地 `thinking-hair-return-v1/review11/hair_return_preview.tres`，并非该目录较早的失败版本；0–7秒沿用旧保存动画，7秒后以带阻尼的回归力引导两条完整骨链走回退出路径，8.9–9.3秒平滑交还原待机并匹配摆动时间相位。回归力逐渐启用，最大系数400/s²、速度阻尼最大40/s；这是动作配套的物理/动画混合，不宣称纯重力可以自动恢复任意官模待机造型。

退出片段进行时域平滑、约束再投影与短窗平滑，离线投影采用6mm/2mm滤波保护余量，独立验收仍使用原手臂32/35mm和发束14mm半径。L链第3骨在7–8秒增加最高3°的平滑向外绕行，原因是实测残余接触法线主要为+X，避免回程在上臂外侧抄近路；不是更改手臂动作、放大生产碰撞体或全程架起辫子。两条骨链都完整回位；屏幕左右与角色左右不能混淆。`--return-idle` 是独立预览开关，既可在新模拟后处理，也可配合 `HAIR_CLIP` 读取不可变旧模拟，输出新的回位TRES；没有覆盖来源资源。

| 门禁 | 当前候选的实际结果 |
|---|---|
| 独立回放 | `check11.json` 1141帧/120Hz与 `dense-check11.json` 2281帧/240Hz均通过；加密检查包含保存关键帧之间的插值 |
| 回位与相位 | 连续检查9.3–9.5秒而非仅末帧；加密样本49个，全部34发束骨最大局部角误差0.0000256°、全局点位误差0.000000534m |
| 原动作与结构 | 0–7秒与源模拟逐轨比较最大差0.0000659°；骨位移0、缩放误差<0.000000685、非发束旋转保持浮点容差内；身体74轨TRES另作原文件哈希对照 |
| 回程连续性 | 最大单步角度折算到120Hz为1.968°，小于预先设置的2°门禁；不沿用旧末段5.943°折跳，也不在结束时突然复位 |
| 有限碰撞 | 原手臂代理最小间隙−0.0691mm，超过2mm的代理穿入采样0；不是实际网格零穿模证明，也不覆盖所有发丝/腕饰/手指接触 |
| 保留限制 | 前1.29–1.31秒原接触转折仍偏硬，属于0–7秒未修改段；自然度仍由所有者审阅，任意时刻中断、实时混合/生产状态机没有实装或验收 |

试验01/02的直接四元数混合虽然末态正确，但会横穿上臂；03回归物理未平滑有30.45°瞬时转折；04仅平滑又切入代理；05–10逐步验证滤波与再投影会互相影响，不能用单一“末帧正确”或“碰撞通过”替代完整回程验收。失败TRES与JSON仅保存在同一本地证据目录，不进入正式动作注册表。`verify_hair.gd` 仅增加最近接触外法线证据，不改变原距离算法或阈值。`spring_audit.gd --require-return` 才会把回位、回程步长、结构与有限接触一起作为退出码门禁；不带此开关仍保留历史结构审查语义。可另设 `RETURN_SOURCE_CHECK` 核验0–7秒来源轨道保持不变。

本地证据根目录为 `D:/UserData/Administrator/Documents/Codex/2026-08-28/https-github-com-summertianyi-anime-agent/work/motion-output/thinking-hair-return-v1`，其中 `review11` 为最终离线候选，`final-detail` 为实际GPU连续帧与32个多朝向样本，`full-check` 为全身32视图，`idle-reference` 是同相位原待机参照，`delivery` 为前后视频和回位全身图。编码使用 `encode.py <旧physics-v1/final-detail> <新return-v1/final-detail> <新delivery> --return-comparison`；同相位像素及身体TRES检查使用 `verify_return_images.py <新return-v1根目录> <旧physics-v1根目录>`。本轮保持runtime、registry、官模GLB的前述SHA256不变，未实装、未重启生产、未调用Core/API、未启子代理、未commit/push；历史证据全部保留。

交付媒体回读完成：`delivery/thinking-hair-return-preview.mp4`为286帧/30fps/9.53秒，143帧15fps APNG全帧RGB精确回读；`returned-full-comparison.png`展示全身末态。`idle-image-check-v2.json`确认身体TRES SHA256仍为 `6b6e4a15c1f531a5a727408adbee77b84306c038b5953708922c57345c3a9eb2`，四个朝向末态轮廓边界均与同相位待机一致。第一次像素门禁曾失败：−55°图的一个半透明轮廓像素发生4xMSAA单样本覆盖变化（Alpha64→127），其余像素最大差1/255；原失败报告 `idle-image-check.json`保留。修正版仅允许每百万像素图中最多4个半透明边缘像素的一次MSAA覆盖量变化（≤64），不豁免不透明内部或轮廓边界位移；人工注入一个不透明像素10/255变化的负对照仍被拒绝。不能把这一栅格误差豁免当作骨架偏移容差，独立骨架回位门禁保持不变。
