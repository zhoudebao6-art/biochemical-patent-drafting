# 生化专利撰写自动化

最新版本：v1.1.4。独立技能名：`biochemical-patent-drafting`。用于从生物、化学、材料与环境类技术项目优化书撰写、独立复查并交付专利Word。

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

v1.1.4重新提取五份人工终稿的完整权项写法，检查来源客体、技术限定、引用继承链与真实Word自然段；保留无底色、无空格、原生上下标、逐表说明和附图说明末项句号等修复。原版本已完成99项定向测试及五稿50项权利要求、72个自然段校验。这是已完成的维护验证，不代表新电脑环境或未来案件已验收。

公开分享版保持程序与29条撰写规则不变，只清理机器配置、模板隐藏账户信息及样本身份。原始项目书、人工终稿、实验数据和图片不在此仓库。当前电脑的原安装配置不受发布影响。

源架构：[patent-drafting-automation v6.37](https://github.com/zhoudebao6-art/patent-drafting-automation/releases/tag/v6.37)。本技能独立维护，不修改原软通技能。
