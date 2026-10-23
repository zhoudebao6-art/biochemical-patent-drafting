# 生化规则维护

只维护biochemical-patent-drafting的references/rules.json及其规范，不能修改软通技能和运行中的冻结快照。新增/改变规则用rules_tool.py apply的版本化patch；纯工具修复记录实现变更及定向验证，不重复加规则。当前用户要求优先，单案例外不自动变长期通用规则；技术事实始终属于本案。

worker-standard-coverage.json绑定mapping-writing、chemistry-data、format、plan-schema及worker-standard。内容改变先核原文约束/例外、执行要点与按需引用完整覆盖，再更新SHA；不能只刷哈希冒充独立语义复核。阶段包拼接完整、各规则路由不重叠，所有活动ID保留。

维护验证用scripts/test_groups.py的biochemical、workflow、pages组，按改动选测、同用例去重。原上游软通写作测试仅保留为兼容开发资料，不作为生化规范验收；本版活动测试入口不加载它们。脚本成功只证明机械行为，还须用真实源文件做前向生成和实际页面检查，不把测试夹具当生产验收或产能。

更新后核规则结构、技能入口、引用文件、Python语法及运行链；新批次冻结新版本，旧批次继续原工具。当前目录的architecture-provenance.json记录上游v6.37提交、未改架构文件及生化适配点，版本更新应同步。
