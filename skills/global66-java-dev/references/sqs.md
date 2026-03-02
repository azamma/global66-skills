# SQS Configuration Guidelines — Global66

Stack: Spring Cloud AWS Starter SQS v3+ · `io.awspring.cloud:spring-cloud-aws-starter-sqs`

---

## Architecture: 4 Classes Required

Every microservicio that consumes SQS must implement this exact traceability infrastructure.
These classes are the Gold Standard — copy them as-is, only changing the package name.

### 1. `SqsClientConfig` — Client & bean registration

```java
@Configuration
public class SqsClientConfig {

    @Value("${com.global.{domain}.queue.region}")
    private String region;

    @Value("${com.global.{domain}.queue.max-concurrency}")
    private Integer maxConcurrency;

    @Value("${com.global.{domain}.queue.connection-acquisition-timeout}")
    private Integer connectionAcquisitionTimeout;

    @Bean
    public SqsAsyncClient sqsAsyncClient() {
        return SqsAsyncClient.builder()
            .region(Region.of(region))
            .credentialsProvider(DefaultCredentialsProvider.create())
            .httpClientBuilder(
                NettyNioAsyncHttpClient.builder()
                    .maxConcurrency(maxConcurrency)
                    .connectionAcquisitionTimeout(
                        Duration.ofSeconds(connectionAcquisitionTimeout)))
            .build();
    }

    @Bean
    public SqsProperties.Listener listener() {
        return new SqsProperties.Listener();
    }

    // CRITICAL: Register under the exact bean name Spring Cloud AWS expects
    @Bean(name = SqsBeanNames.SQS_LISTENER_ANNOTATION_BEAN_POST_PROCESSOR_BEAN_NAME)
    TracingSqsListenerAnnotationBeanPostProcessor tracingSqsLABPP() {
        return new TracingSqsListenerAnnotationBeanPostProcessor();
    }
}
```

**Why the bean name matters:** Spring Cloud AWS looks for the post-processor by this exact name
(`SqsBeanNames.SQS_LISTENER_ANNOTATION_BEAN_POST_PROCESSOR_BEAN_NAME`). If you register it
under any other name, the tracing wrapper will not be applied.

### 2. `TracingMessageListenerWrapper` — MDC injection on consume

```java
@Slf4j
public class TracingMessageListenerWrapper<T> implements MessageListener<T> {

    public static final String TRACE_ID = "traceId";
    public static final String SPAN_ID = "spanId";

    private static final String UUID_HYPHEN = "-";
    private static final String EMPTY_STRING = "";
    private static final int SPAN_ID_LENGTH = 16;

    private final MessageListener<T> delegate;

    public TracingMessageListenerWrapper(MessageListener<T> delegate) {
        this.delegate = delegate;
    }

    @Override
    public void onMessage(Message<T> message) {
        MDC.put(TRACE_ID, extractOrGenerateTraceId(message));
        MDC.put(SPAN_ID, generateSpanId());
        try {
            delegate.onMessage(message);
        } finally {
            MDC.remove(TRACE_ID);
            MDC.remove(SPAN_ID);
        }
    }

    private String extractOrGenerateTraceId(Message<T> message) {
        Object traceIdHeader = message.getHeaders().get(TRACE_ID);
        return traceIdHeader != null ? traceIdHeader.toString() : generateFullId();
    }

    private String generateSpanId() {
        return generateFullId().substring(0, SPAN_ID_LENGTH);
    }

    private String generateFullId() {
        return UUID.randomUUID().toString().replace(UUID_HYPHEN, EMPTY_STRING);
    }

    @Override
    public void onMessage(@NotNull Collection<Message<T>> messages) {
        delegate.onMessage(messages);
    }
}
```

**What it does:** Extracts `traceId` from the incoming message header (if present, to continue
a distributed trace) or generates a new one. Puts it in MDC before delegating to the real
listener, removes it in `finally` to avoid leaking context across thread reuse.

### 3. `TracingSqsEndpoint` — Wraps the listener at endpoint creation

```java
public class TracingSqsEndpoint extends SqsEndpoint {

    protected TracingSqsEndpoint(SqsEndpointBuilder builder) {
        super(builder);
    }

    @NotNull
    @Override
    protected <T> MessageListener<T> createMessageListenerInstance(
            @NotNull InvocableHandlerMethod handlerMethod) {
        return new TracingMessageListenerWrapper<>(
            super.createMessageListenerInstance(handlerMethod));
    }

    public static class TracingSqsEndpointBuilder extends SqsEndpointBuilder {

        public TracingSqsEndpointBuilder() {}

        @NotNull
        @Override
        public SqsEndpoint build() {
            return new TracingSqsEndpoint(this);
        }
    }
}
```

