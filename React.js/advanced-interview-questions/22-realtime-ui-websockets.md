# How do you handle real-time updates with WebSockets in React?

> **Interview priority:** SHOULD KNOW

## Question

How do you handle real-time updates with WebSockets in React?

## Beginner Lens

Watch the data flow: server sends events over WebSocket (new message, user typing, like notification), React component receives event and updates state, UI re-renders. The tricky parts are: (1) connecting/reconnecting WebSocket in useEffect, (2) merging real-time events with paginated data without duplicates, (3) handling stale events that arrive while user is scrolling or filtering, and (4) optimistic updates for better UX.

## Detailed Explanation

**HOW TO SAY IT (spoken to interviewer):**

> "WebSockets in React are deceptively simple in demos but complex in production. The core challenge is that events arrive asynchronously and out of order while your UI might be paginating, filtering, or showing cached data. I've seen apps show duplicate messages, lose messages during reconnect, or update the wrong user's data. The solution involves careful connection lifecycle management, event deduplication, and merging strategies. Let me show the exact failure scenarios..."

```
REAL APP: Chat Application — WebSocket Integration
─────────────────────────────────────────────────────────────────

NAIVE IMPLEMENTATION (has multiple bugs):
────────────────────────────────────────────────────────────────

function ChatRoom({ roomId }) {
  const [messages, setMessages] = useState([]);

  useEffect(() => {
    const ws = new WebSocket('ws://api.example.com/chat');
    
    ws.onopen = () => {
      console.log('Connected');
      ws.send(JSON.stringify({ type: 'join', roomId }));
    };
    
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      setMessages(prev => [...prev, message]);  // ← BUG: append everything
    };

    return () => ws.close();  // ← cleanup
  }, [roomId]);

  return (
    <div>
      {messages.map(msg => <Message key={msg.id} data={msg} />)}
    </div>
  );
}

BUGS:
─────────────────────────────────────────────────────────────────

1. DUPLICATE MESSAGES ON RECONNECT
   User loses internet → WebSocket disconnects → reconnects
   ├─ Component re-mounts or roomId changes
   ├─ New WebSocket created
   ├─ Server sends last 50 messages (initial sync)
   ├─ messages state ALREADY has those 50 messages
   └─ setMessages appends them AGAIN → 100 messages, 50 duplicates ❌

2. RACE CONDITION WITH API FETCH
   Component mounts:
   ├─ useEffect 1: fetch('/api/messages') → loads historical messages
   ├─ useEffect 2: new WebSocket() → receives new messages
   
   Timeline:
   t=0:    WebSocket connects, starts receiving events
   t=100:  Message A arrives via WebSocket → added to state
   t=200:  API fetch completes → loads messages including A
           └─ setMessages([...apiMessages]) → OVERWRITES WebSocket data ❌
              Message A appears twice or disappears

3. MEMORY LEAK ON UNMOUNT
   User switches rooms (roomId changes):
   ├─ Cleanup runs: ws.close()
   ├─ Old WebSocket closes
   ├─ BUT: Old WebSocket might still have buffered messages
   └─ onmessage handler still references OLD messages state (closure)
      └─ Can cause stale state updates ❌

4. NO ERROR HANDLING / RECONNECTION
   WebSocket connection drops:
   ├─ ws.onerror fires
   ├─ No recovery attempt
   └─ Chat stops working, user sees stale data ❌
```

```
VISUAL DIAGRAM — MESSAGE LIFECYCLE WITH WEBSOCKET:
─────────────────────────────────────────────────────────────────

User A sends message "Hello"

CLIENT (User A):
  1. User types "Hello" → clicks Send
  2. Optimistic update: add "Hello" to local state (pending state)
     UI shows: [Message: "Hello" (sending...)]
  3. HTTP POST /api/messages { text: "Hello" }
  4. Server responds: { id: "msg-123", text: "Hello", ... }
  5. Update local state: replace pending with confirmed
     UI shows: [Message: "Hello" ✓]

SERVER:
  6. Broadcasts WebSocket event to all connected clients
     { type: "new_message", message: { id: "msg-123", ... } }

CLIENT (User B, listening):
  7. Receives WebSocket event
  8. Checks: is msg-123 already in local state?
     ├─ YES → skip (User A already has it from HTTP response)
     └─ NO → add to state
  9. UI updates: new message appears ✅

PROBLEM WITHOUT DEDUPLICATION:
  User A sees "Hello" TWICE:
    - Once from optimistic update (step 2)
    - Again from WebSocket broadcast (step 7)
  ❌ Duplicate message
```

