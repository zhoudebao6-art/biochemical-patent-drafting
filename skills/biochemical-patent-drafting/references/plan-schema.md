# 生化源绑定计划

bio_prepare.py输入本案冻结DOCX，输出evidence.json/content.txt。body_index是document.xml/body直属元素从0起，包含表格，不是paragraphs索引或页码。候选只是导航，需模型核语义。证据保存来源定位、数学和关系对象及has_content_object标记；完整段落/表格XML直接从已核哈希的原DOCX读取，不再在JSON内重复复制。旧证据中的xml字段继续兼容。

plan顶层schema_version=1、source_sha256、title、claim_map、sections。claim_map每项number、parent(null或单个前项)、object、source_body_indices；从属项必须有dependency_reason，具体说明本项在哪些已有条件基础上进一步限定。编号连续、不固定10项；源段号必须包含同一候选全部续段。

从属项必须提供dependency_basis:[{claim,body_index,quote,current_quote}]。claim是需要承接其技术限定的前项号，body_index属于该前项实际源段，quote是该源段中且在前项技术正文中实际存在的短引文，current_quote是本项被进一步限定的实际短引文。quote不能只取“根据权利要求…”头部或另案内容。与本项相关的多个既有限定可分条记录；先据技术内容确定需要，再选X，不以所选父号倒推凑依据。source_text_edits如改到引文，应选仍与源及实际技术正文一致的短片段。

默认每条basis适用于全部引用支；只有多项择一确有不同支的对应依据时，加via=该支直接父号。每支都需有依据，不能用via掩盖另一支所缺的同一必要条件。生成端逐支核实际inheritance_paths包含全部所需claim；任一支选择额外受限的父项却未声明相应技术需要时拒绝，择一引用同样执行。该校验核的是依据和链的一致性，技术需要是否完整正确仍由独立复查判定，禁止为通过校验虚填依据。

独立项可显式kind=independent、group=自身编号；从属项kind=dependent、group=实际独立祖项编号。简单单父项沿用parent；多项择一从属用parents:[前项编号...]并给head，例如“根据权利要求1至3任一项所述的本案对象”，逐支核基础，不能跨客体分组。head不含编号及“，其特征在于，”，普通单父项不必重复填写。

两个及以上独权的案件，第二及后续每一独权必须显式引用前文对应权项，不限客体类别。保持kind=independent、parent=null、group=自身序号，以reference_claims列实际在前编号，head写完整引用式客体，object只写真正保护的对象。应用示意：object为“一种材料的应用”，head为“一种根据权利要求1-4任意一项所述材料的应用”。实际范围依本案对应客体和每支适用关系核定，不固定1-7、不跨入无关组；不能证明关联时记录缺口，不省略引用或虚构条件。详见[多独权引用规则](claims-patterns.md)。本组从权继续按真实限定基础选parent，不能把独权reference_claims当成从权parents。第一独权及单独权案件不添加前文引用。kind、group与实际生成文本必须一致；计划不能掩盖正文漏引。

bio_prepare.claim_candidates仅为导航，包含segments、source_body_indices、explanation_body_indices及group_candidate；不是自动确认的主从关系。完整候选只对应一项，解释不凑数。生成器逐项比较源候选的全部技术限定；如确需有据话术调整，source_text_edits:[{old,new,reason}]逐项明确唯一旧文、替换后文和理由，计划块同步实际编辑。此记录只使编辑可追溯，不证明语义通过，不得删改参数/范围/条件来绕过检查。复杂合并拆分需在本attempt先解决源边界并交独立复查，不能静默漏掉候选。

候选source_object取自本组总体方案的真实客体；object与其一致，仅规范冠词“一种”及源内引导回指“所述”，不改变技术名称。按候选原顺序安排claim_map及Word权项，不按父号重排。数字相同但单位、化学字母标记变化的source_text_edits也拒绝；未被机械识别的中文语义改动仍逐条独立复查。

sections键为abstract、abstract_figure、claims、description、figures，值为按顺序的块数组。块可用source_body_index导入原段/表；普通富文本片段加slice:[start,end]表示可见文字左闭右开区间；跨run保留属性。含数学、图像、OLE、域、制表/换行的段不允许切片，整对象导入或本attempt做最小原生编辑。