### 4. `TracingSqsListenerAnnotationBeanPostProcessor` — Injects tracing into @SqsListener

```java
public class TracingSqsListenerAnnotationBeanPostProcessor
        extends SqsListenerAnnotationBeanPostProcessor {

    @Override
    protected Endpoint createEndpoint(SqsListener sqsListenerAnnotation) {
        return new TracingSqsEndpoint.TracingSqsEndpointBuilder()
            .queueNames(resolveEndpointNames(sqsListenerAnnotation.value()))
            .factoryBeanName(resolveAsString(sqsListenerAnnotation.factory(), "factory"))
            .id(getEndpointId(sqsListenerAnnotation.id()))
            .pollTimeoutSeconds(
                resolveAsInteger(sqsListenerAnnotation.pollTimeoutSeconds(), "pollTimeoutSeconds"))
            .maxMessagesPerPoll(
                resolveAsInteger(sqsListenerAnnotation.maxMessagesPerPoll(), "maxMessagesPerPoll"))
            .maxConcurrentMessages(
                resolveAsInteger(
                    sqsListenerAnnotation.maxConcurrentMessages(), "maxConcurrentMessages"))
            .messageVisibility(
                resolveAsInteger(
                    sqsListenerAnnotation.messageVisibilitySeconds(), "messageVisibility"))
            .build();
    }
}
```

---

## Async Executor — `MdcTaskDecorator`

When using `@Async` or `CompletableFuture` inside a listener, MDC is lost by default.
Global66 uses `MdcTaskDecorator` to copy the MDC context map to the async thread:

```java
public class MdcTaskDecorator implements TaskDecorator {
    @Override
    @NonNull
    public Runnable decorate(@NonNull Runnable runnable) {
        Map<String, String> contextMap = MDC.getCopyOfContextMap();
        return () -> {
            try {
                if (contextMap != null) MDC.setContextMap(contextMap);
                runnable.run();
            } finally {
                MDC.clear();
            }
        };
    }
}
```

Register it in `AsyncConfig`:
```java
@Bean(name = "taskExecutor")
public ThreadPoolTaskExecutor getAsyncExecutor() {
    ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
    int processors = Runtime.getRuntime().availableProcessors();
    executor.setCorePoolSize(processors);
    executor.setMaxPoolSize(processors * POOL_MULTIPLIER);
    executor.setQueueCapacity(QUEUE_CAPACITY);
    executor.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
    executor.setTaskDecorator(new MdcTaskDecorator());  // ← MDC propagation
    executor.initialize();
    return executor;
}
```

---

## SQS Consumer Implementation

```java
// Interface in presentation/consumer/
public interface OrderQueueListener {
    void receiveMessage(String message);
}

// Implementation
@Slf4j
@Component
@RequiredArgsConstructor
public class OrderQueueListenerImpl implements OrderQueueListener {

    private final OrderService orderService;

    @Override
    @SqsListener(value = "${com.global.{domain}.queue.sqs.order.url}")
    public void receiveMessage(String message) {
        log.info("START - [receiveMessage] [SQS]: {}", message);
        try {
            OrderMessageDto dto = ObjectMapperUtils.loadObject(message, OrderMessageDto.class);
            orderService.process(OrderMessageMapper.INSTANCE.toData(dto));
        } catch (Exception e) {
            log.error("Failed to process order message from SQS: {}", message, e);
        }
        log.info("END - [receiveMessage] [SQS]");
    }
}
```

**Rules for consumers:**
- Always START/END logs (see `references/logging.md`)
- Catch `Exception` broadly — an uncaught exception changes message visibility and can cause
  a retry storm. Log the error and let the message go to DLQ after max retries instead.
- Use `ObjectMapperUtils.loadObject()` to deserialize — never `new ObjectMapper()` inline
- Map with `{Domain}MessageMapper.INSTANCE.toData(dto)` before passing to the service

---

## SQS Producer — Sending with traceId in headers

When sending messages via `SqsTemplate`, propagate the `traceId` from MDC into the message
headers so downstream consumers can continue the distributed trace:

```java
@Slf4j
@Component
@RequiredArgsConstructor
public class OrderProducer {

    private final SqsTemplate sqsTemplate;

    @Value("${com.global.{domain}.queue.sqs.order.url}")
    private String queueUrl;

    public void publish(OrderData orderData) {
        String traceId = MDC.get("traceId");
        sqsTemplate.send(to -> to
            .queue(queueUrl)
            .payload(OrderProducerMapper.INSTANCE.toMessage(orderData))
            .header("traceId", traceId != null ? traceId : UUID.randomUUID().toString()));
    }
}
```

**For FIFO queues** — also set `messageGroupId` and `messageDeduplicationId`:

