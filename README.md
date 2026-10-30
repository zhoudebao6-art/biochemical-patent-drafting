# 生化专利撰写自动化

最新版本：v1.7.2。独立技能名：`biochemical-patent-drafting`。用于从生物、化学、材料与环境类技术项目优化书撰写、独立复查并交付专利Word。

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

表格列宽通用修复：普通文字表按当前页面有效宽度和各列完整内容分配，短样品列让出空间给长说明列，能一行放下尽量一行；保留字号、文字、数值、上下标及边框，放不下自然换行。复杂合并/富对象表保留结构并逐页复核；新增同稿列宽证据，沿用现有生成与验收链。16/8/8总并发32、独立复查、原案小文件夹同名交付保持。

304项相关回归通过；新增短列让宽、完整数字与上下标保留、长内容自然换行、复杂表保留、宽度漂移拦截和当前证据要求等回归。合成排版样本经实际WPS渲染逐页查看；所有正文及原生上下标保留。未用用户项目书构建测试数据，未修改旧冻结批次。

公开分享包保留匿名样本统计和已清洗模板，不含原始技术项目书、人工终稿或个人运行路径。runtime.json保持空配置，新电脑须按references/runtime.md探测依赖、配置环境并完成预检及小样实际渲染。

源架构：[patent-drafting-automation v6.37](https://github.com/zhoudebao6-art/patent-drafting-automation/releases/tag/v6.37)。本技能独立维护，不修改原软通技能。
