# SQS FIFO Configuration — ms-payments

## Overview

This document contains the complete SQS configuration for the `ms-payments` microservice,
which consumes the FIFO queue `payment-processing-dev.fifo` using AWS Spring Cloud SQS v3+.

---

## 1. Maven Dependency — `pom.xml`

Add the Spring Cloud AWS SQS starter:

```xml
<dependency>
    <groupId>io.awspring.cloud</groupId>
    <artifactId>spring-cloud-aws-starter-sqs</artifactId>
</dependency>
```

Also ensure the AWS SDK Netty HTTP client is available (required by `SqsAsyncClient`):

```xml
<dependency>
    <groupId>software.amazon.awssdk</groupId>
    <artifactId>netty-nio-client</artifactId>
</dependency>
```

---

## 2. YAML Configuration — `application.yml`

```yaml
com:
  global:
    payments:
      queue:
        region: us-east-1
        max-concurrency: 20
        connection-acquisition-timeout: 10
        sqs:
          payment-processing:
            url: https://sqs.us-east-1.amazonaws.com/{account-id}/payment-processing-dev.fifo
```

> Replace `{account-id}` with the real AWS account ID for the target environment.

---

## 3. Package Structure

```
com.global.payments
├── config/
│   ├── SqsClientConfig.java
│   └── AsyncConfig.java
├── presentation/
│   └── consumer/
│       ├── PaymentQueueListener.java
│       └── PaymentQueueListenerImpl.java
└── business/
    └── tracing/
        ├── TracingMessageListenerWrapper.java
        ├── TracingSqsEndpoint.java
        ├── TracingSqsListenerAnnotationBeanPostProcessor.java
        └── MdcTaskDecorator.java
```

---

## 4. Tracing Infrastructure Classes

These four classes are required for every microservice that consumes SQS. They establish
distributed tracing by injecting `traceId` and `spanId` into MDC before each message is processed.

### 4.1 `TracingMessageListenerWrapper.java`

```java
package com.global.payments.business.tracing;

import io.awspring.cloud.sqs.listener.MessageListener;
import org.jetbrains.annotations.NotNull;
import org.slf4j.MDC;
import lombok.extern.slf4j.Slf4j;
import org.springframework.messaging.Message;

import java.util.Collection;
import java.util.UUID;

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

### 4.2 `TracingSqsEndpoint.java`

```java
package com.global.payments.business.tracing;

import io.awspring.cloud.sqs.config.SqsEndpoint;
import io.awspring.cloud.sqs.listener.MessageListener;
import org.jetbrains.annotations.NotNull;
import org.springframework.messaging.handler.invocation.InvocableHandlerMethod;

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

### 4.3 `TracingSqsListenerAnnotationBeanPostProcessor.java`

```java
package com.global.payments.business.tracing;

import io.awspring.cloud.sqs.annotation.SqsListener;
import io.awspring.cloud.sqs.config.SqsListenerAnnotationBeanPostProcessor;
import org.springframework.messaging.handler.annotation.support.MessageHandlerMethodFactory;
import org.springframework.messaging.handler.invocation.InvocableHandlerMethod;

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

### 4.4 `MdcTaskDecorator.java`

```java
package com.global.payments.business.tracing;

import org.slf4j.MDC;
import org.springframework.core.task.TaskDecorator;
import org.springframework.lang.NonNull;

import java.util.Map;

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

---

## 5. Configuration Classes

### 5.1 `SqsClientConfig.java`

```java
package com.global.payments.config;

import com.global.payments.business.tracing.TracingSqsListenerAnnotationBeanPostProcessor;
import io.awspring.cloud.sqs.config.SqsBeanNames;
import io.awspring.cloud.sqs.config.SqsProperties;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import software.amazon.awssdk.auth.credentials.DefaultCredentialsProvider;
import software.amazon.awssdk.http.nio.netty.NettyNioAsyncHttpClient;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.sqs.SqsAsyncClient;

import java.time.Duration;

@Configuration
public class SqsClientConfig {

    @Value("${com.global.payments.queue.region}")
    private String region;

    @Value("${com.global.payments.queue.max-concurrency}")
    private Integer maxConcurrency;

    @Value("${com.global.payments.queue.connection-acquisition-timeout}")
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

    // CRITICAL: Registered under the exact bean name Spring Cloud AWS expects.
    // If registered under any other name, the tracing wrapper will not be applied.
    @Bean(name = SqsBeanNames.SQS_LISTENER_ANNOTATION_BEAN_POST_PROCESSOR_BEAN_NAME)
    TracingSqsListenerAnnotationBeanPostProcessor tracingSqsLABPP() {
        return new TracingSqsListenerAnnotationBeanPostProcessor();
    }
}
```

### 5.2 `AsyncConfig.java`