replace:[[原文,新文]]局部改话术，prefix在切出的技术限定前加权项头。权项首段前缀如1、XXX，其特征在于，，续段不重复编号。新段用text或runs，每run有text及可选script=subscript/superscript；新技术文字必须source_body_indices绑定实际支持。标题/栏目/图号是结构性文字，可无技术来源。

claims可导入完整源候选并加固定头部，不必手填额外分段元数据。生成器将独立方法项的引导、S步骤或无编号顶层操作整理为真实自然段；有S标签时保留步内分号，从属项内部冒号/分号保持单段。末尾限定不丢失，也不另立权项；其中衔接需由本案计划有据提供。只变段落，不改技术文字，claim_layout_normalizations记录变化。含复杂对象且需要切开的段落明确拒绝自动切分，由本attempt原生编辑后复查，不展平公式。

role为body/heading/title/image/caption/table/table_caption/figure_analysis/results_analysis_heading/technical_summary/benefit_intro/auxiliary_label。image导入源图整段，等比例缩小不裁切；caption只图N。主图从源标记映射，不按media文件序号或图1猜。description包含正式名称、五栏目、相应来源段、全部实施表及结果分析开头的全部图解释，原综合分析保留在其后。auxiliary_label为普通字重的源内标签，仅跟随后文，不变成加粗小标题。

实施例编号与源中的完整首句放在同一个body块中，直接引用完整源段，不用slice截成只有编号，也不把来源首句省掉后直接写S1。源编号与引导原为两个普通段时，plan可用引导段加源绑定prefix组合为同段；原数学/复杂对象不展平。生成端核源句，遗漏或截短时在本attempt修复计划。

bio_author.py --evidence EVIDENCE --plan PLAN --out OUTPUT.docx --check生成草稿及.trace.json，记录源位置、切片、替换、新段、标题及claim_map，并依次生成.preflight.json与同目录inspection-cache。明确机械失败即停止后续取证，保留稿件及失败结果。输出不覆盖，成功仍为draft_not_accepted。未支持的复杂对象不能省略，做本attempt局部补丁并记录，改稿后重新运行两项检查。任何工具记录都不等于独立通过。

成稿按[无空格规范](no-spaces.md)输出；plan的title在冻结前核定无空格表达。技术段的有义英文/独立数字/运算分隔须先依源改写为无空格准确表达；raw来源、JSON语法和路径不清理。生成器仅去显示副本中的无义空格，不能借压缩改变含义。

表格可显式table_header_rows=N定义本表连续前N行列头，多层表头不得猜；默认沿用源连续重复表头或1行，必须语义复核首行确是列头。每张独立表前都要有table_caption，text或源段为表N加有据说明，连续编号，常规字重居中、无缩进；只有表N而无说明不算完整表题。figure_analysis标记全部图解释段，生成器也按evidence.figures解释定位归类并移到结果分析标题后；标题同段带正文时仅可切普通富文本，不支持切富对象则显式原生编辑。technical_summary可加summary_subject=present/missing核定主语，生成器去段首技术总结标签并为明显缺主语句补本发明；详见[tables-analysis-summary](tables-analysis-summary.md)。原计划SHA、来源位置、顺序调整和补主语行为都记录.trace.json。

说明书heading只用于五主栏目，正式名称用title；制备工艺及其他源内标签用body，不能因短句或冒号自动加粗。生成器按源技术效果段统一唯一benefit_intro并去额外标题。源已有性能测试结果总标题时，生成器把它变成测试结果表号引用，并为每张表补“表N各实施例与对比例的性能测试结果N”；源已有各表具体说明则保留，不覆盖其指标含义。其他无标题表须在plan提供源绑定表题，不猜新指标；表号变更必须显式同步正文引用，工具遇未核对的改号拒绝。

新增普通文本优先使用runs分段及script=subscript/superscript，如Na、下标2、CO、下标3；10后整个-5为上标。不能直接输入特殊上下标字符伪装；源导入中的明确特殊上下标由生成器转换并记录。涉及复杂公式/嵌套或冲突格式时需源绑定原生编辑，不展平OMML。

附图说明中的图名段：前面各条按“图N为本发明的……；”编写，最后一条按“图N为本发明的……。”编写，单条列表用句号。生成器兜底只调整本列表句末并在figure_description_endings记录，不展平富文本。
