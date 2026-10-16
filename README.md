# SafeSellAI 商品精铺技能与视觉基础设施

可公开下载、按需读取的两个技能：商品视觉制作与速卖通到沃尔玛的选品/Listing/审核/上架编排。包含 **52 张原始参考图片、15 张视觉配方卡、运行检查脚本、可自部署图床、安装器、运行配置模板和跨平台CI**。

原始图片按字节保留，见 [assets-manifest.json](assets-manifest.json)。原图不是新商品的参数依据；参考图里的品牌、数字、认证、结构和文案不能继承。

## 安装

需要 Python 3.12。先克隆，再安装依赖与技能：

```text
git clone https://github.com/thitrang20160-cell/safesellai-product-listing-skills.git
cd safesellai-product-listing-skills
python -m pip install -r requirements.txt
python scripts/doctor.py
python scripts/install_skills.py --target <你的技能目录>
```

Codex 可安装到自己的 `~/.codex/skills`；Windows也可指定任意工作盘目录。安装器不会覆盖已有技能。其他支持SKILL.md的客户端可复制这两个目录，并配置自己的工具。若复制单个技能，选品上架技能需能找到同级 `safesell-product-visuals`。

入口：[商品生图skill](skills/safesell-product-visuals/SKILL.md)、[速卖通精铺沃尔玛skill](skills/aliexpress-walmart-product-listing/SKILL.md)。正文、配方和资产都使用仓库内相对路径；下载后不依赖作者的电脑盘符。

## 图像制作与放行

商品原图负责身份，原始风格锚点负责构图关系。每张保存brief、实际request和review；预检后调用同一份参数，成图按原尺寸与缩略图对照，失败定向返修后重审。

```text
python skills/safesell-product-visuals/scripts/recipe_library.py list
python skills/safesell-product-visuals/scripts/visual_production_gate.py preflight --request <request.json>
python skills/safesell-product-visuals/scripts/visual_production_gate.py review --request <request.json> --review <review.json>
```

详细合同见[稳定视觉生产](skills/safesell-product-visuals/references/stable-visual-production.md)。当前检查器支持内置image_gen的本地参考参数合同。生图工具由调用客户端提供，本仓库不包含商业模型或免费API账户；其他图像服务须由使用者明确选择并按真实参数编写适配器，不能伪报调用。检查器核对文件/记录，不能识别审美、认证用户认可或证明模型调用真实。

公开版不包含生产店铺、客户/地址、密钥、浏览器Cookie或私有审核会话。没有公开执行证据的历史配方标为 `reference-library/reference-only`，可作探索参考，不冒充独立审核通过。3张有用户历史风格反馈的种子仍保留认可范围；认可不代表商品事实或当前批量稳定率。

## 图床基础设施

[图床代码](infrastructure/image-host/server.py) 提供 `POST /api/images`，使用Bearer上传令牌；下载地址 `/uploads/<sha256>.<ext>` 公开可读。相同文件重复上传返回同一URL，文件按内容哈希不可变存储，客户端上传后再GET核对完整字节。

本机试运行可设置环境变量：

```text
UPLOAD_TOKEN=<自己生成的至少32字符随机令牌>
PUBLIC_BASE_URL=http://127.0.0.1:8080
IMAGE_DIRECTORY=<持久化图片目录>
python infrastructure/image-host/server.py
```

上面是变量清单，按自己的Shell语法设置。正式公开服务使用自己的HTTPS域名；HTTP只允许回环测试。可用[Docker Compose](infrastructure/image-host/compose.yaml)，服务默认仅映射到本机127.0.0.1，接自己的HTTPS反向代理。单个服务实例使用一个图片卷。

客户端读取自己的 `SAFESELL_IMAGE_HOST_URL`、`SAFESELL_IMAGE_HOST_TOKEN`：

```text
python scripts/upload_image.py --image <审核通过的最终PNG> --report <新上传报告.json>
```

该图床是可部署的公共基础设施实现，尚未部署到作者或使用者的生产服务器。私有上传令牌不出现在公开图片URL里；上传不自动代表图片审查通过。

## 外部服务与可选检测

[配置示例](config/runtime.example.json)、[环境变量示例](.env.example)和[外部服务适配合同](docs/service-adapters.md)列出必须由使用者提供的服务。SafeSellAI合规服务、沃尔玛卖家API及卖家系统凭据各自配置；本仓库不包含这些商业服务的后台源码或访问权，不自动发布商品。沃尔玛提交前保留目标店铺、SKU、授权、完整schema、库存及逐件回执检查。

容器元数据检查可本地运行。TrustMark是可选检测范围，模型不打包进Git；[模型清单](config/trustmark-models.json)记录官方来源及既有绑定哈希。使用者从官方来源准备模型并运行正负对照；缺模型、访问权或检测结果时保持unknown。云端检测必须显式选择并配置自己的凭据，类别分数不能代替像素水印检测。

```text
python -m pip install -r requirements-trustmark.txt
python scripts/fetch_optional_models.py --output-dir <自己选择的模型目录>
```

可选SDXL实验处理器需要独立准备实际模型/依赖和授权；不自动安装、不自动运行，不承诺通用去除或平台检测不到。原始参考图片发布时没有为规避检测改动像素或元数据。

## 检查与许可

```text
python -B scripts/verify_public_bundle.py --workdir <隔离测试目录>
```

测试只用合成数据及本机回环服务器，不调用生图、店铺、付费审核或真实检测服务。GitHub Actions配置在Ubuntu和Windows运行相同检查。

原创代码与文档采用[MIT许可](LICENSE)；Adobe代码保留其原许可。参考图片和第三方品牌素材的权利范围见[资产说明](ASSET_LICENSE.md)，本仓库不授予其中品牌、宣传参数或第三方图片的商业使用权。

当前[刮冰器原图与返修对照](skills/safesell-product-visuals/assets/cases/ice-scraper-typography/case.json)同时保留退回、遮字和返修工作稿；返修图没有用户认可或商业放行资格。
