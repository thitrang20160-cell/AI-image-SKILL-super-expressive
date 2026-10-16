# 提示词结构与书挡试验

输入图角色 → 用途 → 卖点/创意动作 → 商品锁定 → 镜头与空间 → 材质/光影 → 文案区 → 排除项 → 输出与评审。

产品参考决定身份，风格参考只传递镜头/材质表现/留白等选定特征。几何约束优先于风格，装饰不能遮住必须验收的底座和接口。

## A：商品英雄图

Use case: product-mockup. Create a premium product campaign candidate for the exact bookends in product reference 1. Style reference 2 supplies only large-subject composition, controlled highlight rhythm and a restrained pale gray background, not its objects, text, branding or claims. Preserve exactly two matching arch-top light wooden boards and their black hollow rectangular wire feet, attachment locations and visible proportions. Do not add solid plates or redesign bases. Compose both bookends in a deliberate near-to-far diagonal, all essential geometry visible, strong but moderate low three-quarter viewpoint near the reference's visible angle. Use natural directional grain, matte wood sheen, crisp edges, broad soft illumination and subtle contact shadows. Clean warm gray studio field with clear upper-left copy space. No text, logos, books, awards, new hardware, sci-fi glow or collage. Output a realistic raster candidate for comparison against the source. Do not invent unseen geometry for a dramatic angle.

本配方可使用样本 7 的镜头/材质语言，但不能给木头套金属、线材或扣具。具体焦段只为视觉指令，不是生成图相机事实。

## B：把功能变成画面

Use case: compositing. Create a premium lifestyle candidate using exactly the pair of wooden bookends from product reference 1. Style reference 2 supplies only clean lighting, clear function-focused composition and text-free negative space. Communicate orderly books through one coherent close-up arrangement. Place a small row of plain books between two arch boards; keep both boards visible and expose enough of the original black wire feet to judge construction and contact. Feet must remain hollow rectangular loops and the books must be physically supported. Modest three-quarter desk-height camera, warm off-white negative space above, restrained wood surface, one soft side light and realistic contact shadows. Preserve the product's light wood appearance and board/wire proportions. No magnets, compartments, invented strength tests or dimensions. No text, branding, glow arrows or infographic. Output a single realistic raster candidate, not a collage. If geometry is unknown use the reference's known angle instead of inventing it.

本配方可借鉴样本 11 的操作/结果明确与简洁信息区，而不迁移其透明剖面、设备或参数。书挡的特写应展示可见木纹、板厚与底座连接。

## C：形态呼应 / 书页框景

Use case: ads-marketing. Product reference 1 is the only identity source. Style reference 2 supplies only a frame-within-frame idea and tactile material hierarchy, not its objects, logo or claims. Put the exact pair of light-tan rounded arch bookends on a pale tabletop with BOTH complete hollow rectangular black wire feet and all attachment points exposed. Behind them, related cream book pages form a large curved advertising frame echoing the product's arches, against a deep muted green field. The boards stay grounded; they do not hold up this page arrangement. Keep the reference board/foot proportions, count and visible construction. Paper, wood and satin black wire have distinct controlled highlights. No text; use actual resulting negative space for later editable typography. Reject hidden feet or altered product hardware; record any deviation in page binding or object count rather than treating the scene as physical proof.

这是广告搭景，不是书籍站在脚上的功能图。背景不完全按单本书连接时需记录偏差，不能把画面当真实纸页结构。第三轮实际完整提示词另见项目 `brief-v4.json`；实际输出与限制见 [第三轮实测](bookends-round-03.md)。


## D：原样本锚定的人物场景

当用户要求严格沿用样本时，先读 [样本风格锁定](sample-fidelity.md)。选择原图作为实际 style-reference，记录其画面拓扑、镜头动作、材质、配色和版式关系。当前书挡示例可用图 3 的“前景递送”作为主锚点、图 5 的低机位/简洁亮蓝空间为辅助：人物把书挡推近镜头，商品占近景，角色动作连向它，背景只建立阅读情境。它不是默认的书桌窗边照，也不需要纸页风暴、发光书或传送门。

实际生成提示词与审核见 [样本纠偏实测](bookends-scene-calibration.md)。新方向是否贴合样本看实际输出，不能把配方当成已经通过。

用户最新指定产品主导、手部参与即可。D 配方中的整个人物不是当前默认：选图 11 的“产品主体＋局部手操作”为主锚点，按需要用图 7 的紧凑材质近景辅助。只显示解释动作所需的手和前臂；产品的轮廓、材质与部件为第一视觉焦点。整个人物/露脸场景须符合用户后续明确选择。


## 验收与迭代

“高级”“8K”“电影感”不能代替机位、主体尺度、材质和明确卖点。迭代记录具体变化，例如“保留当前构图，只恢复矩形底座与两个连接点”。同一个结构问题两次仍失败时，换可核实角度或固定层，不继续称为真实 3D 重建。

最终调用采用的完整提示词、输出文件和评审另存实际试验记录，不能把配方当成已生成结果。
