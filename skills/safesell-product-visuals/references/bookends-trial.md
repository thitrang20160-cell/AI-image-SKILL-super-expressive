# 网站书挡首轮验证

日期：2026-10-08。输入仅为用户给定 Walmart 商品图，没有 3D/CAD 或尺寸资料。

商品参考 URL： https://i5.walmartimages.com/seo/Wooden-Book-Ends-Wood-Decorative-Bookends-Office-Book-Stand-Bookshelf-Ends-Sturdy-Book-Holders-for-Shelves_eb421c16-793f-490c-a266-1eb1328f45e1.26949dc6e721c658bab3fa8ef2fdeaf8.jpeg?odnHeight=573&odnWidth=573&odnBg=FFFFFF

## 执行与文件

本轮使用内置 image_gen，首轮两次独立调用，再对使用图做一次定向编辑，共三次。它们是本地技能的真实试验，未接入 Demo 队列，也没有真实 3D 建模。输出费用/计费 token 未返回，记录为未知。

原图、旧图与新图保存在 `D:/CODEX/saixing-erp-ui-demo/output/imagegen/bookends/`：

- `bookends-reference.jpg`：商品唯一身份依据。
- `bookends-white-v1.png`、`bookends-study-v1.png`：之前的常规构图对照。
- `bookends-hero-v2.png`：新版大主体/木材英雄图，风格参照样本 7。
- `bookends-function-v2-rejected.png`：使用图首轮，右侧底座朝外，未采用。
- `bookends-function-v2a.png`：定向修正后，去掉朝外底座，内侧可见少量接头/线段，仍待审核。
- `brief-v2.json`：两条实际完整生成提示词与输入角色。
- `fix-v2a-prompt.txt`：实际定向修正提示词。

## 观察

| 候选 | 通过的可见点 | 问题与未核实项 | 当前状态 |
| --- | --- | --- | --- |
| hero-v2 | 两件拱形木板、空心矩形黑线底座和连接点可见；近远关系、木纹、板厚、阴影与留白明确。 | 仍接近精致静物，未达到样本的强创意；木纹重绘，真实尺寸/材质种类未核实。 | needs-review |
| function-v2 | 两侧木板、五本书、克制环境与材质层次。 | 右侧脚朝外，违背使用规格；漂亮画面不能替代正确使用关系。 | rejected |
| function-v2a | 保持主体构图，右侧外伸底座已去掉；内侧能看到少量黑色连接/线段。 | 脚被书遮挡，不能完整检查闭合矩形和两连接点；没有证明像素级保留，木纹/织物细节仍变化。 | needs-review |

本轮未给量化总分，文案、系列性及真实结构依据尚不足。不能把“定向删除了错误外伸底座”说成“整个使用结构已经验证”。

## 由本轮支持的规则修正

1. 使用关系比产品轮廓更难：书挡外形正确，底座朝向仍会错。Prompt 中锁定朝向不等于执行保证，需实际查看。
2. 一次局部修正能移除明显错误，但被遮挡的部分仍是未核实，不能让隐藏问题变成通过。
3. 大主体、留白与材质有助于画面控制，但还需要更具体的创意动作和排版，不能宣称已经达到这组样本的全部品质。
4. 仅原图可先进行外观、构图与氛围试作；精确系列与工程剖面仍需固定商品层或结构资料。

## 下一轮范围

用户已要求继续，第二轮选择深色形态/材质海报与浅色整理功能海报，并实际完成独立排版与 PNG 导出。执行记录见 [第二轮实测](bookends-round-02.md)。不要因为有 11 张参考就同时批量重绘所有风格；原图不能提供的背面/底部不成为新图的结构事实。

公开分发说明：历史执行回执不在本仓库。图片仅供设计关系参考；当前SKU逐张重新核验，不将历史摘要当公开审核证书。