```
SOLUTION 1: PROPER WEBSOCKET LIFECYCLE MANAGEMENT
─────────────────────────────────────────────────────────────────

function ChatRoom({ roomId }) {
  const [messages, setMessages] = useState([]);
  const wsRef = useRef(null);  // stable reference

  useEffect(() => {
    // Fetch historical messages first
    const loadHistory = async () => {
      const res = await fetch(`/api/rooms/${roomId}/messages`);
      const data = await res.json();
      setMessages(data.messages);
    };

    loadHistory();

    // Then connect WebSocket
    const ws = new WebSocket(`ws://api.example.com/chat?room=${roomId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'new_message') {
        setMessages(prev => {
          // Deduplicate: check if message already exists
          if (prev.find(m => m.id === data.message.id)) {
            return prev;  // already have it, skip
          }
          return [...prev, data.message];  // add new message
        });
      }
      
      if (data.type === 'message_deleted') {
        setMessages(prev => prev.filter(m => m.id !== data.messageId));
      }
      
      if (data.type === 'message_edited') {
        setMessages(prev => prev.map(m =>
          m.id === data.message.id ? data.message : m
        ));
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('WebSocket closed');
      // Attempt reconnect after delay
      setTimeout(() => {
        if (wsRef.current === ws) {  // still the active WebSocket
          // trigger re-mount or manual reconnect
        }
      }, 3000);
    };

    return () => {
      wsRef.current = null;  // mark as stale
      ws.close();
    };
  }, [roomId]);

  const sendMessage = (text) => {
    const tempId = `temp-${Date.now()}`;
    const optimisticMessage = {
      id: tempId,
      text,
      author: 'Me',
      createdAt: new Date().toISOString(),
      status: 'pending'
    };

    // Optimistic update
    setMessages(prev => [...prev, optimisticMessage]);

    // Send to server
    fetch(`/api/rooms/${roomId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    })
      .then(res => res.json())
      .then(data => {
        // Replace temp message with real one
        setMessages(prev => prev.map(m =>
          m.id === tempId ? { ...data.message, status: 'sent' } : m
        ));
      })
      .catch(err => {
        // Mark as failed
        setMessages(prev => prev.map(m =>
          m.id === tempId ? { ...m, status: 'failed' } : m
        ));
      });
  };

  return (
    <div>
      {messages.map(msg => (
        <Message key={msg.id} data={msg} />
      ))}
    </div>
  );
}
```

```
SOLUTION 2: CUSTOM HOOK FOR WEBSOCKET
─────────────────────────────────────────────────────────────────

// Reusable WebSocket hook with reconnection

import { useEffect, useRef, useState } from 'react';

function useWebSocket(url, options = {}) {
  const {
    onMessage,
    onOpen,
    onClose,
    onError,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5
  } = options;

  const wsRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = (event) => {
        setIsConnected(true);
        reconnectAttemptsRef.current = 0;  // reset attempts
        onOpen?.(event);
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        onMessage?.(data);
      };

      ws.onerror = (error) => {
        onError?.(error);
      };

      ws.onclose = () => {
        setIsConnected(false);
        onClose?.();

        // Attempt reconnection
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++;
          console.log(`Reconnecting... (attempt ${reconnectAttemptsRef.current})`);
          setTimeout(connect, reconnectInterval);
        } else {
          console.error('Max reconnect attempts reached');
        }
      };
    };

    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [url]);

  const send = (data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    } else {
      console.error('WebSocket not connected');
    }
  };

  return { send, isConnected };
}

// Usage:
function ChatRoom({ roomId }) {
  const [messages, setMessages] = useState([]);

  const { send, isConnected } = useWebSocket(
    `ws://api.example.com/chat?room=${roomId}`,
    {
      onMessage: (data) => {
        if (data.type === 'new_message') {
          setMessages(prev => {
            if (prev.find(m => m.id === data.message.id)) return prev;
            return [...prev, data.message];
          });
        }
      },
      onOpen: () => console.log('Connected to chat'),
      onClose: () => console.log('Disconnected from chat')
    }
  );

  const sendMessage = (text) => {
    send({ type: 'send_message', text });
  };

  return (
    <div>
      {!isConnected && <div>Reconnecting...</div>}
      {messages.map(msg => <Message key={msg.id} data={msg} />)}
    </div>
  );
}
```

```
SOLUTION 3: HANDLING PAGINATION + WEBSOCKET
─────────────────────────────────────────────────────────────────

