# 稳定保持用户认可的视觉表现

适用：按已选样张连续制作商品图、套图返修，或用户要求“张力拉满”“效果不要缩水”。当前用户的卖点、材质、场景沿用已认可的产品主导、空间文字关系；用户明确换风格时更新依据，不把本项目偏好推广给所有任务。

## 固定输入与图型关系

提示词写“高级、强张力”不等于传入风格图。每张核对实际 `tool_args.referenced_image_paths`，原商品控制事实、认可样张控制可迁移关系；未获认可的草稿只作编辑目标，不能自升为风格标准。查看原图后实际调用同一份 `tool_args`，修改参数就重新预检。

| 图型 | 固定的设计关系 | 边界 |
| --- | --- | --- |
| master | 商品优先、件数准确、轮廓清楚、符合平台要求 | 不强加广告大字、人物、动作或光迹 |
| feature | 一个已核实主张；前景商品、中景作用点/文字、后景环境 | 第二张改变主张和镜头关系，不只换标题/背景 |
| material | 一个真实材料事件、至少两种空间或材质关系 | 硬质材料用接触和近远对照；不弯钢材、不伪造剖面 |
| scene | 商品—动作—可见结果，产品第一视觉 | 两张改变阶段/镜位/互动；手与背景服务商品 |
| dimensions | 来源数值、单位、正确对象与可核实端点 | 未知端点只呈现供应商组合尺寸，不伪造标线 |

文字允许不影响辨字的局部字形遮挡；关键字符无法辨认就返修。不要把“所有字完全无遮挡”泛化成平铺标题，也不靠堆粒子、霓虹和未证实的数字补张力。无字图型关闭文字模块。

## 新版可运行合同

`scripts/visual_production_gate.py` 校验本地文件、哈希、输入角色和审核完整性；不识别审美、不认证真实调用/用户认可、不运行检测、不接管图床或平台API。它通过不代表已获用户认可、已过合规服务或跨SKU稳定。

沿用 [通用brief](reusable-brief-and-prompt.md) 和 [审核合同](visual-review-protocol.md)，新增：

- brief：`visual_production: {version: 1}`，`style_lock.required` 布尔值；明确 `sku/image_type/review_set/realism.mode` 及 `spatial_type/effects/material_expression.enabled`。参考锁定时 `style_lock.transfer/exclude` 分别列迁移和排除关系，`composition` 写具体 `near/middle/far/tension_source/primary_subject`。
- request：`schema_version=1`、`sku`、`purpose`、`slot_role`、`mode=generate|edit`、`tool="built-in image_gen"`、`brief`、`inputs`、完整实际 `tool_args`。`purpose` 等于 brief.image_type；套图 slot_role 如 `feature-1`。编辑目标标为 `draft`，仍保留原始商品和认可风格图。
- 文件描述符：`{file, sha256}` 使用真实小写SHA256，相对所属JSON目录解析；inputs另带 `role`，可用 product-identity/style-reference/draft/brand-asset/copy-evidence。风格图另带 `approval: {status, evidence: {file, sha256}}`；status仅为真实 `user-approved-style` 或用户本次指定的 `user-selected-reference`，不自造认可。
- `tool_args`：`prompt` 完整实际文案、`referenced_image_paths` 绝对路径数组、`transparent_background` 明确布尔值。声明的图片必须真正附上，附上的图片必须有角色/哈希；copy-evidence不作为图片附件。当前可见内置工具没有seed/model/size/quality参数，不把提示词期望当回执。
- review：保留既有字段，再加 `generation_request: {file, sha256}`、`observed_copy`、`unresolved_defects`、`inspection` 和 `comparisons`。observed_copy逐项等于 brief.message.exact_copy，无字两者为空数组。inspection含实际执行的 full_size/thumbnail及evidence；比较项为 `{reference: {file, sha256}, evidence}`，覆盖本次选用的风格图。制作自查写 `creator-self-check/independent_context=false`。
- 材质张力图启用 material_expression.action/visual_result，checks额外逐项审 material_event/material_tension；普通detail图不冒充已验证材质张力。