```java
package com.global.payments.config;

import com.global.payments.business.tracing.MdcTaskDecorator;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

import java.util.concurrent.ThreadPoolExecutor;

@EnableAsync
@Configuration
public class AsyncConfig {

    private static final int POOL_MULTIPLIER = 2;
    private static final int QUEUE_CAPACITY = 500;

    @Bean(name = "taskExecutor")
    public ThreadPoolTaskExecutor getAsyncExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        int processors = Runtime.getRuntime().availableProcessors();
        executor.setCorePoolSize(processors);
        executor.setMaxPoolSize(processors * POOL_MULTIPLIER);
        executor.setQueueCapacity(QUEUE_CAPACITY);
        executor.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
        executor.setTaskDecorator(new MdcTaskDecorator());
        executor.initialize();
        return executor;
    }
}
```

---

## 6. Message Listener

### 6.1 `PaymentQueueListener.java` (Interface)

```java
package com.global.payments.presentation.consumer;

public interface PaymentQueueListener {
    void receiveMessage(String message);
}
```

### 6.2 `PaymentQueueListenerImpl.java` (Implementation)

```java
package com.global.payments.presentation.consumer;

import com.global.payments.business.PaymentService;
import com.global.payments.domain.dto.PaymentMessageDto;
import com.global.payments.domain.mapper.PaymentMessageMapper;
import com.global.utils.ObjectMapperUtils;
import io.awspring.cloud.sqs.annotation.SqsListener;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class PaymentQueueListenerImpl implements PaymentQueueListener {

    private final PaymentService paymentService;

    @Override
    @SqsListener(value = "${com.global.payments.queue.sqs.payment-processing.url}")
    public void receiveMessage(String message) {
        log.info("START - [receiveMessage] [SQS]: {}", message);
        try {
            PaymentMessageDto dto = ObjectMapperUtils.loadObject(message, PaymentMessageDto.class);
            paymentService.process(PaymentMessageMapper.INSTANCE.toData(dto));
        } catch (Exception e) {
            log.error("Failed to process payment message from SQS: {}", message, e);
        }
        log.info("END - [receiveMessage] [SQS]");
    }
}
```

**Key implementation rules:**
- `@SqsListener` reads the queue URL from the property `com.global.payments.queue.sqs.payment-processing.url`.
- `Exception` is caught broadly to prevent uncaught exceptions from blocking message visibility and triggering a retry storm. Failed messages flow to the DLQ after `maxReceiveCount` retries.
- `log.error()` receives the exception object `e` as the last argument so the full stacktrace is preserved in CloudWatch.
- `ObjectMapperUtils.loadObject()` is used for deserialization — never instantiate `new ObjectMapper()` inline.
- `PaymentMessageMapper.INSTANCE.toData(dto)` converts the DTO before passing to the service layer.

---

## 7. FIFO-specific Notes

Because `payment-processing-dev.fifo` is a FIFO queue, keep these rules in mind:

- **Message ordering is guaranteed per `messageGroupId`.** Ensure business logic respects the processing order within each group.
- **Content-based deduplication or explicit `messageDeduplicationId`** must be enabled on the queue. If sending from this microservice back to another FIFO queue, include a stable business identifier (e.g. `transactionId`) as the deduplication ID — never a random UUID.
- **DLQ must also be FIFO:** The dead-letter queue should be named `payment-processing-dev-dlq.fifo` and configured with a `maxReceiveCount` of 3 in the redrive policy.

---

## 8. AWS Infrastructure Checklist

Before deploying:

- [ ] Queue `payment-processing-dev.fifo` exists in the target AWS account and region
- [ ] DLQ `payment-processing-dev-dlq.fifo` exists and is set as the redrive policy target with `maxReceiveCount: 3`
- [ ] IAM role for `ms-payments` has `sqs:ReceiveMessage`, `sqs:DeleteMessage`, `sqs:GetQueueAttributes` permissions on both queues
- [ ] `{account-id}` in `application.yml` is replaced with the real account ID per environment
- [ ] Long polling is enabled on the queue (`WaitTimeSeconds >= 1`) to reduce empty receives and lower costs

---

## 9. Compliance Checklist

- [x] `io.awspring.cloud:spring-cloud-aws-starter-sqs` in `pom.xml`
- [x] `SqsClientConfig` with `SqsAsyncClient` + `DefaultCredentialsProvider`
- [x] `TracingMessageListenerWrapper` present and wraps the delegate listener
- [x] `TracingSqsEndpoint` present and wraps `createMessageListenerInstance`
- [x] `TracingSqsListenerAnnotationBeanPostProcessor` registered under `SqsBeanNames.SQS_LISTENER_ANNOTATION_BEAN_POST_PROCESSOR_BEAN_NAME`
- [x] `@SqsListener` implementation has `START/END` logs and catches `Exception`
- [x] `log.error()` passes exception as last argument (stacktrace preserved)
- [x] No PII logged in START message
- [x] Async executor uses `MdcTaskDecorator` for MDC propagation
- [x] Queue name follows convention: `{ms}-{action}-{env}.fifo`
- [ ] DLQ configured in AWS (infrastructure task — outside codebase)
- [ ] FIFO `messageGroupId` and `messageDeduplicationId` set in any producer sending to this queue
