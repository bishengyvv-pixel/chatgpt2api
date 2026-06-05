# 通用工程规范

本文件约束当前仓库内的工程建设者、Codex 主代理和子代理。它描述工程事实如何生成、事实如何归位、对象如何出现、对象如何沉淀、代理如何行动。

## 1. 工程生成原则

工程建设是自回归生成过程。每一次行动都以当前事实为输入，产出新的项目状态，并使新状态成为下一次行动的事实基础。

工程设计依据按下列顺序形成：

```text
文件系统事实 -> 源码事实 -> 构成依赖图 -> 运行时依赖图 -> 审计报告 -> 下一次设计
```

权威事实来自文件系统、源码解析、运行时探查、测试、构建、校验和可复算报告。LLM 的职责是读取事实、解释事实、归纳结构、执行行动和辅助审计。

## 2. 事实类型与目录归属

目录用于承载事实类型。事实先被识别，再落入对应目录。

```text
源码事实                         -> src/
二进制或可执行产物               -> bin/
运行数据、运行配置、manifest     -> data/
对象私有材料                     -> assets/
第三方原貌支持                   -> vendor/
测试源码与 fixture               -> test/
文档事实                         -> doc/
宏                               -> script/
临时材料、临时宏、探索和归档     -> .temp/
```

对象内部目录按事实出现。对象可以先只有对象点位；当事实出现时再创建对应目录。

## 3. 对象角色

对象由真实需求和依赖拓扑生成。

```text
app      实例对象；可运行、可部署、可交互、可编排。
domain   领域对象；由 app 的真实依赖图沉淀出的知识对象。
package  组件对象；由 domain 的真实依赖图沉淀出的稳定组件对象。
```

runtime 也采用同一角色语义：

```text
runtime/app      产品外运行能力封装。
runtime/domain   由 runtime/app 的真实治理依赖沉淀出的知识对象。
runtime/package  由 runtime/domain 的稳定汇点沉淀出的组件对象。
```

第三方支持归属于使用它的对象，首先表现为该对象的 `vendor/` 事实。

## 4. 对象出现条件

对象出现由条件触发。

```text
app            出现可运行、可部署、可交互或可编排实例时生成。
domain         app 依赖图中出现可复用知识子图时生成。
package        domain 依赖图中出现稳定低层汇点时生成。
runtime/app    product 需要产品外运行能力时生成。
runtime/domain runtime/app 之间出现共享治理知识时生成。
runtime/package runtime/domain 之间出现稳定低层汇点时生成。
```

对象点位可以先出现，用于标识即将物化的对象边界。对象内部目录由事实驱动创建。

## 5. app 子图沉淀为 domain

domain 的最大判断依据是依赖拓扑结构。

当 app 内部或多个 app 之间出现知识子图，并满足下列条件时，该子图成为 domain 候选：

```text
被多个 app、use、flow 或入口路径依赖。
表达规则、模型、状态转移、策略、权限、流程约束或治理逻辑。
拥有稳定入边，作为知识供给者被消费。
抽出后能降低 app 图复杂度、影响范围、重复边或拓扑变更量。
```

可以用下列拓扑条件表达：

```text
knowledge_subgraph_provider_in_degree_from_app_units >= 2
knowledge_subgraph_provider_out_degree_to_app_units == 0
knowledge_subgraph_has_semantic_role in [model, rule, transition, policy, permission, flow_constraint, governance]
```

其中 `app_units` 指 app、use、flow、入口路径等 app 内部或 app 之间的消费单元。入口路径是消费路径概念，不是 `src/` 角色目录。稳定入边可以由连续多次审计中重复出现的消费边、变更后仍保留的消费边，或影响范围报告中的重复下游来确认。

domain 沉淀后的验证方式：

```text
app 到该知识的依赖边收敛为 app -> domain。
app 内部重复子图减少。
变更影响范围更清晰。
变更速度或变更加速度下降。
```

## 6. domain 汇点沉淀为 package

package 的最大判断依据是 domain induced graph。

当某个 domain 子图满足下列条件时，该能力成为 package 候选：

```text
被两个以上 domain 依赖。
自身不依赖其他 domain。
能力可以脱离具体业务语境表达。
抽出后能降低 domain 图重复边、影响范围或拓扑变更量。
```

可以用下列拓扑条件表达：

```text
domain_provider_in_degree_from_domains >= 2
domain_provider_out_degree_to_domains == 0
```

package 是稳定汇点沉淀，不是工具函数集合。它的价值来自拓扑位置、稳定性和复用方式。