```java
public void publishToFifo(OrderData orderData) {
    String traceId = MDC.get("traceId");
    sqsTemplate.send(to -> to
        .queue(queueUrl)
        .payload(OrderProducerMapper.INSTANCE.toMessage(orderData))
        .header("traceId", traceId != null ? traceId : UUID.randomUUID().toString())
        .header(SqsHeaders.MessageSystemAttributes.SQS_MESSAGE_GROUP_ID_HEADER,
            orderData.getOrderGroupId())
        .header(SqsHeaders.MessageSystemAttributes.SQS_MESSAGE_DEDUPLICATION_ID_HEADER,
            orderData.getTransactionId()));
}
```

**Why `messageDeduplicationId`:** FIFO queues use this to deduplicate messages within a 5-minute
window. Use a stable, unique business identifier (transactionId, orderId) — not a random UUID,
which defeats the purpose.

---

## Infrastructure Naming & Config Conventions

**Queue naming:**
```
{microservice}-{action}-{env}           # Standard: geolocation-events-dev
{microservice}-{action}-{env}.fifo      # FIFO:     transaction-geolocation-dev.fifo
{microservice}-{action}-{env}-dlq       # DLQ:      transaction-geolocation-dev-dlq
{microservice}-{action}-{env}-dlq.fifo  # FIFO DLQ: transaction-geolocation-dev-dlq.fifo
```

**application.yml property convention:**
```yaml
com.global.{domain}:
  queue:
    region: us-east-1
    max-concurrency: 20
    connection-acquisition-timeout: 10
    sqs:
      {queue-purpose}:
        url: https://sqs.us-east-1.amazonaws.com/{account-id}/{queue-name}
```

**Use FIFO when:** Order matters (financial transactions, state machine events, sequential workflows)
**Use Standard when:** Order doesn't matter and you need max throughput (analytics, notifications)

---

## SQS Compliance Review (from git diff or code)

When reviewing SQS implementation, check:

```
SQS COMPLIANCE REPORT
─────────────────────
Status: COMPLIANT | PARTIAL | NON_COMPLIANT

FINDINGS
────────
[1] CRITICAL · TRACEABILITY · SqsClientConfig.java
    Issue: TracingSqsListenerAnnotationBeanPostProcessor not registered
    Fix: Add @Bean(name = SqsBeanNames.SQS_LISTENER_ANNOTATION_BEAN_POST_PROCESSOR_BEAN_NAME)
         TracingSqsListenerAnnotationBeanPostProcessor tracingSqsLABPP() {
             return new TracingSqsListenerAnnotationBeanPostProcessor();
         }

[2] WARNING · INFRASTRUCTURE · OrderQueue config
    Issue: No DLQ configured for the queue
    Fix: Create {queue-name}-dlq and set it as redrive policy with maxReceiveCount: 3

[3] WARNING · IMPLEMENTATION · OrderQueueListenerImpl.java:22
    Issue: Exception not caught — will block message visibility and cause retry storm
    Fix: Wrap processing in try/catch(Exception e) with log.error(..., e)

[4] CRITICAL · TRACEABILITY · OrderProducer.java:34
    Issue: SqsTemplate.send() not propagating traceId in message headers
    Fix: Add .header("traceId", MDC.get("traceId")) to the send builder

[5] WARNING · IMPLEMENTATION · PaymentQueueListenerImpl.java
    Issue: FIFO queue consumed but messageGroupId not considered in processing order
    Fix: Verify business logic handles ordered processing per group correctly

ARCHITECTURAL RECOMMENDATION
────────────────────────────
Consider enabling SQS Long Polling (WaitTimeSeconds > 0) to reduce empty receives and
lower costs. In Spring Cloud AWS SQS v3, set this via SqsProperties or per-listener config.
```

**Compliance checklist:**
- [ ] `io.awspring.cloud:spring-cloud-aws-starter-sqs` in `pom.xml`
- [ ] `SqsClientConfig` with `SqsAsyncClient` + `DefaultCredentialsProvider`
- [ ] `TracingMessageListenerWrapper` present and used
- [ ] `TracingSqsEndpoint` present and used
- [ ] `TracingSqsListenerAnnotationBeanPostProcessor` registered under `SqsBeanNames.SQS_LISTENER_ANNOTATION_BEAN_POST_PROCESSOR_BEAN_NAME`
- [ ] Each `@SqsListener` implementation has START/END logs and catches `Exception`
- [ ] Producers include `traceId` header from MDC when sending
- [ ] FIFO sends include `messageGroupId` and `messageDeduplicationId`
- [ ] DLQ configured in AWS for each queue
- [ ] Queue names follow convention: `{ms}-{action}-{env}[.fifo]`
- [ ] Async executor uses `MdcTaskDecorator` for MDC propagation