// User scrolls through paginated messages while WebSocket sends new ones

function ChatRoom({ roomId }) {
  const [messages, setMessages] = useState([]);
  const [hasOlderMessages, setHasOlderMessages] = useState(true);
  const messageIdsRef = useRef(new Set());  // track loaded message IDs

  // Load initial messages
  useEffect(() => {
    loadMessages();
  }, [roomId]);

  const loadMessages = async (beforeId = null) => {
    const url = beforeId
      ? `/api/rooms/${roomId}/messages?before=${beforeId}`
      : `/api/rooms/${roomId}/messages`;
    
    const res = await fetch(url);
    const data = await res.json();

    setMessages(prev => {
      const newMessages = data.messages.filter(
        msg => !messageIdsRef.current.has(msg.id)  // deduplicate
      );
      
      newMessages.forEach(msg => messageIdsRef.current.add(msg.id));
      
      return beforeId
        ? [...newMessages, ...prev]  // prepend older messages
        : [...prev, ...newMessages]; // append newer messages
    });

    setHasOlderMessages(data.hasMore);
  };

  // WebSocket for real-time messages
  useWebSocket(`ws://api.example.com/chat?room=${roomId}`, {
    onMessage: (data) => {
      if (data.type === 'new_message') {
        const msg = data.message;
        
        if (messageIdsRef.current.has(msg.id)) {
          return;  // already have it (from pagination or optimistic update)
        }

        messageIdsRef.current.add(msg.id);
        setMessages(prev => [...prev, msg]);  // append to end
      }
    }
  });

  const loadOlderMessages = () => {
    if (messages.length > 0) {
      const oldestMessage = messages[0];
      loadMessages(oldestMessage.id);
    }
  };

  return (
    <div>
      {hasOlderMessages && (
        <button onClick={loadOlderMessages}>Load older messages</button>
      )}
      {messages.map(msg => <Message key={msg.id} data={msg} />)}
    </div>
  );
}

KEY TECHNIQUE:
  - messageIdsRef tracks ALL loaded message IDs (from API + WebSocket)
  - When WebSocket event arrives, check if ID already in set
  - If yes: skip (deduplicate)
  - If no: add to state and set
  
  This prevents:
    ✅ Duplicates when API and WebSocket both deliver same message
    ✅ Out-of-order insertion (WebSocket event for message already loaded)
```

```
SOLUTION 4: TYPING INDICATORS (ephemeral state)
─────────────────────────────────────────────────────────────────

// Show "User is typing..." without storing in messages array

