# 视觉审核角色与证据记录

审核实际输出，不审核提示词的承诺。输入按角色排列：当前商品原图、当前 brief/文案证据、必要的用户风格锚点、候选成图。先全图，再原尺寸关键局部与缩略图；SKU 外形、按钮图标、接口、接触点和重要文案必须看清。没看清写 unknown。

v1.11 新制/返修执行 [稳定视觉生产](stable-visual-production.md)：brief标记 `visual_production.version=1`，审核绑定实际 generation_request，并记录 inspection、comparisons、observed_copy 和 unresolved_defects。`visual_production_gate.py review` 校验这些记录；全尺寸/缩略图、原始锚点对照必须实际执行，不能为脚本通过预填。风格用户认可、制作自查、真实独立审核分别记录，SafeSellAI低风险不代替审美检查。

## 审核角色提示词

将下文用于实际 AI 视觉审核请求。不要给审核员生成器的自评分或“这张已通过”的预设。可用独立审核上下文时使用；只有当前制作角色能自查时，记录 `creator-self-check`，不能声称完成了独立审核。不得为执行本协议默认开子代理或外部 API；沿用实际可用工具和用户授权。

> 你是商品商业图片审核员。请对照输入原图、brief 和审美锚点，检查实际候选，而非评价生成提示词。先查商品身份/变体、文案与数字、真实接触及操作；任何明确错误判 fail，无法判断判 unknown，不能用漂亮或总分抵消。再检查产品是否第一视觉、材质相对尺度、用途表达、字物层次和局部效果是否沿真实作用点。关闭的模块可 not-applicable，但说明原因。给每项结论附具体可见部位与参照文件；记录非阻断未知项及适用范围。需要修改时给一个主要修改动作，指出必须保留什么。比较版本时根据可见证据选更好者，不默认偏爱新版本；判定不一致时保留分歧。最后返回约定 JSON，不推断隐藏结构、实测性能或销量。

## 硬闸门与审美

硬闸门 `product_identity`、`copy_and_claims` 必须 pass；`contact_and_operation` 有操作就必须 pass，无操作可 not-applicable。只允许未展示、与本图主张无关的细节进入 `nonblocking_unknowns`；当前图直接宣传的结构、材质、数字或动作不可移到这里逃避审核。

视觉检查：`style_match`、`product_priority`、`purpose_expression`、`material_scale` 必须 pass；`spatial_type`、`effects`、`set_consistency` 仅未启用时可 not-applicable。未知/失败都保留 revise 或 unknown，不平均成通过。材质图的纹理或操作图的作用点尚未核实，不能给该用途入库。

v1.4 新制作另检查 `physical_plausibility`：按 brief 的真实感模式核对可见光影、材质、透视/尺度和接触关系。明确错误为 fail、缺依据为 unknown，不能以风格分覆盖；历史 v1.3 记录没有执行该项，不追填 pass。画面审核不代替文件来源/像素水印检测，文件后处理另记最新哈希与实际检测结果，见 [真实性与生成后处理](realism-and-postprocess.md)。

用户审美认可与商品准确性分别记录。旧挂烫机/充电线案例登记为 `user-style-approved`：有实际图与制作自查，但没有独立 AI 审核回执。它们可指导审美，不能回填成历史 AI pass。

## JSON 记录

v1.9 的 `material` / 材质张力图另须逐项检查 `material_event`、`material_tension`、`material_scale`，提供当前图片的可见证据。只有放大特写时张力项 fail；缺少事件或无法判定空间关系时 unknown，整体不得 pass。`detail` / 工艺细节图不强制张力。不能因无内部资料或硬质材料不可弯曲而跳过张力，按材质分支改用真实接触和空间设计。历史记录保持原样，不追填新检查。

每张一个文件。以下是字段规格，示例状态刻意为未审核；执行后填写真实路径、哈希、brief 和具体观察。

