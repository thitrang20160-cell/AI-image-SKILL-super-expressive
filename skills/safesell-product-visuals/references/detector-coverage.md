# 检测覆盖与处理边界

实施快照：2026-10-09，技能 v1.5。扩展检测脚本只读原图，不是水印去除器；新增接口代码不等于已完成真实服务联调。不要把当前范围说成全检、没有水印或平台检测不到。

v1.10 补充：真实 Google SynthID 网页回执可作为受支持 SynthID 的官方替代证据，经 `delivery_gate.py --manual-pixel-report` 校验文件及截图 SHA 后合并；原 OpenAI API 报告及 v1 汇总不改写。输出单列有效覆盖与使用的来源，两个官方结果冲突则拦截。Google 阴性不解除 TrustMark 的未知/阳性，也不代替原始商品审核。当前已保留的实际网页阳性说明删 C2PA 后像素信号仍可能存在。

## 已实现的范围

| 渠道 | 对象 | 当前实现 | 尚未覆盖 |
| --- | --- | --- | --- |
| 本机 PNG 解析 | C2PA caBX 容器声明 | CRC、块计数、声明标记及副本清理验证 | JPEG/WebP 容器、签名/证书可信、云端关联来源。 |
| OpenAI 内容来源 API | 受支持 SynthID 信号 | 原始脚本只读上传一次，严格校验实际结果及 SHA-256 | 缺密钥、无接口访问权、错误和未上传均 unknown；不覆盖全部水印。 |
| 本机 TrustMark ONNX | TrustMark Q/P 载荷信号 | 官方模型、原版 MIT BCH/DataLayer；先运行阳性/阴性对照，再执行两个固定预处理路径的解码 | B/C、局部定位、旋转搜索、透明图、非默认 EXIF 方向、未知水印算法均未验证；不是 SynthID。 |
| Hive API | AI 图片分类概率 | V2 图片上传适配器及响应合同测试 | 本次缺密钥，真实调用 0；分类概率不是像素水印判定。 |
| Sightengine API | genai 分类概率 | 文件上传适配器及响应合同测试 | 本次缺凭据，真实调用 0；该模型分析像素，不使用 EXIF/C2PA/隐形水印作为判断依据。 |
| Google SynthID、Adobe Inspect | 各入口支持的来源检查 | 登记人工入口、未知状态及未来回执要求 | 本次无实际上传结果；不登记为自动化接口，也不代替其他渠道。 |

