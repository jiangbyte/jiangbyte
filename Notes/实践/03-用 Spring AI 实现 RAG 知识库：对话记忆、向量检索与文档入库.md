---
title: "用 Spring AI 实现 RAG 知识库：对话记忆、向量检索与文档入库"
description: "最近用 Spring AI 做了一套 RAG 知识库对话：后台管理多知识库和文件上传，对话侧支持会话记忆、按知识库过滤检索，以及 SSE 流式输出。骨架还是原来的 DDD-lite Spring Boot 分层。"
permalink: /blog/实践/用 Spring AI 实现 RAG 知识库：对话记忆、向量检索与文档入库/
createTime: 2026-10-01
tags: ["实践"]
type: post
---
最近用 Spring AI 做了一套 RAG 知识库对话：后台管理多知识库和文件上传，对话侧支持会话记忆、按知识库过滤检索，以及 SSE 流式输出。骨架还是原来的 DDD-lite Spring Boot 分层。

技术选型大致是：

| 能力 | 选型 |
|------|------|
| 框架 | Java 21 / Spring Boot 4.1 / Spring AI 2.0 |
| Chat | 阿里云百炼等 **OpenAI 兼容**接口（`spring-ai-starter-model-openai`） |
| Embedding | 本地 **Ollama**（如 `embeddinggemma`，768 维） |
| 向量库 | **Milvus** |
| 对话记忆 | Spring AI **Redis Chat Memory**（RediSearch） |
| 原文存储 | **MinIO**（可与 Milvus 栈共用） |
| 文档解析 | **Tika** + **TokenTextSplitter** |
| 元数据 | **MySQL** + MyBatis-Plus |
| 前端 | Vite + React + Ant Design，SSE 流式对话 |

下面按实现顺序写整条链路：模块怎么分、Spring AI 怎么接、文档如何切片入库、RAG 与记忆如何同时生效，以及默认 RAG 提示词会坑闲聊等问题。

## 1. 目标与整体架构

先明确要做的行为：

1. 管理端：创建多个知识库，上传 txt/md/pdf/office 等文件。
2. 入库：原文进 MinIO，元数据进 MySQL；**Tika** 解析正文，**TokenTextSplitter** 切片后 Embedding 写入 Milvus，并带上 `kbId` / `fileId` 元数据。
3. 对话端：可选某个知识库；携带 `conversationId` 做多轮记忆；SSE 流式回复。
4. 检索：有 `kbId` 时只搜该库；否则全库相似度检索。闲聊时不应被「上下文没有信息」拒答。

端到端可以画成：

```text
管理端上传
  -> MinIO（原文）+ MySQL（kb_base / kb_file）
  -> Tika 解析
  -> TokenTextSplitter
  -> Ollama Embedding
  -> Milvus（向量 + metadata）

对话
  -> message + conversationId + kbId?
  -> MessageChatMemoryAdvisor（Redis）
  -> QuestionAnswerAdvisor（Milvus RAG）
  -> OpenAI 兼容 Chat 模型
  -> 同步 / SSE
```

分层上仍是 DDD-lite 单体：

```text
bootstrap        启动、application.yml、schema.sql
interfaces       Controller / DTO
application      用例、ChatClient 装配、端口（Port）
infrastructure   Spring AI Starter、Milvus/MinIO/MyBatis 适配
domain           约定型抽象（可极薄）
web/             独立前端工程
```

依赖方向保持单向：`interfaces → application → domain`，`infrastructure` 实现 application 里的端口。

## 2. Spring AI 接入：双 Provider 分流

Spring AI 2.x 很方便的一点：classpath 上可以同时放多个模型 Starter，再用属性指定「哪种能力用谁」：

```yaml
spring:
  ai:
    model:
      chat: openai          # 对话走 OpenAI 兼容客户端
      embedding: ollama     # 向量化走本地 Ollama
```

对应依赖（infrastructure 模块）：

- `spring-ai-starter-model-openai`
- `spring-ai-starter-model-ollama`
- `spring-ai-starter-model-chat-memory-repository-redis`
- `spring-ai-starter-vector-store-milvus`
- `spring-ai-vector-store-advisor`（`QuestionAnswerAdvisor`）
- `spring-ai-client-chat`（`ChatClient`）

### 2.1 Chat：OpenAI 兼容（百炼 / Model Studio）

