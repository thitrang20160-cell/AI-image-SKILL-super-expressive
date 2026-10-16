# 配方检索、审核与沉淀

核心 SKILL 保持稳定，案例放在 `references/recipes/`，实图放在 `assets/recipes/`。检索只加载最相关的 1–2 张卡及本次用途的锚点。这是文件经验复用，不是训练模型，也不是已接入 ERP 的自动任务服务。

## 制作前检索

用当前商品的观察填写标签，不从旧案例反推商品。`morphology` 表示主体形态，`action` 表示本图动作，`purpose` 表示图片职责，`style` 表示设计语言；`category` 仅辅助。标签采用已有卡的词汇，可通过 `list` 查看。强匹配仍需比对实图与当前 brief，确定没有未覆盖的新操作或结构。

```powershell
python <skill-root>/scripts/recipe_library.py list
python <skill-root>/scripts/recipe_library.py find --morphology handheld-contact-appliance --purpose material --action hard-soft-contact --style tactile-editorial --route ai-reference-guided --category garment-care
python <skill-root>/scripts/recipe_library.py find --morphology flexible-linear --purpose feature --action insert --style technical-studio --route ai-reference-guided --category electronics
```

返回 `reuse-with-review` 表示能省去重新探索视觉方向；`adapt-one-anchor` 表示只可借部分关系；`explore` 表示没有适用卡。排名是本地标签匹配规则，不是模型置信度或质量分。保真路线不同、图片用途未支持、形态不匹配时，不强套旧配方。商品主图和结构图尤其不能复用广告卡直接出图。

卡里只迁移镜头/主次、文字与物体的关系、动作及光影方法。商品图、颜色、部件、Logo、参数、适配对象和文案来自当前 SKU。参数槽位没有依据就删掉，不能沿用样例数字。参考锚点需查看后传为 `style-reference`；它不能替代当前 `product-identity`。

## 探索成本花在哪里

无匹配时先做一个代表方向（需要对比才做第二个），审核商品、关系和风格，通过后扩展已授权套图；不一开始试遍所有图型。已匹配时直接编译新商品 brief，省掉同样的构图试验。局部失败只修相应问题，结构连续两次失败转保真路线。

复用也需有变化：保持视觉家族，按新商品改变镜头距离、文字尺度/方向、作用点和材料状态。不要把种子图的完整摆位复制成全类目固定模板。套图逐职责检索，例如挂烫机的衣料接触有经验，不代表净水器的透明流路也有。

## 入库层级与边界

| 状态 | 依据 | 下次怎么用 |
| --- | --- | --- |
| `reference-library` | 公开包保留图像与方法，私有审核回执未分发 | 仅作参考起点，evidence_level为reference-only，逐图重新审查 |
| `candidate` | 初次探索、尚未完整审核 | 不进入默认检索；可继续本任务迭代 |
| `user-style-approved` | 用户认可审美，已有实图及制作自查 | 作为有限范围风格种子；保留商品/微观细节未知项 |
| `reviewed-local` | 一项当前用途经独立上下文 AI 视觉审核通过，记录可追溯 | 在该形态、用途、动作和路线内复用，逐张再审 |
| `cross-product-validated` | 同一配方、同一用途，在至少两个不同 SKU 的相容形态上有通过记录 | 同一范围内较强复用；仍不宣称全类目适用 |
| `deprecated` / `rejected` | 新反例或审核不通过 | 从默认匹配排除，旧文件保留便于回滚 |

首次通过只添加配方，不自动改核心 SKILL。单张通过只给该用途加入审核支持；同套其他用途维持种子或候选状态。跨商品的相同方法反复成立，且能说明哪些变量变化、哪些关系不变时，才考虑提炼核心。去重时保留更清楚、证据更完整的一张卡及版本记录，不把每个成功商品都变成一个新 SKILL。

用户本次授权维护技能，可写入这些经验；未来任务是否持久化沿用其用户授权范围。技术入库检查不扩大授权。审美新方向可在 AI 通过后先进入 `reviewed-local`，已有用户要求严格跟样本时必须通过风格闸门；人类修正持续优先于 AI 判断。

## 可执行入库

1. 将本次 brief、当前原图/文案证据、实际成图及审核服务的真实执行记录保存在该任务目录。
2. 按 [审核协议](visual-review-protocol.md) 生成逐张 JSON。先保存审核，再核验文件哈希；未知项不伪造为 pass。
3. 在候选卡写新的整数 `version`、相同 `id` 和精简关系/失败修复，删除旧 SKU 的具体参数与操作对应。不得把跨用途支持范围扩大到未审的图。
4. 先检查，再入库：

```powershell
python <skill-root>/scripts/recipe_library.py check-review --review <actual-review.json>
python <skill-root>/scripts/recipe_library.py promote --card <candidate-card.json> --review <actual-review.json>
python <skill-root>/scripts/recipe_library.py validate
```

`promote` 检查实际引用文件、哈希、审核身份、全部硬闸门及卡片范围，然后保存一个不可覆盖的新版本并更新轻量索引；已有版本不改。检查失败不写入。种子卡的历史人工反馈不能走独立 AI 通过通道。脚本验证记录完整性，不判断图像，也不能证明一个伪造的执行回执是真的；服务端未来应使用可信审核任务回执绑定输出哈希，而不是接受任意客户端“pass”。

## 审核校准和失败库

审核输入原始商品依据、用户风格锚点、用途/准确文案和候选图，先不提供生成器自评分。将“模式引线指错”“编织过粗”“标题平铺”“手未真正操作”等具体现象对应到局部修复；只给当前用途加载相关失败提示。

挂烫机的原错误控制图与修订图可作为文字映射反例；同一审美图里微观结构不清楚时保留 unknown，而不是要求审核员凭空确认。用户反馈与 AI 冲突时保存分歧，复核证据；不能靠更多自评分投票压过用户指定风格。换生成工具或模型后先复测一个代表图，不沿用历史通过标签。

## 衡量是否更省

每次记录配方命中、生成/修订次数、实际耗时、可见 token 与费用回执、各用途一次通过率及用户改稿情况；缺回执写 null。对相近复杂度、相同图片职责和保真路线比较首次探索与后续复用。审核本身也有成本，净节省应减去审核开销。没有测量前不写节省百分比。缓存稳定 brief/来源文件可以减少重复整理，但 SKU/变体、来源改动、参数或品牌文案变更时重新核实。

技能按需加载有助于减少无关上下文：[官方 Skills 文档](https://learn.chatgpt.com/docs/build-skills)。图像审核应分开硬闸门与审美、绑定真实输入输出，并用人类反馈校准：[官方 Image Evals 示例](https://developers.openai.com/cookbook/examples/multimodal/image_evals)。本文的检索、状态和入库策略是本项目工程设计，不是 OpenAI 自动学习功能。