依据：[Adobe TrustMark](https://github.com/adobe/trustmark)、[OpenAI API](https://developers.openai.com/api/docs/guides/content-provenance)、[Hive 上传](https://docs.thehive.ai/docs/visual-content-moderation)、[Hive 分类合同](https://docs.thehive.ai/reference/ai-generated-image-and-video-detection-1)、[Sightengine](https://sightengine.com/docs/ai-generated-image-detection)、[SynthID](https://deepmind.google/models/synthid/)、[Adobe 内容凭据](https://helpx.adobe.com/creative-cloud/apps/adobe-content-authenticity/content-credentials/view-content-credentials.html)。不能由这些供应商文档认定沃尔玛使用某一家。

## TrustMark 对照与误报处理

`scripts/trustmark_local.py` 固定 Adobe 来源提交 `59bde8b41c973d2fac3be7ef89e3ac0fea2254fa` 的数据层实现，并绑定实际下载模型的 SHA-256。模型下载来自官方 HTTPS 地址，本地摘要是版本绑定，不冒充发布方签名或官方校验清单。

每次载入运行环境后先执行控制清单：Q、P 各至少一个已知阳性，以及各自的未加水印阴性。清单绑定原始文件 SHA，运行真实推理后保留预期、实际结果、模型摘要、代码摘要和运行库版本。对照缺失、哈希变化或失败时不给阴性结果。对照通过只验证当前接入，不证明总体准确率。

解码固定采用两个只读路径：官方 JS/ONNX resizer，以及源 Python 方法中的 PIL bilinear 归一化，后者使用当前 ONNX 模型声明的输入尺寸。输入只在内存中预处理，不修改文件。两条路径都使用纠错；版本位损坏时按官方 JS 的固定顺序尝试备用纠错模式，不以随机原始比特当水印。

- 两路 ECC 都通过且载荷摘要一致：`detected`，表示当前支持信号的稳定命中，仍不证明作者、平台行为或所有水印的完整情况。
- 两路都没有 ECC 命中：`not_detected`，仅限当前 Q/P 检查范围。
- 单边命中或载荷不一致：`unknown / unstable-ecc-hit-needs-review`，保留双方证据。不据此删除像素，也不把疑似命中清空为阴性。
- 输入超出验证范围、模型/运行库不可用或异常：`unknown`，不得将异常转换为 false。

双路径一致性是本项目的保守验证条件，不是 Adobe 提供的通用精度保证，也不能消除所有误报或漏报。

## 实际回归记录

本次官方不透明对照：2 张带标记样本分别通过 Q/P 稳定命中，1 张未加标记原件在 Q/P 均无命中。官方 ghost 样本有透明度，未纳入本次输入验证范围。

扫描此前 22 张真实生成图及 22 张 C2PA 清理副本，共 44 个文件、176 次 Q/P 模型推理（控制推理另计）：15 张商品图两路均无 Q/P 命中；7 张存在不稳定命中，保留 unknown；稳定阳性 0。原件与副本逐对结果一致，文件未变。首轮单路径的 5 张 ECC 命中被后续复核覆盖，不作为已确认阳性。

OpenAI/Hive/Sightengine 云端调用均为 0；44 个文件的 SynthID 结果均 unknown。像素去除执行 0，已验证像素去除 0；此前 22 张 C2PA 副本清理成立，解码像素完全一致。两个层次分别报告，不计算不存在的像素去除率。

项目证据目录：`output/imagegen/detector-expansion-20261009/`，以 `expanded-regression-results-v3.json`、`audits-v3/` 和当前 `trustmark-control-validation.json` 为准。v3 额外拒绝索引/RGB transparency 元数据，并严格检查 Hive 成功状态类型。旧报告与 v2 执行代码保留用于说明修复，不作为最新结论。

## 使用与交付闸门

```text
python scripts/detect_image_signals.py --input <最终工作副本.png> --report <新的扩展检测报告.json> --trustmark-model-dir <官方模型目录> --runtime-dir <可选隔离Python依赖目录> --control-manifest <对照清单.json> --cloud openai hive sightengine
python scripts/delivery_gate.py --image <最终工作副本.png> --review <视觉审核.json> --generation-request <实际生成请求.json> --metadata-report <声明处理.json> --pixel-report <实际OpenAI检查.json> --coverage-report <扩展检测报告.json> --report <新的交付状态.json>
```

模型需要 `decoder_Q.onnx`、`decoder_P.onnx`、`resizer.onnx`；运行库需要 numpy、Pillow、onnxruntime。资源不随技能自动安装或下载；模型变更需明确重验证。控制清单为 JSON 数组，每项包含 `file`、`sha256` 和 `expected`（Q/P 到 detected/not_detected）。对照预期来自已知样本，不由模型结果反填。

密钥只从当前进程的 `OPENAI_API_KEY`、`HIVE_API_KEY`、`SIGHTENGINE_API_USER`、`SIGHTENGINE_API_SECRET` 读取。必须明确选择 `--cloud` 才上传；不搜索其他用户文件中的密钥，不打印密钥或请求体，不允许凭据随重定向发送。Hive 需要对应 AI 图片检测项目的密钥；接口访问权仍需实际请求验证。

扩展默认像素范围是 OpenAI SynthID 加 TrustMark Q/P。任一必要渠道未知、疑似或已检出未处理时拦截最终交付；Hive/Sightengine 即使低分也不能解除拦截。报告引用必须与当前图 SHA 对应；旧图回执、伪造响应、不一致摘要或改变图后沿用原结果都不能通过一致性检查。闸门能核验文件和合同一致性，不能为人为捏造的回执作真实性证明。

## 检测后处理

已确认的 PNG C2PA 通过已有副本导出脚本移除，再核对像素/保留块和原件；不会触发重绘。像素命中则记录具体方案及支持范围，只有存在该方案的已验证处理能力、处理前真实阳性与处理后复检，并通过商品质量审核，才记为该信号已处理。

新增低强度 SDXL 实验候选与 before/process/after 检查器，实际方法见 [检查、候选处理与复检](watermark-check-remove-recheck.md)。没有当前文件的处理和复检证据时，不能登记为已验证去除。TrustMark 项目虽然公开学习式 remover，本技能仍只接入其解码，不把它当作 SynthID remover。疑似信号先复核；未知来源不盲目改图。每次改图都重新审核商品与声明、针对新哈希检查；最后状态仍有 unknown 时只保存工作稿。