百炼等平台提供 OpenAI Compatible Mode。Spring AI 2.x 底层走 `openai-java` SDK，**base-url 需要带 `/v1`**，例如：

```yaml
spring:
  ai:
    openai:
      api-key: ${DASHSCOPE_API_KEY:}
      base-url: https://dashscope.aliyuncs.com/compatible-mode/v1
      # 若使用业务空间专属域名，换成文档中的 workspace 域名即可
      chat:
        model: qwen-plus   # 或平台上的其它兼容模型名
        temperature: 0.7
```

注意两点：

1. **密钥用环境变量**，不要写进仓库。
2. Spring AI 2.0 里模型名更推荐写在 `spring.ai.openai.chat.model`，而不是旧的 `spring.ai.openai.chat.options.model`（后者会提示 Deprecated）。

若 base-url 少写 `/v1` 或多拼一层路径，常见表现是 `404 Unknown`；密钥缺失则是 `401`。联调时先分清是「路径」还是「鉴权」。

### 2.2 Embedding：本地 Ollama

向量化继续用本机 Ollama，维度与 Milvus collection 对齐（本项目用 **768**）：

```yaml
spring:
  ai:
    ollama:
      base-url: http://127.0.0.1:11434
      init:
        pull-model-strategy: never
      embedding:
        model: embeddinggemma:latest
```

这样 Chat 可以上云、Embedding 留本地，两边也能单独替换。**换 Embedding 模型或维度时，旧向量不可复用**，需要重建 Milvus collection 并重新入库。

### 2.3 Milvus VectorStore

```yaml
spring:
  ai:
    vectorstore:
      milvus:
        client:
          host: 127.0.0.1
          port: 19530
          username: root
          password: milvus
        database-name: default
        collection-name: rag_knowledge
        embedding-dimension: 768
        index-type: IVF_FLAT
        metric-type: COSINE
        index-parameters: '{"nlist":1024}'
        initialize-schema: true
```

有了 `VectorStore` Bean，后面的入库与 RAG Advisor 都直接依赖这个抽象，而不是手写 gRPC。

## 3. 对话记忆：Redis Chat Memory

多轮对话不能只靠前端把历史全塞进 prompt。Spring AI 提供 `MessageChatMemoryAdvisor` + Redis 仓储（基于 RediSearch）：

```yaml
spring:
  ai:
    chat:
      memory:
        repository:
          redis:
            host: 127.0.0.1
            port: 6379
            password: your-redis-password
            key-prefix: "rag:chat:"
            index-name: "rag-chat-memory"
            initialize-schema: true
            time-to-live: 7d
            max-messages-per-conversation: 40
```

要点：

- 这是 **AI 记忆专用连接**，和业务用的 `spring.data.redis` 可以并存。
- 每次调用通过 Advisor 参数绑定会话：

```java
advisors.param(ChatMemory.CONVERSATION_ID, conversationId);
```

- 前端把「会话列表里的 session id」作为 `conversationId` 传给后端即可；后端为空时再生成 UUID。

记忆解决的是「上一句我说我叫 charlie，下一句问我是谁」；RAG 解决的是「制度里市外出差补贴多少」。两者职责不同，后面会放到同一条 Advisor 链里。

## 4. ChatClient 装配：记忆 + RAG 同时挂上

核心配置类大致如下（简化）：

```java
@Bean
public ChatClient chatClient(ChatClient.Builder builder,
                             ObjectProvider<ChatMemory> chatMemoryProvider,
                             ObjectProvider<VectorStore> vectorStoreProvider) {

    ChatMemory chatMemory = chatMemoryProvider.getIfAvailable();
    if (chatMemory != null) {
        builder.defaultAdvisors(
                MessageChatMemoryAdvisor.builder(chatMemory).build());
    }

    VectorStore vectorStore = vectorStoreProvider.getIfAvailable();
    if (vectorStore != null) {
        builder.defaultAdvisors(
                QuestionAnswerAdvisor.builder(vectorStore)
                        .promptTemplate(PromptTemplate.builder()
                                .template(RAG_PROMPT)
                                .build())
                        .searchRequest(SearchRequest.builder()
                                .topK(4)
                                .similarityThreshold(0.55)
                                .build())
                        .build());
    }

    return builder.build();
}
```

一次请求的处理顺序可以理解为：

