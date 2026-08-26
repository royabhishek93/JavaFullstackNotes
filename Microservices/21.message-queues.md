# 🎯 Q22: Message Queues (Kafka, RabbitMQ) Use Cases?

> **Interview Frequency:** 52% | **Difficulty:** ⭐⭐⭐⭐ | **Study Time:** 4 minutes

---

## 🤔 Problem

When should you use Kafka vs RabbitMQ? When do you need message queues at all?

---

## 📌 Use Cases

### 1. **Async Processing**
- User places order → message sent immediately
- Order processing happens async
- Latency: User sees confirmation in 100ms vs 5sec

### 2. **Decoupling Services**
- Service A doesn't need Service B running
- Service A sends message, B processes later
- Service B down = messages queue, no request lost

### 3. **Load Leveling**
- Traffic spike → messages queue
- Consumers process at steady rate
- Prevents server overload

### 4. **Event Sourcing**
- Store all events (UserCreated, OrderPlaced)
- Replay events to rebuild state
- Full audit trail

---

## 📌 Kafka vs RabbitMQ

| Feature | Kafka | RabbitMQ |
|---------|-------|----------|
| **Model** | Log-based, events | Queue-based, messages |
| **Retention** | Days/weeks | Until consumed |
| **Throughput** | Very high (1M+/sec) | Medium (50k/sec) |
| **Use** | Event streaming, audit | Task queues, RPC |
| **Learning** | Harder | Easier |

---

## 💬 Interview Tip (Say This Exactly)

"Use message queues to decouple services. Kafka for event streaming (audit trail, replay), RabbitMQ for task queues (email, background jobs). Benefits: async processing, load leveling, fault tolerance."

---

**Last Updated:** February 22, 2026  
**Previous: [cap-theorem-trade-offs.md](cap-theorem-trade-offs.md) | Next: [../Database_SQL/acid-properties.md](../Database_SQL/acid-properties.md)**
