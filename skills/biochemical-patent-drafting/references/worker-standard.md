# 生化阶段执行规范

本清单前部已逐条包含本阶段规则、检查和例外，按prepared.pipeline.stage_read_parts读一次。此处不重复规则；遇具体对象按下表读细则，已读且未变的内容不重复加载。

|触发情形|必须读取的细则|
|---|---|
|首次撰写或修改章节映射、实施例引导|[mapping-writing](mapping-writing.md)，其中“实施例首段与来源完整性”约束完整原句、分段及后文核对|
|撰写、修改或复查权利要求|[claims-patterns](claims-patterns.md)，逐项核源顺序、源客体、完整固定头部和限定、真实分段、条件组合与引用关系；所有多独权案件的第二及后续独权均须前文引用，逐字核“一种根据权利要求”完整不漏字，逐项核reference_head_check，核实际编号、任意一项、所述和完整客体；核实际范围和各支对应关系，任意一项完整解析，各组从权保留本组继承链|
|化学式、上下标、数学、谱图、配方或实验数据|[chemistry-data](chemistry-data.md)；不以零OMML认定无公式|
|首次生成或修复版式|[format](format.md)；表格、图分析位置及技术总结见[tables-analysis-summary](tables-analysis-summary.md)|
|源文字含有义空格、英文词间隔或独立数值|[no-spaces](no-spaces.md)，先有据改写，再清理显示副本|
|draft/revise生成或修改Word|[authoring-toolkit](authoring-toolkit.md)和[plan-schema](plan-schema.md)；仅给不支持的对象补原生编辑|

六项独立审查保持：source_support核本案技术事实、实验属性、表格单元格、完整引导及全部后续内容；antecedents逐项核新增限定、X、完整引用链及继承条件，另按整个优化方案此前文字核完整名词首次引入与名称一致；claims_alignment核保护类别、客体、继承范围/计量基准相容及各章节对应；formulas核数学/化学结构、单位及已有计算；figures核主图、全部图像及条件/解释；rendered_pages核全部当前页。机械证据不代替任何语义或视觉结论。

review只读集中findings，revise修改后由新会话review重验；修改者不能自签pass。按prepared.review_reuse核差异及依赖，仅继承有证据、未受影响的已通过范围和已实查的同图页面。已知待改先修改再渲染，同稿有效检查/渲染缓存复用；检查器变化也会使对应检查缓存失效。

最后按[worker-receipt](worker-receipt.md)用prepared.receipt_tool提交一次真实回执，未做项not_run。当前稿六项与全部最终页完整覆盖才pass。只写当前attempt，不启动其他CLI/批次或改来源、冻结工具、共享Office及其他案件。