当前认可原图及范围见 `../assets/approved-style.json`。平台主图、尺寸或无样张的自由探索可设 `style_lock.required=false` 并说明原因，不能借此绕过本用户锁定的附图风格。仅会话图片的调用遵循 imagegen 规则取得可核实来源；无法本地机器绑定时如实保留人工检查范围，不伪造路径或静默换API。

在生图skill目录运行，报告使用新的工作目录文件：

```text
python -X utf8 -B scripts/visual_production_gate.py preflight --request ./work/request.json --report ./work/report.json
python -X utf8 -B scripts/visual_production_gate.py review --request ./work/request.json --review ./work/review.json --report ./work/report.json
```

preflight退出0再按同一参数生成；成图实际查看全图、关键局部和缩略图后才填审核。320px可作本项目缩略图参考，不是所有图的字号标准。缺图、过期哈希、观察缺失、关键项fail/unknown、未解决缺陷均拦住当前图；总分、制作自评和SafeSellAI低风险不能覆盖。独立审核必须实际执行并附对应输出和review_id的记录，不默认开子代理或付费API，不为通过脚本制造记录。

## 返修与持续执行

| 缺陷 | 修改动作 | 复核 |
| --- | --- | --- |
| 遮字、拼错 | 保持商品、镜位、动作和光影，只改文字位置/尺度/拼写 | 逐字核对，再查产品和风格有没有漂移 |
| 张力和层次不足 | 对照原样张，改变一个主要镜位/尺度/字物关系 | 重审构图，不自动降成普通摆拍 |
| 形状、件数、规格漂移 | 回原商品及原风格图重做，或用实际可用的固定商品层 | 身份及关联图；不从错误草稿学习结构 |
| 同类修复两次无效 | 留存失败，诊断约束冲突并换有效策略/路线 | 不盲抽、不降标准凑数 |

已有整套授权且风格明确，锚定候选审核后继续其他图，不重复索要同一审美确认。用户退回覆盖当前对应放行，旧文件和回执保留，失败图哈希进入当前批次拒绝清单。外部阻塞仅影响对应步骤，其他已授权工作继续。

## 交付与上架衔接

新版brief调用 `delivery_gate.py` 时传 `--generation-request <request.json>`；缺参会拦截。若后续像素处理改变候选，另传 `--production-review <原始生成审核.json>`，最终审核的 `processing_receipts` 描述符数组按实际处理顺序绑定已完成处理的input/output；元数据清理沿用原字节证据链。用户跳过剩余检测的既有决定继续生效，未知不改阴性。

沃尔玛新增/返修批次设置 `visualGateRequired=true`。每张新增图的 `visualPipeline.requestRef/reviewRef` 绑定真实请求/审核；最终导出哈希不同，附 `deliveryReportRef`。纯复用旧图用 `reuseExisting=true/reuseManifestRef` 绑定原认可manifest及同一字节哈希；退回图不能以旧图身份复用。具体字段见沃尔玛编排技能 `references/data-contract.md`。

本地交付和批次审计入口会实际重跑文件检查；未调用这些入口的服务器API仍不受自动拦截。写图床/暂存前执行适用闸门，文件再变就重跑；skill更新不扩大发布、付费、采购或发消息授权。

## 经验与稳定性范围

2026-10-16刮冰器案例：原认可样张未持续实际附上，旧制作自查未挡住风格退化。重做绑定原商品/认可原图，发现FROST遮字后定向返修并复核；仅一个图型的一次生成/一次返修和制作自查，用户未认可新样张。不能登记为整套成功、跨类目配方或模型训练。

模型、关键提示词或配方变更后，固定不同SKU/图型重复评估首稿通过率、返修次数、身份/文案失败、实际耗时和合格图成本，并与用户偏好校准。3 SKU×2图型×2次是小规模试验建议，尚未完成，不宣传未经测量的稳定率；seed不代替质量验收。

依据：[官方参考分工与定向编辑](https://developers.openai.com/api/docs/guides/image-prompting)、[生成局限](https://developers.openai.com/api/docs/guides/image-generation)、[对照与持续评估](https://developers.openai.com/api/docs/guides/evaluation-best-practices)。审美评测是工程迁移应用，尚无已验证识别准确率。固定商品/文字层及兼容的结构/图像条件控制属可选路线，当前未部署，不静默换服务、安装模型或训练。
