# CLI执行与恢复

总控维护清单，每个CLI仅负责一个case的一个attempt。按[批次流程](batch-workflow.md)完成scan、selection和init后运行：

```text
python scripts/cli_pool.py run --manifest 批次manifest.json --controller 本批控制器标识 --workers 32
python scripts/cli_pool.py status --manifest 批次manifest.json
```

run会消耗当前CLI登录账户额度。上例32须替换成本批实际可用总容量，包含已占名额，不包含总控和无关任务。默认初稿16、复查8、修改8，总上限32，在制缓冲64；不跨池超限，新三池省略workers即拒绝。64GB内存仅为建议上限依据，不证明实际容量。池满、同案单attempt及即时流转按[三池执行](three-stage-pools.md)。

## 启动与身份

run/status及队列命令自动转入本批冻结脚本。可用--executable指定原生codex.exe；否则检测PATH及本机LOCALAPPDATA/OpenAI/Codex/bin下的原生程序，不经cmd包装或shell拼接。启动一次非模型预检检查Windows、CLI参数和登录状态；文档环境按[runtime](runtime.md)另核。普通批次不另跑付费容量探针。

每次codex exec显式选draft=gpt-6.1-sol/high、review/revise=gpt-6.1-sol/xhigh，stdin传冻结prompt，--json记录事件，-o保存最终JSON。改稿后review用新进程及新会话，禁止复用修改者会话自签通过。不静默降级模型。CLI执行遵守workspace-write及宿主配置，不注入绕过安全约束的参数。

每attempt保留cli-job.json、cli-launch-intent.json、prompt.txt、dispatch.json、events.jsonl、worker-final.json、实际session.jsonl、cli-exit.json和cli-completion.json。PID同时绑定创建时间及exe；supervisor退出后封存五份执行证据SHA。收稿核事件、真实会话的模型/强度/cwd/sandbox、原prompt、最终回复及退出码。它们是本地执行证据，不是第三方签名或专利验收。

只允许唯一turn.started之后、最终agent_message及唯一turn.completed之前，严格匹配`Reconnecting... n/m (stream disconnected before completion: ...)`的中间重连；原始日志不改。未知error、turn.failed、非零退出、身份/封存不一致仍拒绝。

## 工作边界

stage_pool_runner使用三个独立本地准备/收稿通道和一个单写交付通道；慢I/O在清单锁外，同案短事务合并，准备中占槽。worker仅写本attempt，不启动新CLI、批次或子worker，不改来源、其他案或冻结工具。阶段包只读一次，规则/数学/来源导航和证据复用见[检查与收尾](fast-execution.md)。

review先审内容，问题交revise，改后由新review独立重验；通过即交付桌面同一批次目录。CLI成功不表示终稿通过：parallel_batch.record仍核来源、当前DOCX、六项、渲染及全部页证据。verified_scope_v1只能继承真实未受影响的通过范围和已审同稿页面，缓存及自报pass均不能替代验收。

## 中断与失败

|情况|处理|
|---|---|
|总控重启|先status，再以同manifest运行run；supervisor可继续保存退出证据，完成结果只收取，不重复模型任务|
|启动意图或未知进程状态|保留槽位、锁和证据；确认旧进程停止前不取消、不重派；整池唯一总控及每attempt唯一supervisor防重复启动|
|来源损坏或本案准备失败|隔离该案，其他合格案继续；来源哈希变化不得重算放行|
|CLI非零退出、身份/哈希/会话不一致或未知异常|停新付费派发，继续收已有worker；只有确认退出才释放槽，坏JSON或查身份失败不能推定退出|
|身份已核、仅业务回执字段错误|仅明确的CaseReceiptError可保存cli-rejection.json并隔离本案，其他案继续；不自动收费重跑。须先核已提供路径、哈希和跨案边界，缺字段不能掩盖完整性错误|
|有效needs_input|单列来源缺口，继续其他案；有阻断或待处理时run返回非零，不将pending视为完成|
|权限、额度或内部工具故障|按[恢复规范](tool-fault-recovery.md)诊断原attempt，保全有效稿及日志，修复验证后接续；不因耗时久重复派发或终止无关进程|

## 受控历史恢复

仅旧程序误拒收成功重连的draft，确认整池已退出后用`python scripts/recover_cli_batch.py --manifest 旧manifest --work-root 工作根目录 --controller 新控制器标识`。工具重验原执行/模型/来源及冻结身份，以恢复初稿进入新独立review；不恢复未知失败、修改稿或旧通过结论。

若旧恢复布局导致派发前的`Foreign or changed current artifact`，--new-generation仅适用于无活动及历史attempt、无启动意图/派发记录、且原因完全匹配的准备失败。保留旧manifest和恢复指针后重建，并验证真实reserve --prepare及交接。恢复候选置于stages/recovered-draft，不假造模型attempt。

## 兼容与观察

旧批次无dispatch_transports时仅保留原collaboration通道；CLI不可用时只能在创建启动意图前使用真实可用的collaboration容量。旧批次省略workers仍沿历史默认4；无pool_execution标志时保留原收取、交付后补位及drain，不改旧快照。

reserve按状态和公平次序校验到首个合格候选，显式plan仍列全量阻断；bind/record/deliver的完整性边界保留。同次收取、历史审计和缓存的精确边界统一见[检查与收尾](fast-execution.md#复检后收尾-v58)。本地状态观察不发模型请求；运行中工具按等待工具等待30–60秒，不高频打印全文。曾完成的4路文件读写探针只证明当时执行通道，不证明32路或专利整批产能，普通办案不重跑。