## 7. 目录实体规则

对象内部事实目录如下：

```text
README.md
src/
bin/
data/
assets/
vendor/
test/
doc/
script/
.temp/
```

实体归属：

```text
src/       源码。
bin/       二进制或可执行产物。
data/      运行数据、配置、manifest、运行时图事实。
assets/    对象私有材料。
vendor/    第三方原貌支持。
test/      测试源码与 fixture。
doc/       文档。
script/    宏。
.temp/     临时材料、临时宏、探索和归档。
```

契约是一类事实，不是独立对象部件。契约按实体性质归位：代码契约进入 `src/`，运行 manifest 进入 `data/config/`，文档说明进入 `doc/`。

## 8. src 规则

`src/` 承载源码事实，进入构成依赖图。

源码角色目录按真实代码事实出现。角色目录不是模板清单，而是源码在构成依赖图中的拓扑位置和职责命名。

```text
index/
adapter/
port/
core/
use/
flow/
model/
rule/
transition/
policy/
event/
api/
primitive/
algorithm/
```

源码角色词汇表：

```text
index       对象公开源码入口；在构成依赖图中作为单一消费源点，在反向供给图中作为能力汇点。
adapter     外部能力适配实现；把上游对象、第三方支持、运行环境或外部协议翻译为本对象可使用的形态。
port        源码边界声明；只表达本对象需要外部提供什么或本对象承诺提供什么，不执行协议翻译。
core        无法归入其他角色但对象内部必需的核心协调代码；保持最小。
use         可被触发的用例能力；把入口意图转化为对象内操作。
flow        可被 use 消费的多步骤状态转移流程；编排 rule、transition、policy、adapter 或 event。
model       领域状态、实体、值对象、聚合形态或业务数据结构。
rule        约束、判定、校验和不变量。
transition  单次状态迁移函数、状态机边和状态变更规则。
policy      可替换决策、权限策略、调度策略或治理策略。
event       已发生事实、领域事件、流程事件或对外发布事件。
api         package 对外稳定源码接口。
primitive   低层稳定原语。
algorithm   可独立复用的算法实现。
```

典型对象映射：

```text
app      index/use/flow/adapter/port/core
domain   index/model/rule/transition/policy/event/adapter/port/core
package  index/api/primitive/algorithm/adapter/core
```

不同对象可以只出现必要角色。角色目录出现的依据是源码事实和依赖拓扑，不是预设模板。

对象内部源码拓扑：

```text
对象边界内的 src 文件图应当是有向无环图。
边方向为 consumer -> provider。
对象边界内应形成单一公开入口文件，通常位于 index/。
该入口在构成依赖图中是单一消费源点。
该入口在 provider -> consumer 的反向供给图中是单一能力汇点。
对象边界内可以有多个边界吸收点或内部供给起点。
每个上游依赖应对应一个本对象边界吸收文件，通常位于 adapter/ 或 port/。
在构成依赖图中，index 逐层依赖内部角色目录。
在 provider -> consumer 的反向供给图中，内部能力逐层汇聚到 index。
```

单一公开入口表达对象对外源码边界。边界吸收点表达对象吸收上游对象、第三方支持、运行环境事实或外部协议的方式。内部供给起点表达对象内部不再继续依赖其他本对象源码的基础能力。上游依赖通过边界吸收点进入对象内部，这描述边界吸收与影响传播，不改变 `consumer -> provider` 的构成边方向。

源码角色判定准则：

```text
边界声明进入 port，边界实现或协议翻译进入 adapter。
对象公开入口进入 index，package 的稳定源码接口进入 api。
package 的跨对象依赖入口仍是 index，index 通过 api 暴露 package 稳定接口。
多步骤编排进入 flow，单次状态变化进入 transition。
触发一次业务意图的能力进入 use，被 use 消费的跨步骤过程进入 flow。
稳定数据形态进入 model，约束和不变量进入 rule，可替换决策进入 policy。
无法由上述角色解释但对象内部必需的协调代码进入 core。
低层不可再分能力进入 primitive，可复用计算过程进入 algorithm。
```

角色之间的常见拓扑方向：

```text
index -> use
index -> flow
use -> flow
use -> port
use -> core
flow -> transition
flow -> rule
flow -> policy
flow -> event
flow -> adapter
transition -> model
rule -> model
policy -> model
index -> api
adapter -> port
adapter -> model
core -> model
api -> primitive
api -> algorithm
algorithm -> primitive
```