```json
{
  "schema_version": 1,
  "review_id": "current-request-image-review",
  "recipe_id": "current-recipe-id",
  "recipe_version": 2,
  "sku": "current-sku",
  "purpose": "material",
  "reviewed_at": "actual ISO-8601 timestamp with timezone",
  "profile": {
    "morphology": "observed-shape-tag",
    "action": "observed-action-tag",
    "style": "chosen-style-tag",
    "route": "ai-reference-guided"
  },
  "reviewer": {
    "kind": "ai-vision",
    "independent_context": false,
    "model_or_tool": "actual reviewer",
    "execution_record": {"file": "actual-review-call.json", "sha256": "actual SHA-256"}
  },
  "brief": {"file": "actual-brief.json", "sha256": "actual SHA-256"},
  "generation_request": {"file": "actual-generation-request.json", "sha256": "actual SHA-256"},
  "output": {"file": "actual-output.png", "sha256": "actual SHA-256"},
  "sources": [
    {"file": "current-product.jpg", "sha256": "actual SHA-256", "role": "product-identity"},
    {"file": "current-claims.json", "sha256": "actual SHA-256", "role": "copy-evidence"}
  ],
  "style_references": [{"file": "selected-style.png", "sha256": "actual SHA-256", "role": "style-reference"}],
  "checks": {
    "product_identity": {"status": "unknown", "evidence": "actual observation and reference"},
    "copy_and_claims": {"status": "unknown", "evidence": "actual visible copy vs current brief"},
    "contact_and_operation": {"status": "unknown", "evidence": "actual contact or why inactive"},
    "style_match": {"status": "unknown", "evidence": "actual comparison with selected anchor"},
    "product_priority": {"status": "unknown", "evidence": "actual first-read hierarchy"},
    "purpose_expression": {"status": "unknown", "evidence": "actual visual message"},
    "material_scale": {"status": "unknown", "evidence": "actual texture relative to product"},
    "material_event": {"status": "unknown", "evidence": "actual material event; new material brief only"},
    "material_tension": {"status": "unknown", "evidence": "actual spatial or material relationships; new material brief only"},
    "physical_plausibility": {"status": "unknown", "evidence": "visible light, material, scale and contact vs chosen realism mode"},
    "spatial_type": {"status": "unknown", "evidence": "actual depth, scale, axis and location"},
    "effects": {"status": "unknown", "evidence": "actual origin, direction and extent or inactive"},
    "set_consistency": {"status": "unknown", "evidence": "actual set comparison or single-image scope"}
  },
  "nonblocking_unknowns": [],
  "inspection": {"full_size": false, "thumbnail": false, "evidence": "not yet inspected"},
  "comparisons": [],
  "observed_copy": [],
  "unresolved_defects": [],
  "judgment": "unknown",
  "main_revision": null,
  "user_style_approval": null,
  "metrics": {"generation_calls": null, "revision_calls": null, "elapsed_seconds": null, "input_tokens": null, "output_tokens": null, "cost_receipt": null}
}
```

哈希只绑定所见文件，不证明视觉判断正确；`independent_context` 必须如实。AI 未真实调用、没有执行回执，或来源仅为 AI 草稿时，不进入自动通过通道。平台主图另核实当前平台规定；广告审核通过不授权发布。

brief 另需明确 `composition.action`、`spatial_type.enabled`、`effects.enabled` 和 `review_set`，用于验证 not-applicable 是否真的关闭该模块。精确文案放在 `message.exact_copy`；有数字需当前 `copy-evidence` 文件。归一化执行记录从真实审核调用提取，至少含 `status: completed`、`review_id`、`output_sha256`、`model_or_tool`、`independent_context`、`returned_judgment`，并保留实际任务 ID 和原始响应的可追溯位置；不能自己制造一份“执行成功”来让入库脚本通过。

新卡使用现有配方卡形状，`purposes` 可包含计划图型，但 `audited_purposes` 由实际通过记录计算。不同用途不能互相代审。原图和通过样张连同配方保留，失败记录至少保留主要现象、原因假设与实际修复效果，避免学习到遮错或无效禁词。
