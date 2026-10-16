# 真实性与生成后处理

## 真实性放在哪一步

主体的身份和物理关系在生成前确定，并随生图落实。生成后的审核用于发现偏差，局部修订用于修复明确问题；不要期待把结构错误的整图靠滤镜、噪点或最后一次重绘变成可信商品图。

| 阶段 | 必须落实 | 回退条件 |
| --- | --- | --- |
| 生成前 | 确认 SKU、变体、件数、轮廓/接口/附件、纹理尺度与已知尺寸；选真实商品层/可信模型或参考引导路线，标明未知项。 | 缺少当前图要宣传的结构或参数依据时，换有依据的表达。 |
| 生图时 | 光源方向、透视/尺度、接触/遮挡、重力与作用点、材质反射/透射、商品与环境的关系；保护精确 Logo 和包装文案。 | 商品比例、连接或操作错误时修正结构，不用装饰遮住。 |
| 生成后 | 对照原图逐项看身份，再审核光影、材质、接触、文字和风格；修正一个主要问题后复查整个商品。 | 结构/数量/身份错误回到生成或固定商品路线；同类结构连续两次失败沿用核心停止条件。 |
| 保存前 | 核对最终文件、声明处理、实际可用的水印检测、文件哈希与交付状态。 | 检测或去除未完成时不能登记为“全部处理完成”。 |

## 真实感与广告张力的两种表达

在 brief 中选择 `realism.mode`，不把“真实”统一解释成普通白底摄影，也不让广告张力改写商品事实。

- `photographic`：适合需要摄影感的商品/使用场景图。使用可信机位、透视、尺度和景深，焦点服务商品。材质细节由原图指导，主光、高光、接触阴影与环境匹配，避免所有表面统一塑料光泽、整幅画面异常锐利。微小表面变化依据素材，不为“骗检测”编造磨损、噪点或相机 EXIF。
- `grounded-advertising`：适合当前用户认可的建模广告语言。保留近大远小、宏观材质动作、空间文字、字物遮挡和真实作用点附近的短距离特效；先锁定商品身份与关键物理关系，再允许可解释的广告夸张。广告悬浮和巨型文字不冒充实拍、工程结构、测试证明或真实尺寸。

有可用实拍/可信渲染层时优先锁住商品层，再匹配 AI 环境的机位和光线；选择该路线不等于工具已经能执行。只能参考引导时仍称重绘候选。透明商品的背景折射、金属环境反射以及手部接触要一起匹配，不能用普通贴图替代真实关系。有手参与时沿用用户偏好的手/必要前臂，不靠露脸建立真实感。

生成后允许的定向微调：局部接触阴影、环境色匹配、明显穿插边缘、材质高光和精确排版。位图编辑仍用实际可用且符合 imagegen 规则的工具；固定商品层不得重新进入 AI 绘制。任何修改产生新版本和新的审核/导出记录。

## 最终保存前的实际步骤

先保存生成原件作为证据；用户所说“完成后再保存”指最终交付副本，不禁止为审核保留内部工作稿。

1. **完成画面与排版。** 真实性、商品身份、文案与风格分开审核。新审核增加 `physical_plausibility`，检查可见光影/材质/尺度/接触是否符合本图用途；只看不可见项时保留 unknown。旧 v1.3 审核不追填这一项。
2. **生成导出工作稿。** 完成需要的画幅、格式、排版和尺寸，再处理来源记录。保存生成原件、编辑来源与逐张审核，交付副本另存；以后重新编辑或重新编码会使旧检测记录过期。
3. **检查并处理文件声明。** 当前用户默认要求 `remove-c2pa`。PNG 的 C2PA 通常在 `caBX` 块里，生成服务名、AI 来源类型和加水印动作可位于同一份清单；移除整个清单可以一起移除这些记录。使用 `scripts/png_provenance_export.py` 创建副本，检查 PNG CRC、原件哈希、所有保留块和 IDAT 数据一致，并记录清理前后状态。它只处理容器元数据，不解码/重绘像素，不去除画面 Logo 或像素水印，也不为签名/证书背书。保留非 C2PA 元数据，尤其颜色、透明度、方向和任务需要的披露信息。JPEG/WebP 不通过改后缀或盲目重编码套用这个脚本，选实际可用的对应工具后再验证。
4. **按范围检查信号。** 先读 [检测覆盖与对照](detector-coverage.md)。`scripts/detect_image_signals.py` 分别记录 PNG C2PA、官方 SynthID、本机 TrustMark Q/P、Hive/Sightengine 分类及人工入口。TrustMark 先运行真实阳性/阴性对照，两条固定预处理仅有单边纠错命中时记 unknown。对支持的 OpenAI 文件，也可用官方网页或 `scripts/verify_pixel_watermark.py` 调用一次内容来源接口；脚本只读文件并绑定 SHA-256。云端需明确启用、可用密钥与访问权限；不存在时记录 unknown，不搜索其他凭据。分类概率不代替水印结果，超时或错误不记作阴性。
5. **安排隐藏水印候选处理与复检。** 实际检出时进入 [检查、候选处理与复检](watermark-check-remove-recheck.md)，核对工具授权、方法依据、硬件与资源，先运行一张阳性图。新增 SDXL 低强度候选脚本记录真实执行但默认 `removal_verified: false`；它会重建像素，必须再查官方信号及商品/文字。没有可执行路线时记录具体缺项；有候选路线时不以“旧版未接入”直接结束。`scripts/watermark_cycle.py` 核对 before/process/after 链和处理保真审核；只在前图阳性、实际改像素、后图未检出且处理保真通过时记本文件验证有效。未经这条链，不把加噪、截图、压缩、再生成或删除 C2PA 写成已验证去除。基线 `not_detected` 仍记 `removal: not-performed`，不统计为去除成功。
6. **再决定交付。** 用只读 `scripts/delivery_gate.py` 合并画面审核、声明处理、像素检测及必填 `--coverage-report` 扩展报告，重新核对实际文件与哈希；退出码 0 才代表当前指定条件满足。配方入库、声明导出或分类接口成功都不是交付成功。检测未知、疑似或已检出未处理时仅保存内部 `working/` 候选及报告，不放入最终下载包、不称完成。用户后来明确接受像素检测/去除限制时，才使用 `--accept-pixel-limitations`，并交付有明确状态的副本；该选项不覆盖画面、声明或报告一致性错误，不以等待时间代替接受。满足任务后保存 `delivery/` 副本和简短状态说明。

