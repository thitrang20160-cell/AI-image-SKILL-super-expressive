# 制作规格与审核

## 参考角色

分别标注 `product-identity` 原始商品依据、`verified-geometry` 核实模型、`style-reference` 审美参考、`brand-asset` 用户选定品牌素材、`copy-evidence` 参数证据、`draft` 已生成候选。风格图上的品牌与内部零件不传递到当前商品。

未显示的背面、底部、接口和内部结构记为未知。AI 生成的细节不成为事实。单张照片可以指导已知视角，不能保证真实 3D 重建。

## Brief 示例

```yaml
sku: BOOKENDS-EXAMPLE
request_id: local-brief-001
purpose: feature-image
route: ai-reference-guided
status: concept
product_identity:
  locked: [two boards, rounded arch tops, flat bottoms, light wood appearance, black hollow wire feet]
  unknown: [exact dimensions, wood species, weight capacity, underside details]
primary_message: Keeps books arranged neatly
creative_action: close low-angle composition showing the boards holding books
references:
  product: bookends-reference.jpg
  style: sample-07.jpg
  transfer: [large foreground subject, clean gray field, controlled highlights]
  exclude: [carabiner, cable, claims, source branding]
composition:
  aspect: '4:5'
  product_region: center-right
  copy_region: upper-left clear field
  perspective: moderate three-quarter low viewpoint
material_intent: directional grain, matte sheen; no invented metallic parts
lighting: broad soft key, restrained edge highlight, coherent contact shadows
copy:
  heading: Neatly in Place
  evidence_backed_numbers: []
preservation: reference-guided redraw; manually compare after generation
output: [textless image, editable copy layout, source-output comparison]
```

示例句子和摆位是试验方案。实际版面记录文字框、裁切和安全边距；用户有明确要求时替换。

## 有模型时

记录模型格式、单位、尺寸、零件清单、核实程度、缺失纹理和实际可用工具。CAD 需适当转换后才能进具体渲染工具，扩展名不等于已支持。

多个镜头复用同一核实几何和贴图。按需要输出商品 beauty、alpha/对象遮罩、接触阴影，必要时提供深度/法线/材质分区。透明商品还需处理反射、透射及背景影响，简单贴 PNG 不等于正确透明材质。

场景与商品地平线、透视、尺度、光源及反射环境匹配。与手、宠物、书或液体互动时检查接触点、穿插、受力和影子。Blender 的 Render Passes、Cryptomatte、Shadow Catcher 可供分层合成使用；实际能力需真实模型和渲染结果验证。[官方通道说明](https://docs.blender.org/manual/en/latest/render/layers/passes.html)。

## 文案与版式

- 一图一个主张，标题/解释/证据建立层级，不强求每张塞三个卖点。
- 精确 Logo、参数和文字尽量独立排版；AI 重绘的包装文字逐字符核验。
- 对比图定义比较对象、同一量纲和条件，数字不是装饰。
- “申请奖项”不同于“获奖/认证”；测试次数、销量与传输速度分别记录来源。
- 99.9%、耐折次数、功率、流量等需证据及适用条件，不能从样本迁移。
- 检查全尺寸、实际展示尺寸和缩略图；不声称固定字号适合所有尺寸。

生成模型对文字、跨图一致性及精确摆位仍有局限，分层与审核是控制步骤，不是必然一致的保证。[OpenAI 图片生成文档](https://developers.openai.com/api/docs/guides/image-generation)。

## 一票不通过

真实性按 [真实性与生成后处理](realism-and-postprocess.md) 从生成前控制。新候选将商品身份与 `physical_plausibility` 分开记录：后者核对本图可见的光源/接触阴影、反射/透射、纹理尺度、透视和作用关系；广告夸张按用途与风格依据判断，不统一降成普通摄影。生成后只定向修复局部问题，结构错误回到生成或固定商品路线。历史审核不追填为已执行新检查。

商品数量/主要几何错误；接口/底座/附件缺失或新增；出现依据不支持的内部构造；文案、品牌或数字错误；演示图冒充实拍/真实渲染；明显穿插、漂浮；混入不同 SKU 的特征。

广告可夸张叙事尺度，但陈述尺寸、承重、容量或结构的画面要和资料一致。广告产品悬浮可以成立，使用图里的书要被书挡实际支撑。

## 初版人工评分

当前用户要求严格跟随样本时，先执行 [样本风格闸门](sample-fidelity.md)：对照原始锚点的主次、镜头动作、材质、色彩密度和版式。明显偏离标记 `rejected-style`，下表的总分不能覆盖此决定。

| 维度 | 权重 | 可观察判断 |
| --- | ---: | --- |
| 商品身份与真实性 | 30 | 件数、轮廓、接口、附件、变体和参数与依据一致。 |
| 材质 | 20 | 纹理方向/尺度、边缘、粗糙度及透射区分，无统一塑料感。 |
| 光影 | 15 | 高光解释形状，阴影/反射/接触一致，无关键结构过曝。 |
| 镜头与构图 | 15 | 焦点明确、层次成立、留白可用、透视服务商品。 |
| 创意与表达 | 10 | 视觉动作对应卖点，不依赖无关道具与随机特效。 |
| 文案与系列可用性 | 10 | 文字可读准确、色调一致、裁切与图组互相支持。 |

这组权重只帮助决定修改优先级，当前尚无验证过的数值通过门槛。优先记录可观察证据和具体问题，不以主观总分宣布成功；缺参照时标为未核实。用途图另检查商品、动作和可见结果是否关联。图组逐张对照 SKU，再检查接头、材质、颜色和附件是否跨图漂移。

候选记录：依据、通过点、具体问题、未核实点、修改动作和状态。不给尚未生成的图打分。

视觉审核通过后仍须完成最新导出文件的声明处理和实际可用的像素水印检查。元数据清理成功不代表画面真实性或像素水印去除成功；用户要求的处理未完成时保留工作稿状态。

材质张力图另按 [材质动作与张力](material-tension.md) 检查第一视觉事件、形变/接触连续性、纹理相对尺度、揭示/对照依据及字物关系。只把纹理生成得更粗、更亮，不能算张力通过；AI 候选即使构图成立也可保留材质未核实。

## 实测

同一 SKU、原图和用途对比旧提示词与新方向。记录商品保真、构图、材质、缩略图识别、可读性、生成次数及实际可见费用；无费用回执记为未知。有模型再比较真实几何的两个角度，没有模型不做伪造 3D 验收。首轮无需全量复刻 11 张。

## 配方审核与入库

复用检索不代替当前 SKU 审核。新任务逐张用 [视觉审核协议](visual-review-protocol.md) 输出有实图、文件哈希和来源的检查记录，再按 [配方学习流程](recipe-learning.md) 判断是否归档。精确结构和当前参数重新核对；不可见结构不能因“旧配方通过过”而变成已核实。自动入库需要实际独立上下文的 AI 视觉审核执行证据；历史自查和用户审美反馈只作限定范围的种子经验。