1. 进入 Advisor 链；
2. **QuestionAnswerAdvisor** 用当前用户问题去 Milvus 做相似度检索（可带 filter），把命中片段填进 `{question_answer_context}`，改写用户侧 prompt；
3. **MessageChatMemoryAdvisor** 按 `conversationId` 注入历史消息；
4. 调用 Chat 模型生成（`.call()` 或 `.stream()`）。

应用服务里每次请求注入参数：

```java
private static void applyAdvisors(ChatClient.AdvisorSpec advisors,
                                  String cid, Long kbId) {
    advisors.param(ChatMemory.CONVERSATION_ID, cid);
    if (kbId != null) {
        // 与写入向量时的 metadata 类型保持一致：字符串
        advisors.param(QuestionAnswerAdvisor.FILTER_EXPRESSION,
                "kbId == '" + kbId + "'");
    }
}
```

接口请求体：

```java
public record ChatRequest(String message, String conversationId, Long kbId) {}
```

- `kbId == null`：全库检索  
- `kbId != null`：只检索该知识库切片  

流式接口用 SSE：`event=message` 推增量，`event=done` + `[DONE]` 结束。前端因要 POST JSON，用 `fetch` + `ReadableStream` 解析，而不是浏览器原生只支持 GET 的 `EventSource`。

## 5. 多知识库与文档处理（入库链路）

### 5.1 元数据表

MySQL 只存「库」和「文件」元数据，不存向量：

```sql
-- 知识库
kb_base(id, name, code, description, status, ...)

-- 文件
kb_file(id, kb_id, file_name, content_type, file_size,
        object_key, status, chunk_count, error_message, ...)
```

`kb_file.status` 建议走状态机：`UPLOADED → INDEXING → INDEXED / FAILED`，失败时把原因写到 `error_message`，方便后台排查。

### 5.2 上传与索引流程

应用层用例（逻辑顺序）：

1. 校验知识库存在、文件后缀允许（txt/md/pdf/office/html 及常见代码文本等）。
2. 读入字节，上传 MinIO，对象键形如 `kb/{kbId}/{uuid}-{filename}`。
3. 写 `kb_file` 行，状态 `UPLOADED`。
4. 改为 `INDEXING`，调用 `KnowledgeIndexPort.indexFile(kbId, fileId, name, bytes)`。
5. 成功则 `INDEXED` 并记录 `chunk_count`；异常则 `FAILED`。

删除文件时：先删向量（按 `fileId`），再删对象存储，再删（或逻辑删）元数据。删知识库前要求库下无文件，并清理该 `kbId` 下残留向量。

### 5.3 Tika 解析 + TokenTextSplitter + Milvus

依赖 `spring-ai-tika-document-reader`，用 `TikaDocumentReader` 把字节解析成 `Document`，再用 Spring AI 的 `TokenTextSplitter` 切片（替代手写固定字符窗）：

```java
public int indexFile(Long kbId, Long fileId, String fileName, byte[] content) {
    deleteByFileId(fileId);
    ByteArrayResource resource = new ByteArrayResource(content) {
        @Override public String getFilename() { return fileName; }
    };
    List<Document> parsed = new TikaDocumentReader(resource).get();
    List<Document> chunks = tokenTextSplitter.apply(parsed);

    List<Document> documents = new ArrayList<>();
    for (int i = 0; i < chunks.size(); i++) {
        Map<String, Object> metadata = new HashMap<>(chunks.get(i).getMetadata());
        metadata.put("kbId", String.valueOf(kbId));
        metadata.put("fileId", String.valueOf(fileId));
        metadata.put("fileName", fileName);
        metadata.put("chunkIndex", i);
        documents.add(new Document(UUID.randomUUID().toString(),
                chunks.get(i).getText(), metadata));
    }
    vectorStore.add(documents);
    return documents.size();
}
```

几个实践细节：

1. **Tika**：PDF、Office、HTML 等走同一解析入口，比「只读 UTF-8 文本」覆盖更广。
2. **TokenTextSplitter**：按 token 切分，和 Spring AI 文档管线一致。
3. **metadata 用字符串存 id**：过滤表达式写成 `kbId == '1'`；类型不一致会导致滤空。
4. **先删后写**：同一文件重复上传不会堆多份向量。
5. **原文与向量分离**：MinIO 存原文，Milvus 服务检索；MySQL 做管理与状态。

删除示例：

