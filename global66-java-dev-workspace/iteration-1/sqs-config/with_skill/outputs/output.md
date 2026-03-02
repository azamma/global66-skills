# SQS Configuration — ms-payments · payment-processing-dev.fifo

Generated following Global66 hexagonal architecture standards and SGSI-POL-005 logging rules.

---

## File Index

| # | File | Package / Path |
|---|------|---------------|
| 1 | `SqsClientConfig.java` | `com.global.payments.config` |
| 2 | `TracingMessageListenerWrapper.java` | `com.global.payments.config` |
| 3 | `TracingSqsEndpoint.java` | `com.global.payments.config` |
| 4 | `TracingSqsListenerAnnotationBeanPostProcessor.java` | `com.global.payments.config` |
| 5 | `PaymentQueueListener.java` (interface) | `com.global.payments.presentation.consumer` |
| 6 | `PaymentQueueListenerImpl.java` | `com.global.payments.presentation.consumer` |
| 7 | `application.yml` (SQS block) | `src/main/resources/` |

---

## File 1 — `SqsClientConfig.java`

**Path:** `src/main/java/com/global/payments/config/SqsClientConfig.java`

```java
package com.global.payments.config;

import io.awspring.cloud.sqs.config.SqsBeanNames;
import io.awspring.cloud.sqs.config.SqsProperties;
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

    // CRITICAL: must be registered under this exact name so Spring Cloud AWS
    // picks it up and applies the tracing wrapper to every @SqsListener.
    @Bean(name = SqsBeanNames.SQS_LISTENER_ANNOTATION_BEAN_POST_PROCESSOR_BEAN_NAME)
    TracingSqsListenerAnnotationBeanPostProcessor tracingSqsLABPP() {
        return new TracingSqsListenerAnnotationBeanPostProcessor();
    }
}
```

---

## File 2 — `TracingMessageListenerWrapper.java`

**Path:** `src/main/java/com/global/payments/config/TracingMessageListenerWrapper.java`

```java
package com.global.payments.config;

import io.awspring.cloud.sqs.listener.MessageListener;
import lombok.extern.slf4j.Slf4j;
import org.jetbrains.annotations.NotNull;
import org.slf4j.MDC;
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

---

## File 3 — `TracingSqsEndpoint.java`

**Path:** `src/main/java/com/global/payments/config/TracingSqsEndpoint.java`

```java
package com.global.payments.config;

import io.awspring.cloud.sqs.annotation.SqsListenerAcknowledgementMode;
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

---

## File 4 — `TracingSqsListenerAnnotationBeanPostProcessor.java`

**Path:** `src/main/java/com/global/payments/config/TracingSqsListenerAnnotationBeanPostProcessor.java`

```java
package com.global.payments.config;

import io.awspring.cloud.sqs.annotation.SqsListener;
import io.awspring.cloud.sqs.config.SqsListenerAnnotationBeanPostProcessor;
import org.springframework.messaging.handler.annotation.support.MessageHandlerMethodFactory;
import org.springframework.messaging.endpoint.AbstractEndpoint;
import io.awspring.cloud.sqs.config.Endpoint;

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

## File 5 — `PaymentQueueListener.java` (interface)

**Path:** `src/main/java/com/global/payments/presentation/consumer/PaymentQueueListener.java`

```java
package com.global.payments.presentation.consumer;

public interface PaymentQueueListener {
    void receiveMessage(String message);
}
```

---

## File 6 — `PaymentQueueListenerImpl.java`

**Path:** `src/main/java/com/global/payments/presentation/consumer/PaymentQueueListenerImpl.java`

```java
package com.global.payments.presentation.consumer;

import com.global.payments.business.ProcessPaymentService;
import com.global.payments.presentation.mapper.PaymentMessageMapper;
import com.global.payments.presentation.dto.request.PaymentMessageDto;
import io.awspring.cloud.sqs.annotation.SqsListener;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import com.global.rest.util.ObjectMapperUtils;

@Slf4j
@Component
@RequiredArgsConstructor
public class PaymentQueueListenerImpl implements PaymentQueueListener {

    private final ProcessPaymentService processPaymentService;

    @Override
    @SqsListener(value = "${com.global.payments.queue.sqs.payment-processing.url}")
    public void receiveMessage(String message) {
        log.info("START - [receiveMessage] [SQS]: {}", message);
        try {
            PaymentMessageDto dto = ObjectMapperUtils.loadObject(message, PaymentMessageDto.class);
            processPaymentService.processPayment(PaymentMessageMapper.INSTANCE.toData(dto));
        } catch (Exception e) {
            log.error("Failed to process payment message from SQS: {}", message, e);
        }
        log.info("END - [receiveMessage] [SQS]");
    }
}
```

---

## File 7 — `application.yml` (SQS configuration block)

**Path:** `src/main/resources/application.yml`

```yaml
com.global.payments:
  queue:
    region: us-east-1
    max-concurrency: 20
    connection-acquisition-timeout: 10
    sqs:
      payment-processing:
        url: https://sqs.us-east-1.amazonaws.com/{account-id}/payment-processing-dev.fifo
```

> Replace `{account-id}` with the actual AWS account ID for the dev environment.

---

## Compliance Checklist

- [x] `io.awspring.cloud:spring-cloud-aws-starter-sqs` required in `pom.xml`
- [x] `SqsClientConfig` with `SqsAsyncClient` + `DefaultCredentialsProvider`
- [x] `TracingMessageListenerWrapper` present — extracts/generates `traceId` + `spanId` into MDC, removes in `finally`
- [x] `TracingSqsEndpoint` present — wraps listener at endpoint creation time
- [x] `TracingSqsListenerAnnotationBeanPostProcessor` registered under `SqsBeanNames.SQS_LISTENER_ANNOTATION_BEAN_POST_PROCESSOR_BEAN_NAME`
- [x] Consumer interface in `presentation/consumer/`
- [x] Consumer implementation: `@Slf4j`, `@Component`, `@RequiredArgsConstructor`
- [x] `@SqsListener` value from `${...}` property — no hardcoded URLs
- [x] START/END logs on `receiveMessage` (SGSI-POL-005 compliant)
- [x] `Exception` caught broadly — prevents retry storms; error logged with exception as last arg
- [x] `ObjectMapperUtils.loadObject()` used for deserialization — no inline `new ObjectMapper()`
- [x] Message mapped via `PaymentMessageMapper.INSTANCE.toData(dto)` before passing to service
- [x] Queue name follows convention: `{ms}-{action}-{env}.fifo` → `payment-processing-dev.fifo`
- [x] YAML properties follow `com.global.{domain}.queue.*` convention
- [ ] DLQ must be configured in AWS: `payment-processing-dev-dlq.fifo` with `maxReceiveCount: 3`

---

## Package Dependency Note

All 4 infrastructure classes (`SqsClientConfig`, `TracingMessageListenerWrapper`, `TracingSqsEndpoint`, `TracingSqsListenerAnnotationBeanPostProcessor`) are placed in `com.global.payments.config` — the `config/` package in the hexagonal structure. They are infrastructure concerns and must never be placed in `business/`, `persistence/`, or `presentation/`.

The consumer (`PaymentQueueListenerImpl`) lives in `presentation/consumer/` because it is the inbound entry point — equivalent in role to a REST controller but driven by SQS events.
