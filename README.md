# 生化专利撰写自动化

最新版本：v1.6.1。独立技能名：`biochemical-patent-drafting`。用于从生物、化学、材料与环境类技术项目优化书撰写、独立复查并交付专利Word。

[下载最新分享包](https://github.com/zhoudebao6-art/biochemical-patent-drafting/releases/latest) · [技能入口](skills/biochemical-patent-drafting/SKILL.md)

## 在新电脑安装

在已登录的Codex中复制发送以下内容：

```text
请从https://github.com/zhoudebao6-art/biochemical-patent-drafting安装skills/biochemical-patent-drafting技能到当前电脑的Codex技能目录；按技能references/runtime.md探测本机实际Python、文档渲染工具、WPS或LibreOffice、Poppler和字体，配置runtime.json，执行环境预检和小样实际渲染。保留已有其他技能及配置。本次只安装并核验环境，不启动案件；缺少依赖时准确报告。
```

也可以下载Release中的ZIP，解压后把完整`biochemical-patent-drafting`目录放到`%USERPROFILE%\.codex\skills`；设置了`CODEX_HOME`时放到其`skills`子目录。然后让Codex按上述要求配置运行环境。

技能包包含程序、规则与空白模板，不包含Codex账号、外部Python运行时、Office/WPS、LibreOffice或Poppler。需要已登录且具有指定模型访问权限的Codex/CLI；运行环境以新电脑实际预检和渲染结果为准。未配置的公开包会阻止启动渲染。

## 安装后使用

新建聊天，把下面路径替换为实际文件夹或单份项目书路径：

```text
请使用$biochemical-patent-drafting处理“D:\待撰写生化项目”中的技术项目优化说明书及对应附件，按最新生化规则撰写专利Word；所有两个及以上独权案件的第二及后续每一独权均完整引用前文对应权项，逐字核完整头部、实际编号、任意一项、所述和客体，保留独权身份及全部技术正文；逐案独立复查、修改和页面检查，通过一案立即把验收终稿放回对应案件小文件夹，文件名严格为小文件夹完整名称加.docx，保留原项目书及附件；已有同名文件不覆盖，报告冲突。
```

## 并发配置

初稿16、复查8、修改8，总并发上限32。各池不跨池借位；复查与修改后的独立重验共用8个复查名额。64为在制案件缓冲上限，不是同时运行的CLI数量。主控仍按本批实际可用容量显式填写workers；不足32时使用更低值。新批次生效，旧冻结批次保留原配置。

## 版本与验证范围

连续正文自然换页：生成器清除可明确判断的逗号后句内手动断点，保留文字、数值、单位和原生上下标；有歧义的断点拒绝猜改。检查及交付校验拦截多余断点、正文强制分页和疑似拆段，并要求新版同稿证据。规则v18保持29条，沿用初稿16/复查8/修改8总上限32及原案小文件夹同名交付，旧冻结批次不变。

293项相关回归通过，其中新增9项连续正文测试；使用本地自建排版样稿进行WPS实际渲染并检查修复前后共4页，验证逗号后接排及自然跨页。仅移除句内多余断点，包内其他部件和全部技术文字、原生上标不变。该软件功能验证不替代生产案件的独立语义与页面验收。

公开分享包保留匿名样本统计和已清洗模板，不含原始技术项目书、人工终稿或个人运行路径。runtime.json保持空配置，新电脑须按references/runtime.md探测依赖、配置环境并完成预检及小样实际渲染。

源架构：[patent-drafting-automation v6.37](https://github.com/zhoudebao6-art/patent-drafting-automation/releases/tag/v6.37)。本技能独立维护，不修改原软通技能。
