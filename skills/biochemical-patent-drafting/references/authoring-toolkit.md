# 生化Word生成与检查

pipeline.toolkit唯一指向scripts/bio_author.py。旧软通authoring_toolkit.py及其专用math_fragments.py仅保留在维护包供上游对照，不进入新批次快照。

1. 用`bio_prepare.py SOURCE --out 新证据目录`提取本案，按[plan-schema](plan-schema.md)编写源绑定计划。二进制DOC用实际可用的`--soffice`转换，原件只读。
2. 完成计划后，用`bio_author.py --evidence evidence.json --plan plan.json --out 本attempt/draft.docx --check`一次生成草稿、trace和机械检查结果。先写draft.preflight.json；有明确错误即停止，保留候选和失败证据。无机械错误时在稿件所在目录的inspection-cache生成标准检查缓存，供handoff复用。成功仍为draft_not_accepted，不必再重复运行同稿两项检查。
3. 按[runtime](runtime.md)和当前阶段安排渲染，查看render.json及全部当前页；字节变化须重新渲染，之后按[worker-receipt](worker-receipt.md)交独立复查。

生成器按源顺序、完整客体、真实分段、全部限定及引用关系校验权项，不自动选X或改技术内容。源提取与模型制定计划保留独立边界。evidence.json以body_index/locator定位原文、保留数学及关系对象，用has_content_object判断空段，不再重复整段XML；原DOCX仍是对象权威，旧版含xml的证据继续兼容。

手工编辑已有稿件后，用`bio_check.py DRAFT --evidence evidence.json --plan plan.json --out preflight.json --inspection-cache prepared.draft_inspection_cache`一次刷新源绑定检查和集中取证，与生成时的`--check`共用同一检查顺序。参数中的缓存路径替换为prepared给出的实际路径。预检失败先保存报告并停止，不创建成功检查缓存；旧的两条独立命令仍兼容。两项检查均不表示独立审查通过。每次源绑定校验由bio_claims.evaluate只解析一次当前权项结构，并在本次调用中供客体、完整原文及从属链检查共用；不跨稿缓存，不减少任何检查。

生成器保留源上下标、OMML、表格及图片关系。段落、表格、表题、图说明末尾由bio_layout/bio_presentation处理；bio_package将特殊上下标字形转换、无底色、无空格清理合为一次包事务，共享XML解析，全项成功才原子写回。任一转换有歧义就拒绝，不留下部分修改；trace记录各项变化及当前稿哈希。

规则以[rules](rules.json)、[format](format.md)、[chemistry-data](chemistry-data.md)、[no-spaces](no-spaces.md)和[tables-analysis-summary](tables-analysis-summary.md)为准，此处不再重复。自动化仅处理确定性变换，不推测化学数字、实验结果或保护范围。手动补丁只编辑自己的稿件，完成后重新运行同一检查和渲染链。

## 连续正文与自然换页

同一段正文（含结果分析）须连续排版，到页底由Word/WPS自然换页。不得在逗号后插入手动换行、分页符或空段，使尚有空间的行提前结束；普通正文显式关闭与下段同页、段中不分页、段前分页及孤行控制。保留五分区边界、独立步骤、标题与图表的原有结构，不为填满页面合并不同段落，也不把整段或整串数值设为不可换页。

生成器只在说明书普通正文中，清除可确定为同一句逗号后的多余手动断点，逐项写入trace；原文、标点、数字、单位、原生上下标和内联公式保留。不明确的换行、列分隔、浮动对象绕排或跨段衔接拒绝猜改，须按本案来源编写完整连续段或真实步骤段。不得只删除后一段来消除断点。表格、页眉页脚和附图不作正文自动拼接；lastRenderedPageBreak是排版缓存，不是手动分页。

当前SHA的presentation证据必须包含prose_flow_contract_version=1，检查手动断点、继承分页约束和逗号后的疑似拆段；缺少新证据或有问题不得通过。复查全部实际页面，特别检查页底/次页首是否自然衔接；不要求复制样例的具体页码或行数。

## 终稿黑点与编辑标记

终稿不得新增装饰性的黑点、黑方块或自动项目符号。发现黑点时先区分正文字符、编号产生的项目符号和编辑器非打印标记；只按本案来源修正确定多余的装饰符号，不全局删除点号、科学图形标记、化学自由基点、乘号或公式符号。

段落左侧小黑方块通常是Word/WPS在显示编辑标记时提示“与下段同页”等分页属性，不属于正文。技能打开本案终稿作编辑器预览或截取交付画面时，应在已确认的该文档窗口关闭“显示/隐藏编辑标记(¶)”；若界面设为始终显示段落标记，还须关闭该显示项并观察结果。使用可用的文档接口时明确设ShowAll=False和ShowParagraphs=False并回读；界面操作先核当前状态，不盲按会反向开启的快捷键，不修改注册表或其他文档的显示设置。没有可控编辑器时使用现有PDF/页面图进行页面验收，不能宣称已经修改编辑器显示。

不得为隐藏这类方块全局清除keepNext、keepLines或pageBreakBefore；普通正文沿用既有自然分页规则，标题、表题、表头与首行的必要连接及五分区边界保留。当前稿全部渲染页面必须复查无多余装饰黑点；真实打印内容中的黑点须修正副本后重跑检查和渲染，不能只隐藏显示标记就放行。

编辑标记显示受打开文件的应用控制，DOCX不能保证另一台电脑在主动开启编辑标记后仍不显示这些提示。其不进入正常打印或PDF；交付说明中遇到同类显示问题，提示关闭¶，不要把显示开关说成正文已被删除。规则同时用于初稿、复查和修改；不新增转换器或改变既有验收链。
