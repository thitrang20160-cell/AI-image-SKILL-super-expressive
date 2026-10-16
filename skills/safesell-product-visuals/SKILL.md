---
name: safesell-product-visuals
description: Direct and refine SafeSellAI product images with source fidelity, reference-bound style, spatial typography, executable input/review gates and evidence-bound postprocessing. Use for commercial listing sets, style drift repairs and requested watermark workflows; not ordinary UI design or unsupported engineering reconstruction.
---

# 塞星商品视觉导演

主流程和视觉分支在 [AI生图SKILL.md](AI生图SKILL.md)，制作前读取；保留现有外部调用路径。

v1.11：按样张制作、连续批次或返修时，执行 [稳定视觉生产](references/stable-visual-production.md)。记录实际参考图与调用参数，生图前运行 `visual_production_gate.py preflight`，成图实际对照后运行 `review`；缺风格原图、关键项未知或哈希过期不得放行。分图型保持张力，主图/尺寸按用途处理。已有认可无需重复确认，制作自查不冒充独立审核。

新增或返修图片在 `delivery_gate.py` 传入 `--generation-request`；沃尔玛编排同步启用新版批次闸门。脚本检查记录和字节，不代替视觉判断，也不自动接管服务器上传或发布。

用户要求检查和处理像素水印时，读 [检查、候选处理与复检](references/watermark-check-remove-recheck.md)。先验证当前阳性、实际处理和最终字节复检，再按文件记录有效性；未执行、服务错误和保真失败不当作完成。

素材、商品与文字的审核要求沿用主流程。像素处理不能覆盖原件或消除已有 SKU 一致性问题，最终交付条件仍逐项验证。

执行受阻时先定位具体步骤、保留错误、修复或换可行路线并复测；继续所有不受阻的补图、资料、属性和审核工作。单一检测服务故障不能暂停整批。只有实际外部条件阻塞的步骤保留待处理，不能把未完成目标报告为成功。

用户明确修改验收条件、跳过剩余检测时，记录原话与范围并停止这些检测；未知保留未知，不改写为阴性。继续已授权的商品核对、图床、暂存和表格交付，不重复索要密钥或再次确认同一限制。见 [源图锁定、修复与暂存恢复](references/source-locked-recovery-20261013.md)。
