Email Delivery System (Gmail / Outlook)

"User composes email → Compose Svc validates → Mail Send Svc → Outbox Delivery Orchestrator (SLA-based priority) → Kafka queues → SMTP relay to receiver → Receiver SMTP validates (SPF/DKIM/DMARC) → Inbox → Mailbox DB → Search indexed via Elastic Search"

1. Functional Requirements

Feature 1: User should be able to create a mailing account with unique email address
Feature 2: Users can compose and send emails to one or more recipients (To, Cc, Bcc)
Feature 3: Users can view their Inbox, Sent, Drafts, Spam, trash folders and create custom labels/folders
Feature 4: User should be able to search content across email subject, body, sender, attachments
Feature 5: Users should be able to send attachments (images, docs, PDFs up to 25MB per email)
Feature 6: Emails in the same conversation/replies are grouped together as threads
Feature 7: Support spam filtering, policy checks (PASS/FAIL/UNKNOWN), virus scanning
Feature 8: Reliable email delivery with retry mechanisms, bounce handling, delivery status notifications
2. Non-Functional Requirements

Scale
Users — 1.8B+ users with billions of emails sent/received daily
Storage — Petabytes of email data, attachments stored in S3/blob storage
Traffic — Millions of emails per minute during peak hours
Performance & Reliability
CAP Theorem — Availability >> Consistency, but highly consistent for same user account (no duplicate emails with same email_id)
Durability — Emails must be durable (11 9's via S3), no data loss on server failure
Reliability — Email delivery guaranteed with retry mechanisms, DLQ for failed deliveries
3. Core Entity

Entity 1: Users - user_id, email_address (unique), password_hash, name, quota (15GB default), created_at
Entity 2: Message/Email - email_id (unique across system), message_id (RFC 5322), thread_id (conversation grouping), from_email, to_emails[], cc_emails[], bcc_emails[], subject, body (HTML/plain text), has_attachment, url_attachment, sent_at, metadata
Entity 3: Thread/Conversation - thread_id, subject (first email subject), participant_emails[], email_ids[] (ordered by sent_at), last_updated_at, message_count
Entity 4: Email Metadata - labels[] (Inbox/Sent/Drafts/Spam/Trash/Custom), is_read, is_starred, importance (high/normal/low)
Entity 5: Mailbox_items (Inbox schema) - user_id, email_id, message_id, thread_id, from_email, to_emails, subject, snippet (first 100 chars of body), has_attachment, url_attachment (S3 URLs)
Entity 6: Outbox (pending sends) - user_id, email_id, message_id, thread_id, from_email, to_emails, subject, body, has_attachment, url_attachment, scheduled_at (for retry/delayed send)
Entity 7: Attachment - attachment_id, email_id, filename, size_bytes, content_type, s3_url (blob storage), virus_scan_status
4. API Designing

Account & Email Operations
POST /v1/accounts/register — Create new email account with unique email address (check availability)
POST /v1/emails/send — Send email with Body: {to: [], cc: [], bcc: [], subject, body, attachmentId, storageUrl}
GET /v1/emails/{emailId_UUID} — Get full email object including body, attachments, metadata (Response includes full Email object + attachments)
GET /v1/search?q='meeting tomorrow'&userId={XXXX1234} — Search emails by subject/body/sender, returns matching email IDs + snippets
Attachments
POST /v1/attachments/upload (multipart form) — Upload attachment to S3, returns {attachmentId, storageUrl} for use in send email
5. High Level Design

Architecture: clients/users/webclient → Load Balancer & API Gateway → Services (User Svc, Compose Svc, Mail Send Svc, Search Svc) → Databases
User Svc → User DB: Account creation, authentication, quota management (15GB default Gmail)
Compose Svc → Drafts DB: Save drafts, validate recipients, attachment handling (upload to S3)
Mail Send Svc → SMTP relay: Validates sender, anti-spam checks, routes to external SMTP servers (Gmail → Yahoo, Outlook → Gmail)
Search Svc → Mailbox DB + Elastic Search: Full-text search across subject/body/sender, indexed for fast queries
Mailbox DB: Stores Mailbox_items (Inbox) and Outbox (pending sends) with email metadata
Outside Internet: Receiver SMTP servers (Yahoo SMTP, Outlook SMTP) receive emails via SMTP protocol
Inbound SMTP Service: Receives emails from external senders (Outlook/Yahoo SMTP → Gmail Inbox)
6. Deep Dive Design (Low Level)

Step 1: Email Composition & Draft Saving
User composes email in web client: To: alice@yahoo.com, Cc: bob@outlook.com, Subject: 'Meeting Tomorrow', Body: 'Hi Alice...', Attachment: presentation.pdf (5MB)
Attachment upload (if present): POST /v1/attachments/upload with multipart/form-data {file: presentation.pdf}, Compose Service: Upload to S3: s3://email-attachments/{user_id}/{email_id}/presentation.pdf, Virus scan: ClamAV scans file, if infected → reject, else mark clean, Response: {attachmentId: 'ATT123', storageUrl: 's3://...', size: 5MB, contentType: 'application/pdf'}
Save draft (auto-save every 30 sec): POST /v1/emails/draft with {to: ['alice@yahoo.com'], cc: ['bob@outlook.com'], subject, body, attachmentId: 'ATT123'}, Compose Service: Generate email_id (UUID), message_id (RFC 5322: <{email_id}@gmail.com>), INSERT INTO drafts (email_id, user_id, to_emails, subject, body, has_attachment, url_attachment: 's3://...', updated_at: now()), Response: {emailId: 'E123', status: 'DRAFT'}
Draft retrieval: GET /v1/emails/E123 → returns full email object for editing
Step 2: Send Email Flow (Outbox & Delivery Orchestrator)
User clicks Send: POST /v1/emails/send with {emailId: 'E123'} (from draft) OR new email payload
Mail Send Service validation: (1) Check sender quota: SELECT used_quota, quota_limit FROM users WHERE user_id={user_id}, if used_quota >= quota_limit → return 403 'Quota exceeded', (2) Validate recipients: Check valid email format, resolve domain (DNS MX record lookup), anti-spoofing checks (sender domain verification), (3) Spam/policy check: Content analysis (suspicious keywords, excessive links), Rate limiting (max 500 emails/day for free users), CAPTCHA if suspicious pattern detected
Insert into Outbox: INSERT INTO outbox (user_id, email_id, message_id, thread_id, from_email, to_emails: ['alice@yahoo.com', 'bob@outlook.com'], subject, body, has_attachment, url_attachment, scheduled_at: now()) - Outbox table acts as durable queue
Publish to Kafka: Kafka.send('email.outbound', {emailId: 'E123', toEmails: ['alice@yahoo.com', 'bob@outlook.com'], priority: 'NORMAL', createdAt: timestamp}) - Topic: email.outbound with 100 partitions
Response to user: 200 OK {emailId: 'E123', status: 'SENDING'} - User sees email in Sent folder immediately (optimistic UI), actual delivery happens async
Step 3: Outbox Delivery Orchestrator (SLA-based Priority Processing)
Outbox Delivery Orchestrator consumes Kafka 'email.outbound' topic (100 consumer instances, one per partition)
SLA-based priority routing (6 scenarios): Scenario 1: Sending email to 'elixir (first time)' with no auto-suggestion → Validation DB checks recipient validity, no previous interaction → NORMAL priority queue, Scenario 2: Sending within same org (alice@gmail.com → bob@gmail.com) → auto-suggestion available from contacts → HIGH priority (faster delivery within same domain), Scenario 3: Sending to known contact (within google contacts) → auto-suggestion enabled → HIGH priority, Scenario 4: Sending email with critical subject keywords ('urgent', 'immediate', 'asap') → auto-suggestion might trigger → elevated priority, Scenario 5: Sending to external domain (first contact at new company) → no auto-suggestion → NORMAL priority, Scenario 6: Bulk/newsletter emails → LOW priority (rate limited, sent during off-peak)
Priority determination logic: IF (same_domain OR in_contacts): priority = 'HIGH', ELSE IF (subject contains urgent keywords): priority = 'ELEVATED', ELSE IF (bulk_send OR newsletter): priority = 'LOW', ELSE: priority = 'NORMAL'
Route to appropriate SMTP queue: Kafka topics: email.smtp.high (processed immediately, <1 min delivery), email.smtp.normal (processed within 5 min), email.smtp.low (processed within 30 min, rate limited)
Consistent hashing: Hash email by sending_user_id to maintain order (emails from same user processed by same consumer, preserves send order)
Step 4: SMTP Delivery & External Server Communication
SMTP Worker consumes from priority queues (High: 50 workers, Normal: 100 workers, Low: 20 workers)
Steps to Connect SMTP Server (detailed from image): 1. (Checks/Pings) DNS Request: dig MX outlook.com → MX records: outlook-com.olc.protection.outlook.com (priority 5), 2. MX Receiver Response: Returns SMTP server IP addresses, 3. SMTP connection: TCP connection to receiver SMTP (port 25/587/465), TLS handshake for encryption, 4. SMTP handshake: EHLO gmail.com (identify sending server), Receiver responds: 250-outlook.com Hello [IP], 5. (email) MAIL FROM command: MAIL FROM:<sender@gmail.com>, Receiver validates sender domain, 6. (email) RCPT TO command: RCPT TO:<alice@outlook.com>, Receiver checks if recipient exists (local delivery table), 7. (email) DATA command: Sends email headers + body, Subject:, From:, To:, Date:, Message-ID:, MIME headers for attachments, 8. (email) Email body: Plain text and/or HTML multipart, Base64 encoded attachments (if any), 9. (email) '.' (period): Signals end of email data, 10. (email) QUIT: Terminate connection, 11. (Checks) SPF record check: Receiver queries DNS TXT record for sender domain, spf.gmail.com TXT: 'v=spf1 ip4:74.125.0.0/16 ~all', Validates sending IP is authorized, 12. (Checks) DKIM signature: Email headers include DKIM-Signature, Receiver fetches public key from DNS: default._domainkey.gmail.com, Verifies signature matches email content (prevents tampering), 13. (Checks) DMARC check: Receiver checks DMARC policy at _dmarc.gmail.com, Policy: p=reject (strict) or p=quarantine or p=none, If SPF/DKIM fail + DMARC=reject → email rejected, 14. (Status) Delivery confirmation: 250 OK Message accepted for delivery, SMTP worker receives confirmation
Update outbox status: UPDATE outbox SET status='SENT', sent_at=now() WHERE email_id='E123', DELETE FROM outbox WHERE email_id='E123' (remove from pending queue)
Insert into Sent folder: INSERT INTO mailbox_items (user_id, email_id, folder: 'SENT', from_email, to_emails, subject, snippet, sent_at) - User can see email in Sent folder
Step 5: Receiving Email (Inbound SMTP Service)
External sender (Outlook/Yahoo SMTP) delivers to Gmail: SMTP connection to Gmail's MX servers (gmail-smtp-in.l.google.com)
Inbound SMTP Service receives: (1) MAIL FROM: <sender@outlook.com>, (2) RCPT TO: <recipient@gmail.com> → Check local cache: Does user exist?, (3) DATA → Receive full email content
Spam/Malware filtering: Spam/Malware Filtering Svc (consumes from Kafka): Content analysis: Bayesian filter (spam probability scoring), Sender reputation check (IP blacklist, domain reputation), Policy check: SPF/DKIM/DMARC validation (PASS/FAIL/UNKNOWN based on image), Link analysis: Check URLs against phishing database, Attachment scan: ClamAV virus scan, If spam score > 0.8 → mark as SPAM folder, If virus detected → quarantine/reject
Policy Check results: validation.spf (PASS/FAIL/UNKNOWN), validation.dkim (PASS/FAIL/UNKNOWN), spam_check (clean: PASS/FAIL/UNKNOWN), reputation_score
Insert into Mailbox: Kafka.send('email.inbound', {emailId, recipientEmail: 'recipient@gmail.com', ...}), Mailbox Receiver DB consumer: INSERT INTO mailbox_items (user_id, email_id, message_id, thread_id (if reply), from_email: 'sender@outlook.com', to_emails, subject, snippet, has_attachment, folder: 'INBOX' OR 'SPAM', is_read: false, received_at: now())
Thread detection: Check if email is reply (In-Reply-To header, References header match existing message_id), If match: UPDATE thread SET email_ids = array_append(email_ids, 'E456'), last_updated_at=now(), Else: Create new thread: INSERT INTO threads (thread_id, subject, participant_emails, email_ids: ['E456'])
Step 6: Search Indexing (Elastic Search)
Elastic Search Svc (asynchronous indexing): Consumes Kafka 'email.indexed' events (published on email insert to mailbox_items)
Index email content: POST /emails/_doc/{email_id} to Elasticsearch with {user_id, email_id, from_email, to_emails[], subject, body (full text), snippet, has_attachment, labels[], sent_at}, Fields indexed: subject (analyzed with ngram for autocomplete), body (full-text search), from_email (keyword), to_emails (keyword array), Analyzer: Standard analyzer + stemming (meeting → meet, meetings)
Search query: User searches 'meeting tomorrow', Query: GET /v1/search?q=meeting tomorrow&userId=U123, Elastic Search query: {query: {bool: {must: [{match: {subject: 'meeting tomorrow'}}, {match: {body: 'meeting tomorrow'}}], filter: [{term: {user_id: 'U123'}}]}}, sort: [{sent_at: 'desc'}]}, Response: {emailIds: ['E123', 'E456'], total: 2, results: [{emailId, subject, snippet, from, sentAt}]}
Autocomplete: As user types 'meet...', Elasticsearch completion suggester returns: ['meeting', 'meetings', 'meet and greet']
Step 7: Notification Service (Push/Email alerts)
Notification Svc consumes Kafka 'email.received' events
Determine notification preference: Check user settings (push enabled? email forwarding?), Importance: If from VIP sender OR subject contains important keywords → push notification, Else: silent notification (badge count update)
Push notification: FCM (Firebase Cloud Messaging) for mobile: POST https://fcm.googleapis.com/v1/.../messages:send with {token: device_token, notification: {title: 'New email from alice@yahoo.com', body: 'Meeting Tomorrow - Hi Bob...'}, data: {emailId: 'E456', threadId}}, User's device receives push, tapping opens email in app
Email forwarding (if configured): User has rule: 'Forward emails from boss@company.com to personal@gmail.com', Notification Svc triggers: POST /v1/emails/send (internal send) with modified headers (X-Forwarded-From)
7. Database Schema Details

Mailbox_items (Inbox/Sent/Spam/Trash)
Composite PK — (user_id, email_id) - ensures no duplicate emails for user
user_id — uuid FK → Users
email_id — uuid (globally unique email identifier)
message_id — varchar(255) (RFC 5322 Message-ID: <uuid@gmail.com>)
thread_id — uuid FK → Threads (conversation grouping)
from_email — varchar(255) (sender email address)
to_emails — text[] (array of recipient emails)
cc_emails — text[] (nullable, carbon copy)
bcc_emails — text[] (nullable, blind carbon copy - not visible to other recipients)
subject — text (email subject line)
snippet — text (first 100 chars of body for preview)
has_attachment — boolean (true if attachments present)
url_attachment — text (S3 URLs to attachments, comma-separated)
folder — varchar(50) (INBOX, SENT, DRAFTS, SPAM, TRASH, or custom label)
is_read — boolean DEFAULT false
is_starred — boolean DEFAULT false
received_at — timestamptz (when email arrived in mailbox)
Indexes — INDEX on (user_id, folder, received_at DESC) for folder listing, INDEX on (user_id, thread_id) for conversation view
Sharding — Shard by user_id (user's emails on same shard for fast queries)
Outbox (pending email sends)
Composite PK — (user_id, email_id)
user_id — uuid FK → Users
email_id — uuid
message_id — varchar(255)
thread_id — uuid (if reply, links to existing thread)
from_email — varchar(255)
to_emails — text[]
subject — text
body — text (full email body, HTML or plain text)
has_attachment — boolean
url_attachment — text (S3 URLs)
scheduled_at — timestamptz (when to send, for retry scheduling)
retry_count — int DEFAULT 0 (number of send attempts)
status — enum (PENDING, SENDING, SENT, FAILED)
created_at — timestamptz
Purpose — Durable queue for outbound emails, ensures no email lost on server crash
Threads (conversation grouping)
thread_id — uuid PRIMARY KEY
subject — text (subject of first email in thread)
participant_emails — text[] (all unique emails in thread - from, to, cc)
email_ids — uuid[] (ordered array of email IDs in thread, oldest to newest)
last_updated_at — timestamptz (when last email added)
message_count — int (number of emails in thread)
Indexes — INDEX on participant_emails (GIN index for array containment queries)
Users
user_id — uuid PRIMARY KEY
email_address — varchar(255) UNIQUE (user@gmail.com)
password_hash — varchar(255) (bcrypt hashed)
name — varchar(255)
quota_limit — bigint (15GB = 15 × 1024³ bytes for free Gmail)
quota_used — bigint (bytes used, updated on email/attachment storage)
created_at — timestamptz
last_login_at — timestamptz
Attachments
attachment_id — uuid PRIMARY KEY
email_id — uuid FK → Mailbox_items
filename — varchar(255) (presentation.pdf)
size_bytes — bigint (5MB = 5 × 1024²)
content_type — varchar(100) (application/pdf, image/jpeg)
s3_url — text (s3://email-attachments/{user_id}/{email_id}/{filename})
virus_scan_status — enum (PENDING, CLEAN, INFECTED)
uploaded_at — timestamptz
Kafka Topics
email.outbound — Outbound emails to be sent (100 partitions by user_id hash), consumed by Outbox Delivery Orchestrator
email.smtp.high — High priority SMTP delivery queue (same domain, known contacts), 50 SMTP workers
email.smtp.normal — Normal priority SMTP queue (external first-time contacts), 100 workers
email.smtp.low — Low priority SMTP queue (bulk/newsletters), 20 workers, rate limited
email.inbound — Received emails from external SMTP, consumed by Mailbox Receiver DB service
email.indexed — Emails to be indexed in Elasticsearch, consumed by Elastic Search Svc
email.received — New email notification events, consumed by Notification Svc for push/email alerts
Elasticsearch Index
Index name — emails
Fields — user_id (keyword), email_id (keyword), from_email (keyword), to_emails (keyword array), subject (text with ngram), body (text with standard analyzer + stemming), snippet (text), has_attachment (boolean), folder (keyword), sent_at (date)
Sharding — 10 shards per index, route by user_id hash
8. Scaling & Optimization

Technique 1: Outbox pattern - Durable queue for outbound emails (INSERT into outbox → Kafka publish → SMTP send → DELETE from outbox), prevents email loss on server crash, enables retry with exponential backoff
Technique 2: SLA-based priority queues - 3 Kafka topics (high/normal/low priority), high priority for same domain (gmail→gmail) and known contacts (<1 min delivery), normal for external (5 min), low for bulk (30 min, rate limited), worker allocation: 50/100/20 for high/normal/low
Technique 3: Consistent hashing - Hash emails by sending_user_id to same Kafka partition, ensures send order preserved (user sends Email A then Email B → A delivered before B), prevents out-of-order delivery
Technique 4: Database sharding - Mailbox_items sharded by user_id (user's emails on same shard), enables horizontal scaling to billions of emails, shard routing: hash(user_id) mod N
Technique 5: Elasticsearch for search - Full-text search on subject/body with stemming (meeting → meet), ngram for autocomplete, aggregations for faceted filters (folder, has_attachment, date range), 10 shards per index, <100ms query latency
Technique 6: S3 for attachments - Store attachments in blob storage (not DB), presigned URLs for direct upload (bypasses server), lifecycle policies (archive to Glacier after 1 year), saves 90% cost for old attachments, virus scan before allowing download
Technique 7: Kafka event-driven architecture - Decouples services (Mail Send → SMTP Workers → Mailbox Receiver → Search Indexer → Notification), async processing (user gets 200 OK immediately, actual delivery happens later), enables horizontal scaling (add more consumers)
Technique 8: SMTP connection pooling - Maintain persistent connections to frequently contacted domains (gmail.com → outlook.com reuses TCP connection), reduces handshake overhead (TLS setup ~200ms), connection pool size: 100 per SMTP worker
Technique 9: Spam filtering pipeline - Multi-stage: (1) IP reputation check (blacklist lookup <10ms), (2) SPF/DKIM/DMARC validation (DNS queries ~50ms), (3) Content analysis (Bayesian filter ~100ms), (4) Link/attachment scan (~200ms), total <400ms, parallel processing where possible
Technique 10: Thread detection caching - Cache recent threads in Redis (key: message_id, value: thread_id), TTL 7 days, avoids DB query on every reply, 95% cache hit rate for active conversations
Technique 11: Read replica scaling - 1 master (writes: new emails, outbox updates) + 10 read replicas (reads: inbox listing, search results, thread views), read/write split, replicas lag <1 sec (acceptable for email viewing)
Technique 12: Rate limiting - Per user: 500 emails/day for free accounts, 2000/day for paid, per IP: 100 requests/min to prevent spam bots, per domain: Gradual ramp-up when sending to new domain (first 10 emails slow, then increase if no bounces)
9. Common Interview Questions

Q
How do you ensure reliable email delivery with retry mechanisms and handle failures?
A
Reliable email delivery with Outbox pattern and retry logic:

(1) Outbox pattern (durable queue): When user sends email, INSERT INTO outbox table (durable storage), Publish to Kafka 'email.outbound', SMTP worker processes, If successful: DELETE FROM outbox, If failed: Keep in outbox for retry, Guarantees: Email survives server crash (persisted in DB), At-least-once delivery (retry until success or max attempts).

(2) Retry strategy: Exponential backoff: 1st retry after 1 min, 2nd after 5 min, 3rd after 15 min, max 10 attempts over 24 hours, Retry conditions: Temporary failures (4xx SMTP codes like 421 Service unavailable, 450 Mailbox busy), Network timeouts, Receiver server down.

(3) Failure handling: Permanent failures (5xx codes like 550 User not found, 552 Mailbox full): Stop retrying, Mark status='FAILED', Send bounce notification to sender: 'Delivery failed: User alice@yahoo.com does not exist', INSERT into sender's inbox as system message.

(4) Dead Letter Queue (DLQ): After max retries (10 attempts, 24 hours), Move to DLQ Kafka topic: 'email.failed', Manual investigation by ops team, Possible issues: Misconfigured recipient server, Persistent network partition, Invalid recipient that passed initial validation.

(5) Delivery confirmation: SMTP 250 OK response → email accepted by receiver, UPDATE outbox SET status='SENT', sent_at=now(), DELETE FROM outbox, Receiver may still reject later (after accepting via SMTP) due to spam filters, Track final delivery via DSN (Delivery Status Notification) if supported.

(6) Idempotency: Same email_id sent multiple times (due to retries) → receiver deduplicates by message_id header: Message-ID: <{email_id}@gmail.com>, Prevents duplicate emails in user's inbox. Result: Guaranteed delivery with at-least-once semantics, graceful failure handling with user notification, durable queue survives failures, exponential backoff prevents overwhelming receiver.

Q
How does the Outbox Delivery Orchestrator implement SLA-based priority routing?
A
SLA-based priority routing with 6 scenarios:

(1) Priority determination: HIGH priority (target <1 min delivery): Same domain (gmail.com → gmail.com, internal routing), Known contacts (recipient in sender's contacts, auto-suggestion enabled), VIP senders (emails from boss@company.com), NORMAL priority (target 5 min): External first-time contact (gmail.com → yahoo.com, no prior interaction), Subject doesn't contain urgent keywords, LOW priority (target 30 min): Bulk sends (>100 recipients), Newsletter emails (detected by unsubscribe link, bulk headers), Marketing campaigns (tagged by sender).

(2) Implementation: Outbox Delivery Orchestrator consumes 'email.outbound', Determines priority: IF (recipient_domain == sender_domain): priority = 'HIGH' // Same domain, ELSE IF (recipient IN sender_contacts): priority = 'HIGH' // Known contact, ELSE IF (subject CONTAINS ['urgent', 'asap', 'immediate']): priority = 'ELEVATED', ELSE IF (recipient_count > 100 OR 'List-Unsubscribe' header present): priority = 'LOW', ELSE: priority = 'NORMAL', Routes to Kafka topic: email.smtp.{priority}, Kafka.send('email.smtp.high', emailPayload) or 'email.smtp.normal' or 'email.smtp.low'.

(3) Worker allocation: HIGH: 50 SMTP workers (dedicated, always available for fast delivery), NORMAL: 100 workers (majority of traffic, balanced capacity), LOW: 20 workers (rate limited, processes during off-peak to avoid impacting high/normal).

(4) Auto-suggestion correlation: Scenarios 1-6 from image all reference auto-suggestion, Auto-suggestion = recipient appears in sender's contact list or has prior email interaction, Enables HIGH priority routing (faster delivery for known contacts improves user experience).

(5) Rate limiting per priority: HIGH: No rate limit (immediate processing), NORMAL: 1000 emails/min per domain (gradual ramp-up for new domains), LOW: 100 emails/min per domain (prevents spam, spreads load).

(6) Monitoring: Track SLA compliance: % of HIGH priority emails delivered <1 min (target 99%), % of NORMAL delivered <5 min (target 95%), % of LOW delivered <30 min (target 90%), Alert if SLA violated (queue backlog, worker shortage). Result: Fast delivery for important emails (same domain, known contacts), efficient resource allocation (most workers on normal priority), abuse prevention (bulk emails rate limited), SLA-driven user experience.

Q
Walk through the complete SMTP delivery process with SPF, DKIM, and DMARC validation.
A
Complete SMTP delivery with authentication:

(1) DNS MX lookup: SMTP worker needs to send to alice@outlook.com, Query DNS: dig MX outlook.com, Response: outlook-com.olc.protection.outlook.com (priority 5) with IP addresses, Select lowest priority MX server (priority 5 = highest priority in MX records, lower number = higher priority).

(2) TCP connection: Connect to receiver SMTP server: TCP connection to outlook-com.olc.protection.outlook.com:25 (SMTP), Or port 587 (submission), port 465 (SMTPS with TLS), TLS handshake: STARTTLS command → upgrade to encrypted connection, Prevents email interception (MITM attacks).

(3) SMTP handshake: Client (Gmail SMTP worker): EHLO gmail.com, Server (Outlook): 250-outlook.com Hello [74.125.0.1], Server lists supported extensions: 250-STARTTLS, 250-AUTH PLAIN LOGIN, 250-SIZE 35000000 (max 35MB email).

(4) Sender verification: Client: MAIL FROM:<sender@gmail.com>, Server: 250 OK (accepts sender, may check later via SPF).

(5) Recipient verification: Client: RCPT TO:<alice@outlook.com>, Server checks local delivery table: SELECT user_id FROM users WHERE email='alice@outlook.com', If exists: 250 OK, If not exists: 550 User not found (reject, sender gets bounce).

(6) Email transmission: Client: DATA, Server: 354 Start mail input; end with <CRLF>.<CRLF>, Client sends headers + body: From: sender@gmail.com, To: alice@outlook.com, Subject: Meeting Tomorrow, Date: Mon, 26 Jan 2026 10:30:00 -0800, Message-ID: <E123@gmail.com>, DKIM-Signature: v=1; a=rsa-sha256; d=gmail.com; s=default; h=from:to:subject; bh=base64hash; b=signaturebase64, Content-Type: multipart/mixed (if attachments), Blank line, Email body (plain text or HTML), Attachments (Base64 encoded), Client: . (period on line by itself = end of message).

(7) SPF validation (Sender Policy Framework): Server queries DNS: dig TXT gmail.com → spf.gmail.com, Response: v=spf1 ip4:74.125.0.0/16 ip4:74.125.224.0/19 ~all, Server checks: Is sending IP (74.125.0.1) in allowed ranges?, Result: PASS (IP authorized) or FAIL (unauthorized IP, likely spoofed), If FAIL: May reject email or mark as spam.

(8) DKIM validation (DomainKeys Identified Mail): Server extracts DKIM-Signature header from email: d=gmail.com (signing domain), s=default (selector, identifies which key to use), h=from:to:subject (signed headers), bh=hash of body, b=signature of headers, Server fetches public key: dig TXT default._domainkey.gmail.com, Response: Public key (RSA or Ed25519), Server verifies: Hash email body → compare with bh, Sign headers using public key → compare with b, Result: PASS (signature valid, email not tampered) or FAIL (signature invalid, email modified).

(9) DMARC validation (Domain-based Message Authentication): Server queries: dig TXT _dmarc.gmail.com, Response: v=DMARC1; p=reject; rua=mailto:dmarc@gmail.com (policy=reject strict, report aggregate to dmarc@gmail.com), Server checks alignment: Does 'From' header domain (gmail.com) match SPF/DKIM domain?, SPF: MAIL FROM domain = gmail.com? (aligned), DKIM: d= domain = gmail.com? (aligned), If SPF PASS AND aligned: DMARC PASS, If DKIM PASS AND aligned: DMARC PASS, If both FAIL + policy=reject: Reject email (550 DMARC policy violation), If both FAIL + policy=quarantine: Accept but mark as spam, If both FAIL + policy=none: Accept, log only.

(10) Final acceptance: If all checks pass (SPF, DKIM, DMARC, spam filters), Server: 250 OK Message accepted for delivery, Client: QUIT, Server: 221 Goodbye (close connection).

(11) Post-delivery: Server inserts email into alice@outlook.com's mailbox, Sends DMARC aggregate report to gmail.com (daily summary of auth results), Gmail tracks delivery confirmation, updates outbox status='SENT'. Result: Authenticated email delivery with anti-spoofing protection, SPF prevents IP spoofing, DKIM prevents email tampering, DMARC enforces policy, ensures legitimate emails delivered, spam/phishing blocked.

Key Interview Tips

⚠️
CRITICAL: Outbox pattern mandatory for reliable email delivery. NEVER publish to Kafka without persisting to Outbox DB first. If Kafka publish succeeds but server crashes before DB commit → email lost. Outbox guarantees at-least-once delivery (email survives crashes, retries until success).

⭐
Interviewers ALWAYS ask: 'How ensure email delivery?'. Answer: Outbox pattern (durable DB queue) + Kafka + SMTP workers with exponential backoff retry (1min, 5min, 15min, max 10 attempts 24hr). Failures → bounce notification. DLQ for manual investigation. Idempotency via message_id header.

💡
SLA-based priority routing: HIGH (same domain, known contacts, <1min, 50 workers), NORMAL (external first-time, 5min, 100 workers), LOW (bulk/newsletters, 30min, 20 workers). Auto-suggestion correlates with known contacts → HIGH priority for better UX.

⭐
SMTP authentication triple-check: SPF (validates sending IP authorized for domain, DNS TXT spf.gmail.com), DKIM (validates email not tampered, signature verification with public key from DNS), DMARC (enforces policy: reject/quarantine/none, requires SPF or DKIM alignment).

⚠️
NEVER store email body in Kafka messages. Email body can be large (25MB with attachments). Kafka message size limit 1MB. Store in DB, pass only email_id in Kafka. SMTP worker fetches full email from DB when processing. Keeps Kafka lightweight, prevents broker overload.

💡
Thread detection: Check In-Reply-To and References headers for existing message_id. If match → UPDATE thread (append email_id to array). Else → CREATE new thread. Cache recent threads in Redis (message_id → thread_id, 7 day TTL, 95% hit rate) avoids DB query on every reply.

⭐
Database sharding by user_id: User's emails on same shard (fast folder listing, thread view). Partition key: hash(user_id) mod N. Cross-shard query only for global search (uses Elasticsearch). Enables horizontal scaling to billions of users, each shard handles millions.