```java
Filter.Expression expression = new FilterExpressionBuilder()
        .eq("fileId", String.valueOf(fileId))
        .build();
vectorStore.delete(expression);
```

## 6. RAG 提示词：默认模板会坑闲聊

这是联调时最容易误判成「模型不行」的点。

`QuestionAnswerAdvisor` 默认提示大意是：**只能根据提供的上下文回答；上下文没有就说不知道**。于是：

- 用户说「你好，我是 charlie」；
- 向量检索可能空结果，或硬匹配到毫不相关的制度片段；
- 模型乖乖回复：「抱歉，上下文没有任何相关信息，无法回答」。

这不是 LLM 坏了，是 **Advisor 改写后的 prompt 约束过死**。

处理思路：

1. **自定义 `promptTemplate`**：有相关片段就引用；空/不相关或明显闲聊时，结合对话历史正常回答，禁止那句拒答套话。
2. **适当提高 `similarityThreshold`**（例如 0.45 → 0.55），减少弱相关片段污染普通对话。

自定义模板必须包含占位符 `{query}` 与 `{question_answer_context}`，例如：

```text
用户问题：
{query}

知识库检索片段（可能为空或不相关）：
---------------------
{question_answer_context}
---------------------

规则：
1. 片段相关则优先依据片段作答，不编造。
2. 片段为空/不相关，或问题是问候、自我介绍、闲聊、记名字等，结合历史正常回答，
   不要说「上下文没有相关信息无法回答」。
3. 不要使用「根据上下文」等套话。
```

这样「制度问答」和「多轮闲聊 + 记忆」可以共存在同一条链路里。

## 7. 前端如何配合

前端不是本文重点，但和后端契约强相关：

1. **会话**：本地 `localStorage` 维护会话列表；每个会话带可选 `kbId`。
2. **知识库下拉**：拉启用中的 `kb_base`；清空表示全库检索（传 `kbId: null`）。
3. **流式**：`POST /ai/chat/stream`，解析 SSE 的 `event`/`data`。
4. **管理端**：侧栏布局；知识库 CRUD；文件上传走 `multipart`，展示 `INDEXED/FAILED`。

开发期 Vite 把 `/ai` 代理到 `8080` 即可。

## 8. 联调清单与常见坑

**环境**

- MySQL / Redis / Milvus（含 etcd、MinIO）/ Ollama 就绪  
- Ollama 已拉取 Embedding 模型  
- 已导出 Chat 所需 API Key  

**功能自测**

1. 后台新建知识库 → 上传制度 txt 或 PDF → 状态变为 `INDEXED`，`chunk_count > 0`。  
2. 对话选中该库，问制度相关问题应命中文档。  
3. 新开对话说「我叫 charlie」，再问「我是谁」——依赖 Redis 记忆 + 自定义 RAG 提示，不应再被拒答。  
4. 换库过滤：A 库内容不应在绑定 B 库时被检索到（检查 metadata 与 `FILTER_EXPRESSION`）。

**常见坑**

| 现象                              | 排查                                    |
| ------------------------------- | ------------------------------------- |
| Chat 404                        | base-url 是否含正确的 `/compatible-mode/v1` |
| Chat 401                        | API Key 是否注入进程环境                      |
| 有文件但 RAG 没内容                    | Embedding 是否正常；Milvus 维度是否匹配；阈值是否过高   |
| 过滤后永远空                          | `kbId` 写入类型与 filter 字符串是否一致           |
| 闲聊被拒答                           | 是否仍在用默认 QA 提示词                        |
| 重复上传结果变乱                        | 索引前是否按 `fileId` 删除旧向量                 |
| Deprecated `chat.options.model` | 改为 `spring.ai.openai.chat.model`      |

## 9. The End

这套实现里，Spring AI 比较省事的地方主要是：

- 用 **统一抽象**（`ChatClient` / `EmbeddingModel` / `VectorStore` / `ChatMemory`）拼云端 Chat 与本地 Embedding；
- 用 **Advisor** 把记忆和 RAG 挂到同一条调用链，请求级参数（`CONVERSATION_ID`、`FILTER_EXPRESSION`）动态生效；
- 业务侧自己管 **知识库元数据、对象存储、切片、提示词与过滤**。

后面如果要加深，还可以加语义分块、Rerank、按相关度决定是否启用 RAG、多租户隔离 collection 等。
