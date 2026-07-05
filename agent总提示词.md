## 1. 项目目标

实现一个**从零构建的最小可用 Agent 系统（Minimal Agent Runtime）**

## 2. 项目结构说明

当前工程结构如下：

```
cmd/        → 程序入口（命令行交互）
config/     → 配置管理（模型选择 / 拓展配置等）
internal/   → 核心逻辑
tools/      → 工具层（日志 / 错误处理 / 通用工具）
agent.md    → Agent 设计规范（本文件）
README.md   → 项目说明
```

## 3. 核心运行机制e

### /cmd 实现主函数/接口（以及router），维护一个全局任务列表vector，键为对话id
- askQuestion接口 接收goal，httpstreaming 流式返回
- listTask 接口 列出所有对话
- taskDetail 接口 根据对话id列出对话详情（分页，打开对话第一句，每次请求请求一句）
- 全局任务列表有lock功能，如果已存在正在进行思考中的对话，则将goal放入缓存区，待上一个对话结束再执行。

### /internal
/runtime 按照项目结构说明生成demo

/mysql
init.py 全局初始化
processor 封装mysql增删改查等接口

/llm_tools
calculater 封装多项式计算器
research 封装网络搜索api
weather  封装天气查询api
（后面两个config文件夹都有api）

/context
上下文聚合函数
单组对话中两层记忆机制，底层每5轮生成一条sumerry记录。对话数超过10轮触发，查询5*（x-1）-5*x次的来回对话，调用LLM总结，写prompt，写入数据库；第二层是每6轮进行的自动总结更新，维护唯一一个sumerry，每次将最近六轮对话内容和原summery发给llm
，让他将新内容添加进去，替换旧的summery，这个需要简短精悍，同时写prompt，两层记忆分别存入对应对话的附属表（带对话主键）
每次聚合上下文，请求所有对话的两层记忆和最近的10条对话一起发送
对于记忆生成，每次模型返回用户对话后，判断当前论数，符合条件则挂载异步任务，无需返回用户

ask新增追问接口，前端选择之前对话的一句话，自动出现追问图标，点击后拉入输入框，ask发送需要记录此条追问的id以及序列号，runtime处理需要请求context一个函数，根据序列查找此对话，如果序列是最近10条的则直接将追问话聚合进上下文，如果已经是之前的了，被压缩了，则查数据据库请求此条对话原文再加入上下文

/prompt
prompt提示词聚合文件夹，先生成demo

### /config 参数配置文件夹
定义静态变量即可，demo不考虑安全性

### /tools 工具文件夹
/errs 返回用户端报错统一接口，封装msgError（给err打上string提示以及状态码），newError（新建错误），需要对错误进行直接追踪，爆出详细出错语句错误信息，并调用logs在控制台输出error（红色报错）

/logs 日志接口，命令行输出日志，封装输出，error（红），warning（黄），正常日志（无颜色）

/llm 封装底层的llm调用接口，便于使用

/snowflake 生成全局唯一雪花id接口，供所有服务调用

mysql库：对话id使用雪花，以最新更改时间检索
         单组对话中每次来回交互使用+1的id计数（先查最大的id，然后自增1，空对话则建立0序号），方便计算sumerry
         