闸门返回前重新核对图片、原件及报告的哈希，检查期间发生变化即不通过。保存 `delivery/` 副本后，再核对副本 SHA-256 与通过记录的 `image.sha256` 一致；不一致时取消最终交付，重新检查实际文件。通过记录绑定具体文件字节，不是对路径永久有效的许可。

处理前后像素数据相同，只证明删除记录未改图；若原来有像素水印，它也保持原样。检测器的 `not_detected` 仅是该检测器支持信号的结果，不代表平台接受、真人摄影或流量分配。

## 可复用命令

以下命令从技能根目录运行；在项目目录执行时，将 `scripts/...` 替换为本机技能脚本的绝对路径。文件参数替换成当前任务实际文件，不沿用案例 SKU。命令本身不启动生图或替用户发布商品。

```powershell
python scripts/png_provenance_export.py --input <final-export.png> --output <working/metadata-cleaned.png> --report <working/metadata-report.json> --policy remove-c2pa
python scripts/verify_pixel_watermark.py --input <working/metadata-cleaned.png> --report <working/pixel-check.json>
python scripts/detect_image_signals.py --input <working/metadata-cleaned.png> --report <working/coverage.json> --trustmark-model-dir <models> --control-manifest <controls.json> --cloud openai hive sightengine
python scripts/delivery_gate.py --image <working/metadata-cleaned.png> --review <image-review.json> --generation-request <generation-request.json> --metadata-report <working/metadata-report.json> --pixel-report <working/pixel-check.json> --coverage-report <working/coverage.json> --report <working/delivery-status.json>
```

第二条命令从环境变量读取 `OPENAI_API_KEY`，不把密钥写到技能、命令行或报告。仅发往官方 `https://api.openai.com/v1/content_provenance_checks`，一次最多一文件；缺密钥时不发请求。网络失败如实返回未知，后续只按官方规则处理短暂错误，不通过重复查询优化逃避检测。

归一化规则：检测 `check_status != completed` 或哈希过期保持 `unknown`；有效 `detected` 保持 `pending-removal`，处理器结果另存；有效 `not_detected` 表示当前支持信号未检出。仅有真实 before/process/after 链及处理保真通过时才登记本图验证有效。原始回执保留，不将统一状态 JSON 冒充官方响应。交付验证器要求 physical_plausibility，旧样张缺这一项仍保留历史范围。

Google 网页证据可通过 `delivery_gate.py --manual-pixel-report <实际回执.json>` 作为受支持 SynthID 的官方替代渠道；OpenAI API 原始报告仍保留其真实 unknown，不改写为 completed。两个官方结果冲突时拦截，Google 阴性不解除 TrustMark unknown。先导出最终字节，再上传对应文件，避免沿用旧路径、旧截图或旧 SHA。

可在网页 [OpenAI Verify](https://openai.com/verify) 上传实际文件；将返回结果与该文件哈希一起保存，人工检查结果不能伪造为 API 回执。[官方文档](https://developers.openai.com/api/docs/guides/content-provenance) 区分 C2PA 来源记录与 SynthID 像素水印；其检测范围不是所有生成器的所有隐形标记。调用前核实接口仍可用。

另有 Google 公共 [SynthID Detector](https://synthid.com/)，官方宣布支持 Google 与包括 OpenAI 在内合作伙伴的受支持内容。需要实际上传和结果证据，不能把可打开入口当作检测已执行；方法及适用边界见 [隐形水印检测与研究边界](watermark-research.md)。

## 状态记录

```json
{
  "source": {"file": "generator-original.png", "sha256": "actual source hash"},
  "working_export": {"file": "working/metadata-cleaned.png", "sha256": "actual export hash"},
  "realism": {"mode": "grounded-advertising", "identity": "unknown", "physical_plausibility": "unknown", "style": "unknown"},
  "metadata": {"policy": "remove-c2pa", "status": "not-performed", "retained_image_data_identical": null},
  "pixel_watermark": {"detector": null, "checked_sha256": null, "outcome": "unknown", "removal": "not-performed", "receipt": null},
  "delivery": {"status": "working", "requirements_met": false, "limits": []}
}
```

这些是未执行状态示例，不是验收回执。缺失的画面、元数据和像素检测分别保留未知；不让任一项代替另两项。
