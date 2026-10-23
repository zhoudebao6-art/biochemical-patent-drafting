# 生化Word生成与检查

pipeline.toolkit唯一指向scripts/bio_author.py。旧软通authoring_toolkit.py仅保留在维护包供上游对照，不进入新批次快照。

1. 用`bio_prepare.py SOURCE --out 新证据目录`提取本案，按[plan-schema](plan-schema.md)编写源绑定计划。二进制DOC用实际可用的`--soffice`转换，原件只读。
2. 用`bio_author.py --evidence evidence.json --plan plan.json --out 本attempt/draft.docx`从脱敏五分区模板和原对象生成草稿及trace。bio_author整理真实权项段落并保留技术文字，bio_claims在保存前比对源顺序、源客体、实际分段、完整源限定及客体引用关系；拒绝错误计划，不自动改写技术内容。规划时先解决语义、完整引导和有义空格，工具不补造事实。
3. 用`inspect_docx.py DRAFT --kind draft --out prepared.draft_inspection_cache --extract-media --reuse`生成供handoff/回执复用的当前稿报告；用`bio_check.py DRAFT --evidence evidence.json --plan plan.json --out preflight.json`补核五分区、计划权项和源表数量。两工具职责不同，均不表示语义通过。
4. 按[runtime](runtime.md)用`render_docx_checked.py --reuse --compact`渲染，查看render.json及全部当前页；字节变化须重新渲染，之后按[worker-receipt](worker-receipt.md)交独立复查。

生成器保留源上下标、OMML、表格及图片关系。段落、表格、表题、图说明末尾由bio_layout/bio_presentation处理；bio_package将特殊上下标字形转换、无底色、无空格清理合为一次包事务，共享XML解析，全项成功才原子写回。任一转换有歧义就拒绝，不留下部分修改；trace记录各项变化及当前稿哈希。

规则以[rules](rules.json)、[format](format.md)、[chemistry-data](chemistry-data.md)、[no-spaces](no-spaces.md)和[tables-analysis-summary](tables-analysis-summary.md)为准，此处不再重复。自动化仅处理确定性变换，不推测化学数字、实验结果或保护范围。手动补丁只编辑自己的稿件，完成后重新运行同一检查和渲染链。
