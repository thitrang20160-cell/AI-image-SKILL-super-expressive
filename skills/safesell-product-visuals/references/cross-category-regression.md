# 12 个视觉家族实测：v1.3

本轮实际完成 12 个沃尔玛商品的参考引导广告图测试；12 个通过独立视觉审核并限定范围入库。实际生图 20 次，其中修订 8 次。

| 类目 | 当前商品 SKU | 图型 | 调用 / 修订 | 状态 |
| --- | --- | --- | --- | --- |
| 家具家居 | 15689309055 | campaign | 3 / 2 | reviewed-local |
| 厨房厨具 | 32958517 | operation | 2 / 1 | reviewed-local |
| 清洁家电 | 2182471405 | hero | 3 / 2 | reviewed-local |
| 电子数码 | 5433539246 | feature | 2 / 1 | reviewed-local |
| 宠物用品 | 877788390 | feature | 2 / 1 | reviewed-local |
| 户外园艺 | 19864126 | material | 1 / 0 | reviewed-local |
| 运动健身 | 685169867 | material | 1 / 0 | reviewed-local |
| 工具家装 | 251417300 | campaign | 1 / 0 | reviewed-local |
| 美妆个护 | 625527254 | campaign | 1 / 0 | reviewed-local |
| 服饰箱包 | 17472857032 | use-scene | 1 / 0 | reviewed-local |
| 食品饮料 | 47217461 | campaign | 2 / 1 | reviewed-local |
| 玩具母婴 | 405352430 | operation | 1 / 0 | reviewed-local |

每张卡只支持已审核的 `形态 + 动作 + 图型 + 设计语言 + 路线`。一个 SKU、一种图型只记 reviewed-local；不代表该商城大类的所有商品和主图、场景图、材质图都已验证。原充电线和挂烫机配方仍为 user-style-approved。

## 已执行的学习与回归

- eos source currently has a flip cap; generic pump-bottle assumptions would change SKU identity 修订：Set observed cap and package morphology before choosing operation 依据：`09-beauty/source.jpg`。
- Fisher-Price link redirected to current 405352430 variant; ring colors differ from common classic pattern 修订：Bind actual resolved SKU and observed ring count/order; obtain full-peg supporting source 依据：`12-toys/source-evidence.json`。
- v1/v2 small caption near tabletop remained upright and was rejected; v3 flat foreshortened lettering passed 修订：Separate axis-following callout text from surface-plane type, and explicitly define glyph foreshortening when surface-plane type is requested 依据：`01-furniture/review-v3.json`。
- v1 arrows pointed in opposite rotational directions and the rear headline lacked the specified bowl-rim overlap; v2 passed after both were repaired. 修订：Specify one motion axis and direction, with arrowhead positions on each side; name the actual occluding part instead of asking vaguely for depth. 依据：`02-kitchen/review-v2.json`。
- v1 local copy opposed the product axis; v2 fixed copy but shortened a dock attachment; v3 passed with both restored. 修订：Define the baseline vector explicitly and re-audit full product plus accessories after text-only edits. Never give typography space by deleting product parts. 依据：`03-cleaning/review-v3.json`。
- v1 dropped YOUR from TAKE YOUR SOUND despite good type placement; v2 passed with complete copy and unchanged product. 修订：Check exact-copy word completeness separately from typography; reduce phrase size before omitting words. Applied a verbatim-copy gate to remaining ungenerated prompts. 依据：`04-electronics/review-v2.json`。
- v1 preserved water/product but put copy above the water and occluded the headline only with rim; v2 passed with flower overlap and water-adjacent copy. 修订：Use a camera and text plane that can support the named occluder physically. Place local functional copy at the actual action, not a convenient header space. 依据：`05-pet/review-v2.json`。
- The first candidate passed with the source closed jaw state, actual pivot/spring, fine grip grain and matching copy axis. 修订：For rigid material products, choose exterior surface contrast and the actual mechanical axis; do not force flexible-material deformation, invented cutaways or action claims. Explicit baseline vectors from prior failures were reused here. 依据：`06-garden/review-v1.json`。
- The first candidate passed with one continuous rolled/unrolled mat, source-scale ridges and copy following the actual straight mat edge. 修订：For flexible sheets, let continuous curvature and near/far scale express material; preserve one material and avoid inherited cable cross-sections or invented performance numbers. 依据：`07-sports/review-v1.json`。
- First candidate passed with correct bare-tool battery state, current source markings and axis-following copy, without invented operation effects. 修订：Use actual kit state as a hard identity constraint. Source package/device markings can remain; additional numeric advertising requires its own current evidence. Static shaft staging does not justify sparks or powered-action claims. 依据：`08-tools/review-v1.json`。
- First candidate passed with the actual flip-cap package, fine plastic and cloth material contrast, complete current package copy, rear headline overlap and fold-following fragrance caption. 修订：For personal-care campaign images, use verified package morphology and tactile mood to carry the design. Preserve package wording without adding skin transformations or ingredient effects; scope sensory props as context rather than product contents. 依据：`09-beauty/review-v1.json`。
- First candidate passed with continuous handles held by one cropped hand, plausible bag suspension, source seam/snap/wordmark identity and cloth-aligned secondary copy. 修订：For flexible carry products, trace the load path from hand to handle to fabric and check the full outline. Use deformation and selective lettering overlap without inventing capacity or load claims; retain source closures and seams. 依据：`10-fashion/review-v1.json`。
- First candidate passed with exactly five rings in the current source color/size order, one cropped hand lifting the smallest ring along the visible peg and full action copy. 修订：For modular toy operations, lock resolved SKU, total part count, order and the exact moved component before staging contact. Use a supporting source if the main image crops a controlling geometry; do not inherit unverified material, age or educational claims. 依据：`12-toys/review-v1.json`。
- v1 achieved depth but fully hid U/N in CRUNCH and received unknown. v2 exposed U and sufficient N contour while keeping package/chip overlap and passed the independent review. 修订：Treat occlusion and exact-copy readability as separate gates: never infer fully hidden letters from context. Reduce type or reposition the complete product without changing package geometry; re-audit all product and copy gates after repair. 依据：`11-food/review-v2.json`。

每次入库后实际检查当前与此前配方的检索命中、未审核用途/不相关形态排除、全部独立审核文件哈希及历史配方证据等级。视觉复核针对当次候选；检索回归是程序检查，不冒充重新生图或跨 SKU 验证。

本轮核验 20 份实际生成与独立审核记录；最终检索/文件回归 38 项通过，机制测试 27 项通过。后两组为程序检查，不计为视觉审核次数。

## 下次执行

1. 确认当前商品链接最终解析 SKU、件数、变体、材质纹理、盖口、接口和可见动作。只加载最相关的 1–2 张卡及必要实图。
2. 强命中复用设计关系，部分命中只借一个模块，无命中探索新锚点；当前事实和包装文案重新校准。
3. 查看实际候选并做独立审核。失败项对应一项具体修复；未通过候选不成为新风格锚点。
4. 同一结构连续两次失败时改用有依据的现有角度或固定商品层，停止靠遮挡掩盖问题。
5. 通过后沉淀范围明确的卡及真实输出、失败修复；至少另一个不同 SKU 在同一范围通过，才增加跨商品证据。

未知 token 和费用保持为空。此机制是按需检索经验，不是模型权重训练；不会承诺固定节省比例或首次必过。

公开分发说明：历史执行回执不在本仓库。图片仅供设计关系参考；当前SKU逐张重新核验，不将历史摘要当公开审核证书。
