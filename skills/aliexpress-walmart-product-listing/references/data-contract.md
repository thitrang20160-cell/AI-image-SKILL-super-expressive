# 规范化批次与只读审计器

`scripts/audit_batch.py` 是可选的确定性核对工具。它不解析任意业务系统的原始 JSON，不调用网站/API，不执行发布，也不证明记录中的观察或审核是真的。先把本批实际证据规范化成以下合同；原始证据仍保留，路径相对 `batch.json` 所在目录或使用绝对路径。

## 批次字段

```json
{
  "batchId": "EXAMPLE-US-BATCH",
  "destinationCountry": "US",
  "currency": "USD",
  "scopeSkus": ["EXAMPLE-001"],
  "storeId": "example-bound-store",
  "inventoryTarget": 0,
  "preserveCopy": true,
  "allowedImageHosts": ["images.example.com"],
  "watermarkPolicy": {"requiredChannels": [], "waivedChannels": [], "waiverEvidenceRef": null},
  "authorization": {"push": false, "storeId": "example-bound-store", "estimateMeasurements": false},
  "products": []
}
```

美国USD价格规则默认读取本技能的 `project-profile.json`；新任务不同规则用批次 `pricePolicy` 明确覆盖。脚本只实现该美国项目的四个价格分组，其他国家/币种先调整规则实现，不能直接标通过。

`scopeSkus` 是本轮实际做的集合，不是250个总目标。`storeId` 为指定绑定店铺，不能用显示名代替唯一ID。`inventoryTarget` 遵循用户授权；带估算测量值的本项目必须保持0。

2026-10-14以后的新选品批次设置`selectionGateRequired=true`。每件增加`selectionReview.traffic`及`selectionReview.profit`，各含`status=pass`和可读`evidenceRef`；profit另带`approvedRetailPriceUsd`，必须等于本次售价。依据文件应含[流量、利润与竞品闸门](traffic-and-profit.md)的实际核验及测算，而不只是手填pass。审计器检查存在和价格绑定，不代替真实证据审查。既有批次不因缺新字段被追溯改价。

## 每个产品字段

```json
{
  "sku": "EXAMPLE-001",
  "storeId": "example-bound-store",
  "source": {
    "url": "https://www.aliexpress.com/item/1234567890.html",
    "selectedVariant": "Blue 1 Pc",
    "observedAt": "2026-10-13T10:00:00Z",
    "evidenceRefs": ["evidence/source.txt"],
    "lockedAttributes": {"color": "Blue", "packCount": 1, "lengthCm": 150}
  },
  "procurement": {
    "itemPriceUsd": 0.99,
    "shippingUsd": 0,
    "freeShipping": true,
    "promotion": {"active": true, "eligibility": "New customer first order", "limit": "One per qualifying account"}
  },
  "listing": {
    "title": "Actual approved title",
    "features": ["Actual feature"],
    "description": "Actual approved description",
    "attributes": {"color": "Blue", "packCount": 1, "lengthCm": 150},
    "claimReview": {"status": "pass", "evidenceRef": "audit/copy-review.json"}
  },
  "originalCopy": {"title": "Actual approved title", "features": ["Actual feature"], "description": "Actual approved description"},
  "brand": "Actual authorized brand",
  "brandAuthorizationEvidenceRef": "evidence/user-brand-confirmation.txt",
  "retailPriceUsd": 3.99,
  "inventory": 0,
  "measurements": [{"field": "packagedWeightG", "value": 40, "status": "measured", "evidenceRef": "evidence/weight.txt"}],
  "images": [],
  "schemaValidation": {"pass": true, "version": "current-official-version", "evidenceRef": "audit/schema-validation.json"},
  "identifiers": {"productId": "CUSTOM", "productIdType": "GTIN", "exemptionRequestAuthorized": true},
  "official": {"itemStatus": "INPROGRESS", "catalogFound": false, "exemptionStatus": "APPROVED", "evidenceRef": "receipts/item.json"}
}
```

示例值不是可用商品数据。合同仅要求 features 为非空实际要点列表，不把示例1条当平台标准；真正数量以当前类目和用户要求为准。`lockedAttributes` 用规范化事实键/单位，一致性审查后的 listing 属性应逐键相同；品牌/卖家声明放独立字段，不伪装为供应商事实。

