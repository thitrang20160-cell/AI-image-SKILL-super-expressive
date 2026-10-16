# 沃尔玛暂存、推送与恢复

对按2026-10-14新逻辑选出的SKU，入本阶段前核对流量和利润两个前置闸门及获批售价。当前采购成本、佣金、运费或配送模板变化时先重算；不能以暂存或已生成图片代替利润通过。原有已完成商品不因新增规则自动改价或重推。

## 目标与外部服务

确认使用者指定店铺的绑定ID、显示名、市场、环境及凭据可用性；不把密钥复制进skill或日志。已有授权接口可用时直接复用，无需重复登录。公开仓库提供本地审计和图床实现，生图/合规服务/卖家账号由使用者配置。

卖家应用适配器需要店铺/节点读回、暂存upsert/读回、feed提交/逐件状态、目录/价格/库存读回。参考仓库的 `docs/service-adapters.md` 和 `config/runtime.example.json`；没有私有后台的固定文件路径依赖。调用实际接口保持原业务校验，不能直接改数据库伪装成功。只加载必要函数，不启动整套服务器或定时任务来完成一次性调用。

## 暂存与幂等更新

建立本次允许的店铺和 SKU 集合、目标库存与预期旧版本。在任何写入前，检查所有待更新商品是否仍等于预期快照；有并发修改先定位差异，不能盲盖。

使用现有暂存 upsert，保留已有暂存 ID；读回商品对象，逐项比较标题、五点、描述、源属性、售价、库存、品牌及顺序 URL。对非本批/非本店记录比较摘要，证明没有误写。暂存读回成功不代表沃尔玛已接收。

## 当前 Product Type schema

通过官方 API 获取当前美国站 taxonomy、spec版本、每种 Product Type 的 Orderable、Visible、required 和条件必填。不要只按标题猜分类或沿用旧模板；完整 root/header 也要验证。

明确单位和对象：ShippingWeight 通常按当前 schema 为磅；实物单件、整套外形和包装/物流尺寸不混用。克转磅使用453.59237并遵守 schema 小数步长，记录取整方式。JSON schema 的 multipleOf 校验同时用 Decimal 解析数据和 schema，避免二进制浮点导致误判或 Decimal/float 类型错误。

用户授权估算的尺寸/重量要标明来源为估算。估算是建品数据的临时选择，不是实测或物流报价；本项目库存为0，备货发货前校正。没有估算授权时，缺失值留待核，不用 feed-builder 的0.5lb等默认值补造。

品牌、制造商、原产地、保修与 Prop65 分别取证。品牌不是制造商/原产地的推断依据。卖家委托制定的书面保修或预防性警告政策须记授权，警告的适用文字和实物标签按当前官方规则核实；不能把未知化学检测、认证或保修写成已确认。

本次 scope adapter 曾遇到 header 多余 `tenant`，完整 root schema 拒绝；根据实际 schema 移除该多余字段后通过。不能由此推断未来任何版本都禁止 tenant；校验当次取得的 schema。不要为本批问题顺手改全局生产 builder。

## GTIN / UPC

真实编码须对应此卖家/商品且有效；不能借用竞品条码或生成看似数字的占位UPC。当前官方 `MP_ITEM` 支持有资格的无编码商品使用 `productId="CUSTOM"`、`productIdType="GTIN"` 发起豁免，必须实时核官方文档和授权。

豁免请求可以自动批准、拒绝或人工审查。用 `/v3/items/gtin-exemption/status` 按当前品牌及Product Type核结果，保存submissionId和时间。`Feed PROCESSED + item INPROGRESS`可能是豁免审查，不能反复重传同一数据。

官方要求获批后等待4小时再建品。只有submissionTime时不能冒充approvalTime；可用首次确认全部批准的观察时刻保守计时，并标明计算依据。到时先查现有SKU：已创建的只核对，不重复建；父feed已SUCCESS但目录暂不可见时先等待同步。仍不存在、豁免有效且条件已满足时，重传准确的未完成SKU一次。

等待不等于自动任务授权。用户要求稍后自动继续时按调度工具安排，提示词限定本批、查重、库存和实际验收；用户选择手动继续则保存恢复入口，禁止后台偷偷提交。

## 实际提交与状态

1. 上架前核对当前 store/name/mart、SKU集合、价格来源、库存目标、当前全部图URL及完整schema。验证活跃 fulfillment shipnode，不从旧店继承节点。
2. 每次 payload 独立保存，记内容哈希、requestId、父feed和修正依据。提交前写exclusive ledger；已存在ledger先查现有结果，不能删除ledger重跑。
3. 通过现有 `submitMpItemFeed` 等业务接口保留品牌/发布闸门。不得修改白名单来强行通过；用户已有合法品牌信息和现有白名单时直接沿用。
4. 保存实际ACK/feedId，登记现有业务feed历史与上传归档。网络超时记“提交结果未知”，先检索现有feed，不能将未知当作失败后盲重传。
5. 查询逐件feed结果，核收到/成功/失败/处理中数量和每个SKU的错误路径。只重传实际失败或有官方要求需重提的SKU；一次错误不能触发整批重复建品。
6. 保存旧失败记录，新attempt链接父feed。按实际结果同步feed历史、上传归档和暂存状态，不把旧错误留在当前视图，也不删历史掩盖失败。
7. 逐 SKU 查官方目录和指定节点库存，确认价格、品牌、itemId/生命周期及目标库存。若用户指定库存0，不为让商品“可售”而改正库存。

请求层GET 401自动续 token 不代表可重复未知的POST。429/5xx按官方退避处理，重试应有依据且不放大业务写入。JSON stdout 应等待缓冲区写完再退出，避免大回执被 `console.log(); process.exit()` 截断。

## 验收与外部阻塞

正式完成至少有：每个SKU官方建品成功或可解释的已存在目录证据、指定店铺目录读回、售价一致、库存读回与用户目标一致，以及文案/图/属性一致性记录。库存0的商品可能不可购买，这符合本项目目标；“可售”另行核验。

若官方返回实际缺项，保存路径/错误码，核原链接完整规格和已有记录，修复后做完整验证再提交。schema通过不保证业务摄入成功。平台处理中、需要真实资料或凭据权限时，说明准确未完成项，继续完成其他SKU、图床、表格和恢复准备；不以“有错误”结束可修的工作。

## 官方资料入口

- [Item setup中的GTIN豁免](https://developer.walmart.com/us-marketplace/page/request-gtin-exemptions-during-item-setup)
- [豁免状态与人工审查后的重提](https://developer.walmart.com/us-marketplace/docs/viewing-my-gtin-exemption-status)
- [获批后的四小时生效要求](https://marketplacelearn.walmart.com/guides/Item%2520setup/Troubleshooting/request-a-gtin-exemption)
- [指定SKU库存读取](https://developer.walmart.com/us-marketplace/reference/getinventory)
- [目录SKU读取](https://developer.walmart.com/global-marketplace/docs/get-item-details)

上述行为在2026-10-13已核实；未来执行刷新对应市场和当前版本，不把本次通过的header/version/brand/shipnode硬编码给新店。
