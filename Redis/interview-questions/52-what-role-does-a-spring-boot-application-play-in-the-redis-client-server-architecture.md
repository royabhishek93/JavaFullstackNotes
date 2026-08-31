# What role does a Spring Boot application play in the Redis client-server architecture?

**Type:** Scenario-Based
**Topic:** Redis Architecture — Client-Server Model
**Level:** Mid Interview (3–8+ YOE)

## Direct Answer
The Spring Boot application acts as a **client**, exactly like `redis-cli` or any GUI tool. It sends commands (via a library such as Lettuce or Jedis, wrapped by `RedisTemplate`) to the Redis server, which does all the actual data storage and command processing. The application never stores data itself — it only requests and receives it over the network.

## Easy Explanation
Think of Redis as a librarian who actually holds and organizes every book (all the data), and your Spring Boot app as a visitor who asks the librarian for books or hands new ones over. The visitor doesn't personally store any books — they just make requests and receive answers. Whether the "visitor" is a command-line tool, a GUI app, or your own backend service, they're all just clients talking to the same librarian (the Redis server).

## Diagram
```
                          +---------------------------+
                          |        Redis Server         |   <- the "librarian"
                          |  (stores & processes data)  |      holds ALL the data
                          +--------------+---------------+
                                         ^
                     sends commands,     |     receives responses
                     receives responses  |
        +----------------+   +----------+---------+   +------------------+
        |  redis-cli      |   |  Spring Boot App    |   |  RedisInsight GUI |
        |  (a client)     |   |  (a client, via      |   |  (a client)       |
        |                 |   |   RedisTemplate)     |   |                   |
        +----------------+   +---------------------+   +------------------+

All three are equally "just clients" — none of them hold the data themselves.
```

## Production Example
```java
@Service
public class SessionService {
    private final RedisTemplate<String, String> redisTemplate;

    public void save(String sessionId, String data) {
        redisTemplate.opsForValue().set("session:" + sessionId, data, Duration.ofMinutes(30));
        // Spring Boot is the CLIENT here — it sent a SET command to the Redis SERVER
    }
}
```

Whether ten instances of this Spring Boot service are running behind a load balancer, they're all just independent clients talking to the same central Redis server (or Redis cluster) — which is why Redis works so well as shared state across horizontally scaled application instances.

## Why Interviewers Ask This
It's a foundational architecture question that confirms a candidate understands the client-server separation clearly — a surprising number of engineers conflate "using Redis in my app" with "my app stores the data," when the application is always just a client issuing commands.