function ChatRoom({ roomId }) {
  const [messages, setMessages] = useState([]);
  const [typingUsers, setTypingUsers] = useState(new Set());

  useWebSocket(`ws://api.example.com/chat?room=${roomId}`, {
    onMessage: (data) => {
      if (data.type === 'user_typing') {
        setTypingUsers(prev => new Set(prev).add(data.userId));
        
        // Remove after 3 seconds (user stopped typing)
        setTimeout(() => {
          setTypingUsers(prev => {
            const next = new Set(prev);
            next.delete(data.userId);
            return next;
          });
        }, 3000);
      }
      
      if (data.type === 'user_stopped_typing') {
        setTypingUsers(prev => {
          const next = new Set(prev);
          next.delete(data.userId);
          return next;
        });
      }
      
      if (data.type === 'new_message') {
        // Remove from typing when message sent
        setTypingUsers(prev => {
          const next = new Set(prev);
          next.delete(data.message.authorId);
          return next;
        });
        
        setMessages(prev => [...prev, data.message]);
      }
    }
  });

  const handleTyping = useDebouncedCallback(() => {
    send({ type: 'typing', roomId });
  }, 500);

  return (
    <div>
      {messages.map(msg => <Message key={msg.id} data={msg} />)}
      {typingUsers.size > 0 && (
        <div>{Array.from(typingUsers).join(', ')} typing...</div>
      )}
      <input onChange={handleTyping} />
    </div>
  );
}
```

```
OPTIMISTIC UPDATES — BEST PRACTICES:
─────────────────────────────────────────────────────────────────

1. IMMEDIATE FEEDBACK
   User clicks "Like" button:
   ├─ Instantly update UI (show filled heart)
   ├─ Send request to server in background
   └─ If server fails, revert UI (show empty heart)

2. TEMP ID STRATEGY
   const tempId = `temp-${Date.now()}-${Math.random()}`;
   
   Add to state with tempId → send to server → replace tempId with real ID

3. STATUS TRACKING
   message.status: 'pending' | 'sent' | 'failed'
   
   Show different UI for each state:
   - pending: gray checkmark
   - sent: blue checkmark
   - failed: red X with retry button

4. ROLLBACK ON ERROR
   try {
     await sendMessage(text);
   } catch (err) {
     setMessages(prev => prev.filter(m => m.id !== tempId));
     toast.error('Failed to send message. Try again?');
   }
```

```
DEBUGGING CHECKLIST — "WebSocket messages duplicating/missing"
─────────────────────────────────────────────────────────────────

✅ Check message deduplication
   - Using Set or map to track loaded IDs?
   - Checking before adding to state?

✅ Check connection lifecycle
   - WebSocket reconnecting on every render? → Use ref
   - Old WebSocket still sending events? → Cleanup in useEffect

✅ Check race between API and WebSocket
   - Load history THEN connect WebSocket (not parallel)
   - Deduplicate using IDs, not timestamps

✅ Check event ordering
   - WebSocket sends events out of order?
   - Sort by timestamp before rendering

✅ Check optimistic updates
   - Temp message not being replaced? → Check ID matching logic
   - Duplicate after server confirms? → Deduplicate by ID

✅ DevTools Network tab
   - WebSocket connection count → should be 1 per room
   - Messages in WebSocket frames → inspect payload
```

> "The mental model: WebSocket is a stream of events that arrive asynchronously. Your React state is a snapshot. The challenge is merging the stream into the snapshot without duplicates or gaps. Use a Set to track what you've seen, deduplicate by ID, and separate ephemeral state (typing indicators) from persistent state (messages). Optimistic updates make the UI feel instant, but always handle rollback on failure."

**INTERVIEW FOLLOW-UP QUESTIONS:**

**Q: "What if the WebSocket connection is flaky?"**

> "Implement exponential backoff for reconnects. Use a library like `reconnecting-websocket` or build custom logic: first retry after 1s, then 2s, 4s, 8s, max 30s. Also queue messages while disconnected, send them on reconnect."

**Q: "How do you handle authentication with WebSockets?"**

> "Send auth token in initial WebSocket URL query param or in first message after connection. On server, validate token before accepting events. If token expires, server closes connection, client detects close, refreshes token, reconnects."

**Q: "What about scaling WebSockets across multiple servers?"**

> "Use Redis pub/sub or message queue. User A connects to Server 1, User B to Server 2. User A sends message → Server 1 publishes to Redis → Server 2 subscribes, receives event, sends to User B. All servers share the same event stream via Redis."