实际新增的 listing 功能、材质、认证等须逐条在 claimReview 核实。仅填 `pass` 不能代替审核；脚本只能要求有可读的依据文件，不能看懂产品或证明文件真实。

## 每张图片字段

2026-10-16后的新制/返修批次设置 `visualGateRequired=true`，新增图必须附下述 `visualPipeline`；审计器现场调用生图skill的 `visual_production_gate.py`。老批次未启用时给出legacy警告，不追溯改写已完成记录，也不能据此声称已执行新版检查。

```json
{
  "visualPipeline": {
    "requestRef": {"file": "production/request.json", "sha256": "实际请求文件SHA256"},
    "reviewRef": {"file": "production/review.json", "sha256": "实际审核文件SHA256"},
    "deliveryReportRef": {"file": "audit/delivery.json", "sha256": "实际交付报告SHA256"}
  }
}
```

request的sku、purpose、slot_role与本件/图型一致；feature-1/2的purpose为feature，scene-1/2为scene。deliveryReportRef在交付字节不同于原候选时必需，要求最终哈希与同一新版视觉证据链一致；旧报告的pass不替代当前文件核对。

原样复用旧图可改用 `reuseExisting=true` 和 `reuseManifestRef: {file,sha256}`。该manifest须保留assets数组，对应项SKU/role/sha256完全一致、finalApproved=true，原文件仍存在且同哈希。只限已认可的相同字节，不是重绘免检。批次 `rejectedImageSha256s` 保存用户本轮退回图的真实哈希；即使旧manifest曾通过，也禁止这些图复用。人工认可与撤回范围仍须真实取得，脚本不证明用户原话或图片内容。

```json
{
  "role": "master",
  "file": "final/EXAMPLE-001-master.png",
  "sha256": "actual-64-hex-content-hash",
  "url": "https://images.example.com/EXAMPLE-001-master.png",
  "hostedSha256": "actual-64-hex-content-hash",
  "httpStatus": 200,
  "visualReview": {"status": "pass", "method": "creator-self-review", "evidenceRef": "audit/master-review.json"},
  "watermark": {"sha256": "actual-64-hex-content-hash", "synthid": "not_run", "trustmark": "negative"}
}
```

本项目图序为 `master, feature-1, feature-2, material, scene-1, scene-2, dimensions`。其他图数/职责在批次 `imageRoles` 明确覆盖。

水印状态为 `negative / positive / unknown / not_run / error`。按用户实际要求填 `requiredChannels`，不要自动强制所有检测器。用户跳过的渠道列 `waivedChannels` 并附原话依据；已知阳性不会因“跳过剩余检测”自动成为通过。明确接受已知阳性须另记 `knownPositiveAccepted=true` 和 `knownPositiveAcceptanceEvidenceRef`，仍保留阳性标签。

图片发生后处理时添加 `postprocessed=true` 及 `postProcessReview`，按最终文件哈希绑定复检。哈希核对不证明图像内容真实；视觉观察还需执行生图skill审核。

## 阶段与结果

- `stage`：核对本轮SKU/店铺集合、源页与锁定属性、采购价规则、文案锁定、图序/文件/托管哈希、审核证据、测量来源和库存目标。
- `push`：增加指定店铺推送授权、确认品牌、有效销售价及当前schema校验记录。`CUSTOM/GTIN`需要 `identifiers.exemptionRequestAuthorized=true`；否则提供真实非占位编码及对应证据。完整商品schema仍由官方schema验证器负责。
- `acceptance`：在push核对基础上，要求每件 `official.itemStatus=SUCCESS`、`catalogFound=true`、目录售价与目标价一致、`inventory.quantity`及`inventory.shipNode`与授权目标一致，并有实际回执依据。豁免批准或feed完成均不足以通过。

结果包含 `ok`、`errors`、`warnings` 和逐SKU价格分组；失败退出码为2。默认只输出stdout。可用 `--report ./work/report.json` 保存结果，输出目录由使用者指定，不覆盖输入证据。

回归工具 `scripts/test_audit_batch.py --workdir ./work/tests` 只生成合成测试文件、调用只读审计器，不生图、不读取账号、不联网、不发布。
