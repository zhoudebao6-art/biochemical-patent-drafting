# 生化专利撰写自动化

最新版本：v1.2.0。独立技能名：`biochemical-patent-drafting`。用于从生物、化学、材料与环境类技术项目优化书撰写、独立复查并交付专利Word。

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
请使用$biochemical-patent-drafting处理“D:\待撰写生化项目”中的技术项目优化说明书及对应附件，按最新生化规则撰写专利Word，逐案独立复查、修改和页面检查，通过一案立即交付到桌面同一批次文件夹。
```

## 版本与验证范围

本次五案维护验证的源证据总量由2,378,076降至479,388字节；生化预检的文件读取由9次降至2次；生成与两项检查由三条命令合为`bio_author.py --check`一条；新运行快照由76个文件降至75个。五案50条权项、72个真实自然段及来源Word XML/媒体等价检查通过。主回归共245项（100+101+44）通过；独立验证重复执行的用例不另叠加到此数量。以上是维护检查结果，不代表未来案件的语义/页面验收或产能实测。

公开分享包保留匿名样本结构统计及已清洗的五分区模板；不含原始题名、原件哈希、技术项目书、人工终稿、实验数据或图片。runtime.json保持空配置，必须在新电脑探测并验证Python、文档渲染器、WPS或LibreOffice、Poppler和字体后填写；安装技能不等于环境就绪。未配置时预检会拒绝运行。

v1.2.0复用已有生化生成器、检查器和缓存，不新增调度层；保留三池、29条规则、源绑定权项校验、冻结身份、独立复查及逐案交付。补齐损坏DOCX XML的受控拒绝，旧命令、旧证据和旧冻结批次保持兼容。

源架构：[patent-drafting-automation v6.37](https://github.com/zhoudebao6-art/patent-drafting-automation/releases/tag/v6.37)。本技能独立维护，不修改原软通技能。
