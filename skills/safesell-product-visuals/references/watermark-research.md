# 隐形水印：检测渠道与方法边界

查证快照：2026-10-09。此页是研究结论，不是已经通过实测的像素水印去除配方。检测服务、模型和公开代码可能变化，实际任务重新确认可用性。

2026-10-13 补充：已加入 [检查、候选处理与复检](watermark-check-remove-recheck.md) 及可运行的低强度 SDXL 实验脚本。参考了 [wmr 作者方法](https://github.com/froggeric/gemini-watermark-and-synthid-remover) 与 [remove-ai-watermarks 研究记录](https://github.com/wiltodelta/remove-ai-watermarks/blob/main/docs/synthid-removal-research.md)：公开路线会重建图像，可能改变文字和细节，没有因此获得本批商品图的去除保证。是否有效以项目中当前阳性原件、处理后官方复检和保真审核为准；脚本新增不计为实图成功。

同日 [实际单图试验](watermark-pilot-20261013.md) 已运行一次，输出 TrustMark Q/P 未检出；官方 SynthID 后检两次服务错误、细节保真仍 unknown，因此没有当前实图去除成功结论。原图、实际参数、最终 SHA 和错误证据均已保存。

v1.5 已落地的多渠道检测、TrustMark Q/P 官方对照和实图复核见 [检测覆盖与对照](detector-coverage.md)。其中单路径 ECC 命中存在不稳定情况，按 unknown 保留；公开 remover 没有自动成为本项目已验证的去除步骤。

## 先识别检查对象

| 对象 | 可用检查 | 不能由此推出 |
| --- | --- | --- |
| C2PA / EXIF / XMP 文件记录 | 容器解析、清单和签名检查 | 删除记录不等于删除像素水印；字符串扫描不等于签名可信。 |
| 已知传统盲水印 | 对应算法/密钥/长度的解码器 | 任意解码输出不等于水印检出；LSB 或单个 DWT 解码器不是通用检测器。 |
| SynthID 等生成来源水印 | 来源支持的官方检测器 | 没有检出支持信号，不等于全部隐藏水印不存在，也不等于真人摄影。 |
| 一般 AI 图片分类器 | 分类模型的概率与适用数据范围 | 分类概率不是水印解码，也不能证明平台是否分流。 |

[invisible-watermark 作者实现](https://github.com/ShieldMnt/invisible-watermark) 支持 DWT/DCT/SVD 与 RivaGAN 等特定方法，解码需要相应参数，作者也提示原始解码并非百分之百准确。不要将其命名当成“扫描所有隐形水印”的能力。

## 当前官方入口

- [Google SynthID](https://deepmind.google/models/synthid/) 宣布公共 [SynthID Detector](https://synthid.com/) 支持 Google 及合作伙伴，包括 OpenAI 的受支持内容。公共网页入口不等于本机已能自动上传；记录实际登录、上传、结果与文件哈希。
- 对支持的 OpenAI 内容，使用 [OpenAI Verify](https://openai.com/research/verify/) 或 [内容来源检测 API](https://developers.openai.com/api/docs/guides/content-provenance)。C2PA 与 SynthID 结果分别读取；API 密钥是否存在与组织是否有接口访问权分别确认，不在报告或提示词中保存密钥。
- 未上传、连接超时、无访问权、接口错误、缺少适用结果均为 `unknown`。网页人工结果保留原始结果证据与 SHA-256，不冒充 API 回执。只有模型直接看图的审美审核不能替代官方像素检测。

## 去除研究候选

| 方向 | 公开依据 | 当前商品图的边界 |
| --- | --- | --- |
| 压缩、缩放、裁切、滤镜、降噪 | SynthID 官方说明其设计可耐受多种常见修改 | 可能削弱部分方案，不保证消失；压缩或截图不能自动验收为去除成功。 |
| 再生成 | [WatermarkAttacker](https://github.com/XuandongZhao/WatermarkAttacker)、[论文](https://arxiv.org/abs/2306.01953) | 在作者测试方案中有去除作用；改变文字、纹理、轮廓或接触关系就不能作为合格商品交付。不能外推当前 SynthID。 |
| 控制再生成 | [CtrlRegen](https://github.com/yepengliu/CtrlRegen)、[论文](https://arxiv.org/abs/2410.05470) | 作者用空间/语义控制减轻改图。其公开演示的 512 缩放和中心裁切会破坏竖版画幅，需重新设计几何与精确文案保护；未在本项目执行。 |
| 频域优化 | [UnMarker 作者实现](https://github.com/andrekassis/ai-watermark)、[论文](https://arxiv.org/abs/2405.08363) | 作者追加实验报告 SynthID 攻击成功约 79%，仍有约 21% 检出；不是本项目实测或彻底去除。标准运行要求至少 32GB NVIDIA 显存、CUDA 12 和约 30GB 存储。可能留下可见改动。 |

学术标题中的“通用”限定于论文假设和实验，不能迁移成所有模型/版本的百分之百保证。再次使用原生生成服务还可能引入新的来源标记，不能把重新生图直接记为无水印。

## 回归如何成立

采用 [WAVES](https://wavesbench.github.io/) 的核心评估思想：检测表现与图像质量一起记录。每次测试绑定原件、实际处理方法/版本、最终文件 SHA-256、支持的检测器与原始结果。需要有效的阳性原件基线，才能评价“原来能检出、处理后该信号未检出”；基线阴性或未知时不计算去除率。

商品质量同时核查 SKU/变体、结构、Logo、精确文字、纹理尺度、手部操作、画幅、光影和用户参考风格。像素误差或感知相似度只量化改动，不能代替商品质量审核或水印检测。未执行的方法单列 `not-executed`，不并入成功数量。

本项目 2026-10-09 对 22 张真实生成 PNG 做了 C2PA 副本导出回归：22 张声明记录清理通过，22 张解码像素完全一致，原件均未改；官方像素检测调用 0 次、像素去除执行 0 次、隐藏水印结果 22 张 `unknown`。这证明容器处理的完整性，也证明该操作保留原来的全部像素，不能作为隐藏水印去除证据。

执行后处理仍遵循 [真实性与生成后处理](realism-and-postprocess.md) 的实际状态和交付检查；研究方法尚未验证时，不登记为生产流程的已完成步骤。
