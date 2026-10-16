# 通用制作规格与提示词

这是按当前商品填充的规格，不是需要用户逐栏回答的表单。已有资料可直接提取，未知项保留 `null` 或未知说明；不以填写模板扩张任务。主图无文字、静物无动作等分支关闭无关字段。

## 可复用 brief

```yaml
version: '1.4'
sku: current-sku
category: current-category
variant: current-variant
image_type: campaign
review_set: false # 单张 false；完整图组 true，必须是布尔值
channel: local-demo
output:
  aspect_ratio: '3:4'
  requested_size: null
  count: 1
  typography_mode: editable-overlay
route: ai-reference-guided
recipe:
  id: null
  version: null
  mode: explore # reuse-with-review / adapt-one-anchor / explore
  transferable_modules: []
  excluded_modules: []
  morphology: null
  action: null
  design_language: null
product_identity:
  reference_files: []
  locked: [] # 件数、轮廓、接口/部件、颜色、可见纹理、附件与包装
  unknown: [] # 缺失视角、隐藏结构、精确尺寸或微观细节
references:
  style_primary: null
  style_secondary: null
  transfer: [] # 当前图确实要借的镜头、层次、材质、字物关系
  exclude: [] # 原样本的商品、品牌、数字、角色或内部构造
message:
  main_claim: null
  evidence: [] # 每项：claim, source, qualifier, checked_date
  exact_copy: []
composition:
  first_read: product
  camera: null
  foreground: []
  middle: []
  background: []
  action: null
  visible_result: null
  contact_points: []
  allowed_crop: []
spatial_type:
  enabled: true
  main: null # text, plane, position, scale, orientation_from, occluder
  local: [] # text, semantic_anchor, scale, orientation_from, clearance
  supporting: []
effects:
  enabled: false
  origin: null
  direction_from: null
  graphic_intent: null
  protect: [] # 接口、动作、字形、结构和主要材质
materials: [] # observed_material, texture_scale, reflection, highlight_limit
material_expression: # 普通细节图可关闭；广告张力分支见 material-tension.md
  enabled: false
  mode: null # exterior-behavior / contact-contrast / verified-reveal / measured-comparison
  observed_property: null
  action: null
  visual_result: null
  primary_region: null
  secondary_identity: null
  contact_or_force: null
  texture_anchor: null
  scale_constraint: null
  reveal_evidence: null
  claim_scope: null
palette: null
lighting: null
realism:
  mode: grounded-advertising # photographic / grounded-advertising；保留用户所选风格
  identity_route: null # fixed-product / verified-model / ai-reference-guided，按实际可用工具
  physical_locks: [] # 机位/尺度、光源、接触/遮挡、材质反射/透射与动作
  local_revision_scope: []
postprocess:
  metadata_policy: remove-c2pa # 当前用户偏好；保留生成原件，按后续任务覆写
  pixel_watermark_check: requested
  pixel_watermark_removal: requested # 当前没有已验证实现，不能将 requested 写成 done
  completion_before_delivery: true
  status: not-performed
human:
  presence: none # none / hands / cropped-body / model，按当前需求
  action: null
  crop: null
review:
  image: needs-review
  layout: needs-review
  spatial_type: needs-review
  interaction_effect: not-applicable
  physical_plausibility: needs-review
  overall: needs-review
  record_file: null # 逐张 review JSON；未执行不填 pass
learning:
  admission: candidate # candidate / reviewed-local / cross-product-validated
  user_style_approval: null # 审美认可单独记录，不等于准确性通过
  measured_tokens: null
  measured_seconds: null
  generation_calls: null
  revision_calls: null
  cost_receipt: null
```

`typography_mode`：`none` 为无字商品图；`editable-overlay` 为独立文字层；`integrated-raster` 为检验空间融合的一体候选，注明烘焙文字。图像尺寸以实际工具回执和文件为准，不能把 requested_size 当已达成。

## 编译为实际生图请求

从 brief 选已启用字段，写成以下自然语言顺序：

1. 用途、单张/套图职责、画幅与媒体。
2. 输入图角色：商品身份、风格、品牌、参数证据或编辑目标。指出哪个控制什么。
3. 商品锁定与未知边界。
4. 场景、镜头、前中后层、真实动作/可见结果与接触关系。材质张力分支写清主材料状态、次要身份线索、纹理相对尺度与是否有剖面依据。
5. 文字：准确文案、所在平面、与商品的前后关系、语义位置、尺度、由什么轴线/切线决定方向。无字分支明确不生成文案。
6. 已启用的局部特效：起点、方向、长度/强度意图，以及需要保持可读的结构；无特效分支省略。
7. 当前商品的材质、纹理尺度、反射、色彩与光线；结合 realism.mode 写入已确认的透视/尺度、光源和接触约束。真实性随此轮生成落实，不只留给导出后修饰。
8. 针对本次最可能漂移的少量禁项。不要把所有历史失败词堆到每个提示词。

文字方向要有理由，例如“沿扶手轴线”“沿瓶口出液方向”“顺拉链切线”“跟桌面透视”。不固定 -60 度、蓝色、S 曲线、两个接口或 480 Mbps。可编辑模式需要底图为对应文字关系预留位置与遮挡边缘；留白不等于全部图文分离。

## 定向修订

编辑请求写清“保持哪些内容，仅调整哪一主要问题”。全局构图不成立时另建版本，局部材质/接口可定向编辑。不得从生成图提取新参数、内部构造或商品事实。结构失败持续时按 SKILL 的停止条件转路线，不靠文字或特效遮错。

审核记录对应实际输出文件：商品身份/材质/使用关系、实际文案、字物关系、交互效果、参考偏离与跨图一致性。风格被用户认可可记 `style_approved`，剩余结构未核实仍保留；图片工坊业务队列、成本和平台发布状态各自记录，不能由技能完成推断已接通或已上线。