这些方向用于表达常见稳定结构。真实代码可以形成不同的合法边，但每条边都应能解释为 consumer 需要 provider 的定义、构建、校验、测试或解释，并在对象 `README.md`、manifest 或 `doc/reference/` 中留下可审计依据。

`flow -> event` 表示 flow 依赖事件定义或事件类型，不表示 flow 产出 event 的运行时事实。

对象间源码拓扑：

```text
product/app/*/src      可以依赖 product/domain/*/src。
product/domain/*/src   可以依赖 product/domain/*/src 与 product/package/*/src。
product/package/*/src  可以依赖 product/package/*/src。
runtime/app/*/src      可以依赖 runtime/domain/*/src。
runtime/domain/*/src   可以依赖 runtime/domain/*/src 与 runtime/package/*/src。
runtime/package/*/src  可以依赖 runtime/package/*/src。
```

对象通过上游对象的公开源码入口建立构成依赖。跨对象依赖优先落到被依赖对象的 `src/index/` 或等价公开入口，再由该对象内部拓扑展开。等价公开入口需要由对象 `README.md`、manifest 或 `doc/reference/` 标明。

源码拓扑验证：

```text
对象内无环。
对象内单一公开入口。
跨对象边符合 app -> domain、domain -> domain、domain -> package、package -> package 的层级。
跨对象边进入上游公开入口。
上游变化的影响范围可以从公开入口向下游追踪。
重复子图可以被识别为 domain 或 package 沉淀候选。
```

测试源码进入 `test/`，但测试同样进入构成依赖图。测试结构应与被测 `src/` 形成可追踪映射：测试文件依赖被测源码，测试之间可以按构成关系聚合，单元测试、对象内集成测试和跨对象集成测试都应能从依赖图中解释。

manifest、运行配置、文档、材料、第三方原貌文件和运行数据属于其他事实类型，进入对应目录。

## 9. bin 规则

`bin/` 承载二进制或可执行产物。

来源可以是：

```text
第三方二进制。
从源码构建出的可执行产物。
第三方提供或源码构建出的命令产物。
```

第三方二进制可以从 `vendor/` 复制、链接或暴露到 `bin/`。自研源码构建出的可执行产物进入 `bin/`。

shell 编排属于宏事实，进入 `script/` 或 `.temp/`。当需要可执行命令入口时，应优先由源码生成可执行产物，或由第三方可执行产物进入 `bin/`。

`bin/` 的公开性由 README、manifest 或 reference 文档描述；目录本身表达实体类型。

## 10. script 规则

`script/` 承载宏。

宏用于固化已有动作：

```text
定位项目或对象。
设置环境。
调用已有对象能力。
编排多个命令。
转发参数和退出码。
```

宏不创造能力本体。宏中出现稳定源码逻辑时，将该逻辑识别为源码事实并沉淀到 `src/`。宏中出现运行配置时，将配置事实沉淀到 `data/config/`。宏中出现正式可执行产物时，将产物事实沉淀到 `bin/`。

对象 `script/` 编排本对象能力。项目 `script/` 编排项目内对象能力。一次性机械动作和探索动作进入 `.temp/`。

## 11. data 规则

`data/` 承载运行数据和运行事实。

推荐结构：

```text
data/
  config/
  storage/
  cache/
  state/
  log/
  tmp/
```

语义：

```text
config   manifest、运行配置、运行时图事实。
storage  持久化数据和正式运行产物。
cache    可再生缓存。
state    当前运行状态。
log      日志。
tmp      临时运行文件。
```

`data/config/` 是运行时 manifest 的自然位置。构成所需的源码、类型、算法和编译输入进入 `src/` 或 `test/fixture/`。

## 12. vendor 与 assets 规则

`vendor/` 承载第三方原貌支持。

```text
vendor/<support>/
```

`vendor/<support>/` 内部结构完全自由。对象通过自己的源码、宏、bin 产物或 manifest 使用 vendor 能力。

`assets/` 承载对象私有材料。材料通过读取、校验、解包、生成或迁移转化为正式事实。转化后的事实进入 `src/`、`data/`、`vendor/`、`test/fixture/`、`bin/` 或 `doc/`。

第三方支持的对象化依据是产品能力或运行能力，而不是共享次数本身。

## 13. 构成依赖图

构成依赖边方向为：

```text
consumer -> provider
```

含义：

```text
consumer 的定义、构建、校验、测试或解释需要 provider。
provider 变化时，consumer 需要重新评估。
```

构成图描述源码、测试、构建输入、文档解释和对象定义之间的关系。

对象间构成拓扑：

```text
app -> domain
domain -> domain
domain -> package
package -> package
```

边界关系：

```text
app 通过 domain 获得可复用业务知识。
domain 通过 package 获得稳定低层组件。
product 源码图和 runtime 源码图各自独立。
跨对象交互通过公开入口、运行时图或文档化事实发生。
vendor/assets/data/.temp 保持对象私有边界。
```

## 14. 运行时依赖图

运行时依赖图描述实例运行时交互。

运行时节点可以是：

```text
product/app 实例。
runtime/app 运行能力。
数据库进程。
网络代理进程。
容器守护进程。
命令执行环境。
```

运行时边可以表示：

```text
命令调用。
进程启动。
端口连接。
数据库连接。
文件运行时读写。
环境变量注入。
```

运行时依赖图记录在 `data/config/`、运行时报告或 `doc/reference/` 中。运行时图与构成图分别回答不同问题。

## 15. 文档规则

项目级 `doc/` 描述跨对象规则、整体方法和全局约束。

对象级 `doc/` 使用 Diataxis：

```text
doc/
  tutorial/
  how-to/
  reference/
  explanation/
```

语义：

```text
tutorial     首次完整路径。
how-to       具体操作。
reference    事实，尽量可机械生成或校验。
explanation  理由，引用 reference 事实。
```

reference 记录真实目录、真实入口、真实依赖、真实运行配置和证据路径。explanation 解释事实为何成立。

## 16. README 边界卡

对象 `README.md` 是边界卡，记录：

```text
对象身份。
对象职责。
公开能力。
上游依赖。
下游影响。
边界规则。
文档入口。
```

README 用于快速识别对象。完整教程、完整参考、运行报告和历史材料进入各自事实位置。

## 17. 自包含环境

项目正式运行和开发使用项目内部 runtime。

系统作为不可变基础运行时存在，例如内核、CPU、文件系统和启动项目脚本所需的基础 shell。

产品外运行依赖进入 `runtime/app`，成为项目内封装的运行能力。网络代理、数据库、容器、语言工具链、移动 SDK 等都以 runtime app 表达。

引导阶段可以使用系统基础工具读取事实、归档、下载、解压和物化 runtime。runtime 建立后，正式构建、测试、运行和开发命令通过项目 runtime 执行。

## 18. 临时区

`.temp/` 承载临时事实：

```text
归档。
探索。
临时机械脚本。
临时宏。
临时审计报告。
下载中间产物。
未定稿方案。
```

机械化批量任务可以先在 `.temp/` 写脚本执行。脚本产出的正式成果落入正式对象目录。正式对象通过读取、迁移或转化 `.temp/` 中的材料获得正式事实。

## 19. 变更指标

变更次数是文件或目录写操作次数。

写操作包括：

```text
创建文件。
删除文件。
修改文件。
创建目录。
删除目录。
移动路径。
```

变更量以拓扑变化为核心：

```text
nodes_added
nodes_removed
edges_added
edges_removed
edges_changed
cycle_count_delta
illegal_edge_count_delta
affected_owner_count_delta
runtime_edge_delta
```

变更速度：

```text
change_velocity = topology_change_amount / write_operation_count
```

变更加速度：

```text
change_acceleration = current_change_velocity - previous_change_velocity
```

这些指标用于判断结构稳定性和沉淀效果。沉淀后的拓扑扰动应更小，影响范围应更清晰。

## 20. 代理规则

代理开始重要工作前读取本文件。

行动顺序：

```text
明确目标。
读取相关事实。
识别事实类型。
识别对象边界。
判断构成依赖和运行时依赖。
判断沉淀条件。
制定最小行动。
执行。
机械审计。
必要时独立上下文盲审。
```

子代理默认独立上下文。审计代理报告问题和证据。实现代理说明写入范围。子代理用完及时关闭。

代理应以推理方式收敛对象、依赖和行动，用依赖拓扑、影响范围和变更指标支撑判断。

## 21. 建设顺序

建设顺序：

```text
1. 确认规范。
2. 重建 runtime/app 中真实运行依赖。
3. 通过 runtime 对象事实生成项目环境宏。
4. 构建 product/app/develop 作为开发工具对象。
5. 用 develop 提取依赖图和影响范围。
6. 根据真实依赖图沉淀 product/domain、product/package。
7. 根据 runtime 依赖图沉淀 runtime/domain、runtime/package。
```

每一步以可复算事实、依赖拓扑和审计结果为依据。
