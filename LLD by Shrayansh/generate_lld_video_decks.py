#!/usr/bin/env python3
"""Build a scenario-first LLD interview deck beside every transcript."""
from html import escape
from pathlib import Path
import re

ROOT = Path(__file__).parent

CSS = '''<style>@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');*{box-sizing:border-box}:root{--bg:#07111d;--s:#0c1a2a;--s2:#10253a;--line:#25435b;--ink:#e8f1f7;--muted:#9cb5c9;--blue:#5eb5ff;--cyan:#5eead4;--lime:#a3e635;--red:#fb7185}body{margin:0;background:var(--bg);color:var(--ink);font-family:'DM Sans',sans-serif;height:100vh;overflow:hidden}#p{height:100vh;display:flex;flex-direction:column}header,footer{background:var(--s);display:flex;align-items:center;padding:9px 24px;border-color:var(--line);border-style:solid}header{justify-content:space-between;border-width:0 0 1px}footer{justify-content:space-between;border-width:1px 0 0}.name{font-size:12px;color:var(--blue);font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:75vw}.counter{font:11px 'IBM Plex Mono',monospace;color:var(--muted)}#progress{height:3px;background:#102238}#progress i{display:block;height:100%;background:linear-gradient(90deg,var(--blue),var(--cyan));transition:width .25s}.stage{flex:1;min-height:0}.slide{display:none;height:100%;overflow:auto;padding:18px max(24px,calc((100vw - 1360px)/2));animation:in .25s ease}.slide.active{display:block}@keyframes in{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}h1{font-size:clamp(2rem,4vw,3.7rem);line-height:1.08;margin:0}h2{font-size:1.34rem;margin:0 0 12px;color:var(--blue)}.eye{font:700 10px 'IBM Plex Mono',monospace;color:var(--cyan);letter-spacing:.08em;text-transform:uppercase;margin-bottom:8px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.grid3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.card{background:var(--s);border:1px solid var(--line);border-radius:7px;padding:13px 15px}.card h3{font-size:.9rem;color:var(--cyan);margin:0 0 7px}p,li{font-size:.88rem;line-height:1.55;color:var(--muted);margin:0}ul{padding-left:18px;margin:0}li{margin:4px 0}strong{color:var(--ink)}.quote{border-left:3px solid var(--cyan);padding:13px 16px;background:#092033;color:#d9e9f5;font-size:.95rem;line-height:1.62;border-radius:0 7px 7px 0}.diagram,.api{background:#04101c;border:1px solid var(--line);border-radius:7px;padding:12px;font:12px/1.58 'IBM Plex Mono',monospace;white-space:pre;overflow:auto;color:#bad3e7}.api{white-space:pre-wrap}.why{border-left:3px solid var(--lime);background:#102311;color:#d9f99d;padding:11px 14px;border-radius:0 7px 7px 0;font-size:.87rem;line-height:1.55;margin-top:10px}.trap{border-left:3px solid var(--red);background:#280f1b;color:#fecdd3;padding:11px 14px;border-radius:0 7px 7px 0;font-size:.87rem;line-height:1.55;margin-top:10px}.tag{display:inline-block;border:1px solid var(--line);border-radius:99px;padding:3px 8px;color:var(--muted);font-size:10px;margin:2px}table{width:100%;border-collapse:collapse;font-size:.8rem}th{text-align:left;color:var(--blue);padding:7px;border-bottom:1px solid var(--line)}td{color:var(--muted);padding:7px;border-bottom:1px solid #183048;vertical-align:top}.title{height:100%;display:flex;align-items:center;justify-content:center;text-align:center;flex-direction:column;padding:24px}.title p{max-width:760px;margin-top:14px}.btn{background:var(--s2);border:1px solid var(--line);color:var(--ink);font:600 12px 'DM Sans',sans-serif;padding:6px 15px;border-radius:5px;cursor:pointer}.dots{display:flex;gap:4px;max-width:55vw;flex-wrap:wrap;justify-content:center}.dot{width:6px;height:6px;border-radius:50%;border:0;background:var(--line);padding:0;cursor:pointer}.dot.active{background:var(--blue);transform:scale(1.35)}@media(max-width:720px){.grid,.grid3{grid-template-columns:1fr}.slide{padding:15px 16px}.diagram{font-size:10px}.dots{display:none}.name{max-width:60vw}}</style>'''

def title_for(source, fallback):
    line = source.splitlines()[0] if source else ''
    line = re.sub(r'^#\s*Index\s+\d+\s*\|\s*Video\s+\d+\s*\|\s*', '', line)
    return re.sub(r'\s*(?:--?|—)\s*Transcript\s*$', '', line).strip() or fallback.replace('_', ' ')

def excerpt(source):
    text = re.sub(r'\*\*\[\d+\]\*\*|\s+', ' ', source).strip()
    return text[:360].rsplit(' ', 1)[0] + '...' if len(text) > 360 else text

def profile(title):
    """Return production vocabulary for every LLD topic, not generic placeholders."""
    key = title.lower()
    systems = {
        'tic tac toe': ('two players submit moves simultaneously', 'Game', 'Board, Player, Move', 'POST /games/{id}/moves', 'cell must be empty; version prevents stale moves', 'Chess clock and multiplayer lobby', 'in-memory game state and Redis pub/sub'),
        'elevator': ('a lunchtime burst creates conflicting floor requests', 'ElevatorController', 'Elevator, Request, Door, Scheduler', 'POST /elevators/requests', 'one car accepts a request; scheduler avoids starvation', 'SCAN and LOOK scheduling', 'priority queue and event stream'),
        'car rental': ('two customers try to reserve the last available car', 'Reservation', 'Vehicle, Branch, Customer, Payment', 'POST /reservations', 'a vehicle cannot have overlapping confirmed reservations', 'PostgreSQL exclusion constraint', 'Redis availability cache'),
        'logging system': ('a production outage needs consistent filtering and routing', 'LogEvent', 'Logger, Appender, Formatter, Level', 'POST /logs', 'never block the request path on a slow sink', 'Logback async appenders', 'Kafka for durable central ingestion'),
        'snake and ladder': ('a turn must resolve dice, jump, and winning state consistently', 'Game', 'Board, Player, Dice, Snake, Ladder', 'POST /games/{id}/turns', 'only current player advances; final position is deterministic', 'seeded random generator', 'event-sourced move history'),
        'bookmyshow': ('thousands of users race for the same premiere seats', 'Booking', 'Show, Seat, SeatHold, Payment, Ticket', 'POST /shows/{showId}/holds', 'a seat hold expires and only one payment confirms it', 'PostgreSQL row lock', 'Redis TTL holds plus DB confirmation'),
        'vending machine': ('payment succeeds but a product cannot be dispensed', 'VendingMachine', 'Slot, Product, CashSession, State', 'POST /machines/{id}/sessions', 'balance, stock, and state transition stay consistent', 'State pattern', 'hardware adapter and transaction journal'),
        'atm': ('cash dispense fails after account debit is requested', 'Withdrawal', 'Card, Account, CashCassette, Transaction', 'POST /atms/{id}/withdrawals', 'debit and dispense need compensation and an audit trail', 'ISO 8583 adapter', 'saga with reversal transaction'),
        'chess': ('an online move arrives after another player has moved', 'ChessGame', 'Board, Piece, Move, Player, Clock', 'POST /games/{id}/moves', 'only legal moves on the current turn change the board', 'bitboard move engine', 'optimistic version plus WebSocket'),
        'file system': ('a folder move risks forming a cycle and corrupting the tree', 'Directory', 'File, Directory, Permission, Path', 'POST /directories/{id}/children', 'a directory cannot become its own descendant', 'Composite pattern', 'materialized path versus adjacency list'),
        'splitwise': ('an edited expense must not silently corrupt member balances', 'Expense', 'Group, Member, Split, Balance, Settlement', 'POST /groups/{id}/expenses', 'split amounts exactly equal the expense total', 'BigDecimal and append-only ledger', 'simplified debt graph'),
        'cricbuzz': ('millions of fans refresh during the last over', 'Match', 'Match, Innings, Over, Delivery, Scorecard', 'POST /matches/{id}/deliveries', 'a delivery is scored exactly once and in order', 'event sourcing for score', 'Redis fanout cache and WebSocket'),
        'inventory': ('two warehouses allocate the last unit at the same time', 'InventoryItem', 'SKU, Warehouse, StockReservation, Order', 'POST /inventory/reservations', 'available quantity cannot go below zero', 'atomic SQL conditional update', 'reservation expiry and reconciliation'),
        'word processor': ('a document with 100K repeated characters becomes memory-heavy', 'Document', 'CharacterStyle, Glyph, Paragraph, Cursor', 'POST /documents/{id}/operations', 'shared style must be immutable across documents', 'Flyweight style cache', 'rope versus piece-table document buffer'),
        'undo': ('a user edits, undoes, then makes a new edit', 'CommandHistory', 'Command, Memento, Editor, History', 'POST /documents/{id}/commands', 'a new command invalidates the redo branch', 'Command pattern', 'memento snapshots versus inverse operations'),
        'auction': ('two bids arrive at auction close with the same amount', 'Auction', 'Lot, Bid, Bidder, AuctionMediator', 'POST /auctions/{id}/bids', 'close time and winner selection are deterministic', 'database time and row lock', 'event-driven bidder notifications'),
        'coupons': ('several promotions compete and one order must remain auditable', 'Cart', 'CartItem, Coupon, Rule, Discount', 'POST /carts/{id}/coupons', 'discount order and cap are deterministic', 'rule strategy chain', 'promotion snapshot for audit'),
        'payment gateway': ('a client times out although the payment provider may have charged', 'Payment', 'PaymentIntent, Attempt, Provider, Refund', 'POST /payments', 'one merchant idempotency key creates one charge', 'provider adapter and idempotency', 'outbox webhook processing'),
        'object pool': ('expensive connections need reuse without leaking broken instances', 'ObjectPool', 'PooledObject, Lease, Factory, Validator', 'POST /pool/leases', 'a lease is returned once and invalid objects are discarded', 'bounded blocking pool', 'HikariCP versus direct allocation'),
    }
    for needle, values in systems.items():
        if needle in key:
            scenario, aggregate, entities, api, rule, choice_a, choice_b = values
            return {'scenario': scenario, 'aggregate': aggregate, 'entities': entities, 'api': api, 'rule': rule, 'choice_a': choice_a, 'choice_b': choice_b, 'kind': 'system'}
    patterns = {
        'strategy': ('a new pricing or driving algorithm must ship without changing every caller', 'Context', 'Strategy, ConcreteStrategy, Client', 'the context delegates a variable algorithm', 'composition with injected policies', 'inheritance with overrides'),
        'observer': ('an order change must notify email, analytics, and loyalty without coupling them', 'Order', 'Subject, Event, Subscriber, Subscription', 'publish after state commits; subscribers are idempotent', 'domain events', 'direct synchronous callbacks'),
        'decorator': ('a response needs optional compression, encryption, and metrics in combinations', 'RequestPipeline', 'Component, Decorator, ConcreteDecorator', 'each wrapper preserves the component contract', 'decorator chain', 'subclass explosion'),
        'factory': ('provider-specific objects must be chosen from configuration, not client code', 'ProviderFactory', 'Factory, Product, ProviderConfig', 'creation is centralized and validated', 'factory registry', 'new expressions scattered in callers'),
        'proxy': ('a remote or protected resource needs access control and caching before invocation', 'ResourceProxy', 'Subject, Proxy, RealSubject, Policy', 'the proxy preserves authorization and timeout semantics', 'proxy interceptor', 'caller-owned checks'),
        'null object': ('optional behaviour should not spread null checks across a transaction flow', 'NotificationPolicy', 'Policy, NullPolicy, RealPolicy', 'absence is represented as safe no-op behaviour', 'null object', 'nullable dependency checks'),
        'adapter': ('a legacy bank SDK has an incompatible model but must be safely integrated', 'PaymentAdapter', 'Target, Adapter, Adaptee, Translator', 'translation preserves money, errors, and idempotency', 'anti-corruption adapter', 'leaking vendor DTOs'),
        'builder': ('an immutable request has many optional fields and invalid combinations', 'RequestBuilder', 'Builder, Request, ValidationRule', 'build validates cross-field invariants once', 'fluent builder', 'telescoping constructors'),
        'facade': ('a checkout must hide inventory, tax, payment, and shipping orchestration', 'CheckoutFacade', 'Facade, Inventory, Payment, Shipping', 'the facade defines transaction and compensation boundaries', 'facade with application service', 'clients orchestrating subsystems'),
        'bridge': ('message type and delivery channel vary independently', 'Message', 'Abstraction, Implementor, Channel', 'both dimensions evolve without cross-product subclasses', 'bridge composition', 'type-channel inheritance matrix'),
        'iterator': ('a collection must expose ordered traversal without exposing its storage', 'Collection', 'Aggregate, Iterator, Cursor', 'cursor state is isolated per client', 'iterator interface', 'leaking internal list'),
        'visitor': ('new reporting operations are added to stable object types', 'Document', 'Element, Visitor, ConcreteVisitor', 'double dispatch selects behaviour by element type', 'visitor for stable hierarchy', 'type-switch in every operation'),
        'memento': ('an editor needs rollback without exposing every internal field', 'Editor', 'Originator, Memento, Caretaker', 'memento is opaque outside the originator', 'memento history', 'public mutable state snapshot'),
        'template method': ('a payment workflow is fixed while provider steps differ', 'PaymentWorkflow', 'Template, Hook, ConcreteWorkflow', 'invariant order is owned by the template', 'template method', 'duplicated workflow methods'),
        'interpreter': ('business users define small pricing expressions that must run safely', 'Expression', 'Expression, Context, Parser, AST', 'grammar and evaluation limits prevent unsafe input', 'parsed AST interpreter', 'eval on raw user text'),
        'mvc': ('web delivery must evolve without mixing view rendering and domain rules', 'Controller', 'Controller, Model, View, Service', 'controller coordinates but does not own business rules', 'Spring MVC layers', 'fat controller'),
        'solid': ('a small feature change currently ripples through unrelated classes', 'Module', 'Client, Abstraction, Implementation', 'each class has one reason to change', 'dependency inversion', 'concrete cross-layer dependency'),
        'liskov': ('a subtype rejects behaviour its parent promises to support', 'Contract', 'BaseType, Subtype, Client', 'subtypes preserve preconditions and postconditions', 'composition for incompatible behaviour', 'invalid subtype override'),
    }
    for needle, values in patterns.items():
        if needle in key:
            scenario, aggregate, entities, rule, choice_a, choice_b = values
            return {'scenario': scenario, 'aggregate': aggregate, 'entities': entities, 'api': 'POST /api/v1/commands', 'rule': rule, 'choice_a': choice_a, 'choice_b': choice_b, 'kind': 'pattern'}
    if 'roadmap' in key:
        return {'scenario': 'a senior engineer turns an ambiguous product request into an interview-ready design plan', 'aggregate': 'DesignRoadmap', 'entities': 'Requirement, Constraint, Decision, Validation', 'api': 'POST /design-roadmaps', 'rule': 'each technology choice must trace to a requirement and a failure mode', 'choice_a': 'incremental vertical slices', 'choice_b': 'big-bang component design', 'kind': 'roadmap'}
    if 'what is lld' in key:
        return {'scenario': 'a checkout feature needs a model that remains safe when discounts, payments, and delivery options evolve', 'aggregate': 'Checkout', 'entities': 'Cart, PriceRule, Payment, Order', 'api': 'POST /checkouts', 'rule': 'an order can be confirmed only after its price and payment are valid', 'choice_a': 'domain-driven object model', 'choice_b': 'transaction script', 'kind': 'introduction'}
    return {'scenario': 'a team needs a maintainable path from requirement to production code', 'aggregate': 'DesignDecision', 'entities': 'Requirement, Invariant, Component, Test', 'api': 'POST /designs/decisions', 'rule': 'the design must preserve the stated invariant', 'choice_a': 'explicit model', 'choice_b': 'ad-hoc implementation', 'kind': 'foundation'}

def page(index, label, heading, body):
    return f'<section class="slide" id="s{index}" data-title="{escape(label)}"><div class="eye">{escape(label)}</div><h2>{escape(heading)}</h2>{body}</section>'

def build(title, source):
    safe = escape(title)
    intro = escape(excerpt(source))
    p = profile(title)
    slides = [f'''<section class="slide active" id="s1" data-title="Introduction"><div class="title"><div class="eye">LLD interview simulation | 15 years experience</div><h1>{safe}</h1><p>Conversational, scenario-first architecture walkthrough: define the production problem, show the implementation, then defend it under senior cross-questions.</p><div><span class="tag">Architecture</span><span class="tag">API Design</span><span class="tag">ER Model</span><span class="tag">Sequence</span><span class="tag">Trade-offs</span></div></div></section>''']
    slides.append(page(2, 'Scenario', 'Start with the production situation', f'''<div class="quote">“Let me first make the problem concrete. I would not introduce <strong>{safe}</strong> because it is a textbook name. I use it where the changing behaviour is making the code hard to extend, test, or operate safely.”</div><div class="grid" style="margin-top:12px"><div class="card"><h3>What this source teaches</h3><p>{intro}</p></div><div class="card"><h3>Questions I clarify first</h3><ul><li>What behaviour changes and how often?</li><li>Which business rule must never break?</li><li>What happens when two requests arrive together?</li><li>Which operation must be retry-safe?</li></ul></div></div><div class="why"><strong>Why scenario-first:</strong> requirements and invariants decide the object model. Starting by drawing classes usually produces a diagram without a reason to exist.</div>'''))
    slides.append(page(3, 'Architecture', 'Big picture architecture', '''<div class="diagram">+-------------+      command       +-------------------+
   Caller      -------------------> | API / Controller  |
+-------------+                     +---------+---------+
                                             |
                                             v
                                  +-----------------------+
                                  | Application Service   |
                                  +---+---------------+---+
                                      |               |
                                      v               v
                         +------------------+  +------------------+
                         | Domain Aggregate |  | Repository / DB  |
                         +--------+---------+  +------------------+
                                  |
                                  v
                         +------------------+
                         | Outbox / Event   |
                         +------------------+</div><div class="why"><strong>Why this architecture:</strong> the controller translates transport input, the service coordinates one use case, and the aggregate owns the business invariant. Persistence and side effects stay behind ports.</div>'''))
    slides.append(page(4, 'Class Diagram', 'Object model and responsibility', '''<div class="diagram">+-------------------+       uses       +-------------------+
| ApplicationService|----------------->| Behaviour / Policy |
| + execute(cmd)    |                  | + execute(cmd)     |
+---------+---------+                  +---------+---------+
          |                                      ^
          | loads / saves                         | implements
          v                                      |
+-------------------+                  +---------+---------+
| Aggregate         |                  | Concrete Variant  |
| - id, status      |                  +-------------------+
| - version         |
| + handle(cmd)     |
+-------------------+</div><div class="grid"><div class="card"><h3>Ownership</h3><p>The aggregate guards state transitions. A policy owns the algorithm that varies. The service does orchestration, never the core rule.</p></div><div class="card"><h3>Why composition</h3><p>Several types can reuse one behaviour. Constructor injection makes the choice explicit and allows a unit test to substitute a fake policy.</p></div></div>'''))
    slides.append(page(5, 'API Design', 'API design: accept an intention, not table columns', '''<div class="grid"><div class="api">POST /api/v1/actions
Idempotency-Key: 6bd7...

{
  "action": "EXECUTE",
  "subjectId": "sub_123",
  "parameters": { "mode": "DEFAULT" }
}

201 Created
{ "id": "req_456", "status": "ACCEPTED" }</div><div class="card"><h3>How I speak to this</h3><p>“This endpoint accepts a command. The controller validates shape and authentication, but the domain validates business rules again because an API is not the only caller.”</p><h3 style="margin-top:10px">Why these decisions</h3><ul><li><strong>Idempotency key:</strong> client retries do not duplicate work.</li><li><strong>Resource id:</strong> lets clients poll and support trace failures.</li><li><strong>Stable error code:</strong> clients never parse prose.</li></ul></div></div>'''))
    slides.append(page(6, 'ER Diagram', 'ER relationship diagram and persistence rules', '''<div class="diagram">+--------------------+       1     *    +--------------------+
| AGGREGATE          |------------------| ACTION             |
| id (PK)            |                  | id (PK)            |
| status             |                  | aggregate_id (FK)  |
| version            |                  | type, payload      |
+---------+----------+                  +---------+----------+
          | 1                                      | 1
          |                                        | 
          *                                        *
+---------+----------+                  +---------+----------+
| ACTION_AUDIT        |                  | OUTBOX_EVENT       |
| id, aggregate_id    |                  | id, state, type    |
+--------------------+                  +--------------------+</div><div class="why"><strong>Why version and outbox:</strong> optimistic versioning detects a stale concurrent update. A local transaction writes both state and an outbox record; a publisher safely retries event delivery after crashes.</div>'''))
    slides.append(page(7, 'Sequence Diagram', 'Sequence: a safe command execution', '''<div class="diagram">Caller        API       Service      Aggregate       DB       Publisher
  | command     |           |              |             |            |
  |------------>| validate  |              |             |            |
  |             |---------->| load         |------------>|            |
  |             |           |-------------> apply rule   |            |
  |             |           | save + outbox|------------>|            |
  |<------------| 201/status|              |             |            |
  |             |           |                            |--event---->|
</div><div class="why"><strong>Why this sequence:</strong> respond after the local transaction commits. Publish non-critical side effects asynchronously. Consumers must be idempotent because publishing remains at-least-once.</div>'''))
    slides.append(page(8, 'Implementation', 'Java implementation: make change points explicit', '''<div class="api">public interface Behaviour {
    Result execute(Command command);
}

public final class Aggregate {
    private final Behaviour behaviour;
    public Result handle(Command command) {
        requireValidState(command);
        return behaviour.execute(command);
    }
}

@Transactional
public Result execute(Command command) {
    var model = repository.lockOrLoad(command.id());
    var result = model.handle(command);
    outbox.save(OutcomeEvent.from(result));
    return result;
}</div><div class="trap"><strong>Implementation trap:</strong> a large service `switch` that understands every variant has only moved the coupling. Select a policy in a registry or factory and keep the workflow stable.</div>'''))
    slides.append(page(9, 'Trade-offs', 'Trade-offs: what I choose and what I pay', '''<table><tr><th>Decision</th><th>Why choose it</th><th>Cost and mitigation</th></tr><tr><td>Composition</td><td>Reuse policies across types and isolate change.</td><td>More objects; use clear role names.</td></tr><tr><td>Optimistic locking</td><td>Good throughput without holding a long DB lock.</td><td>Conflict retries; return an explicit 409 response.</td></tr><tr><td>Transactional outbox</td><td>Database change and event record commit together.</td><td>Eventual consistency; monitor event lag.</td></tr><tr><td>Interface boundary</td><td>Testable, independently replaceable behaviour.</td><td>Do not add interfaces without a real variation.</td></tr></table><div class="quote" style="margin-top:10px">“This is not the only possible design. It is the smallest design that keeps the expected policy change separate from the stable business workflow.”</div>'''))
    slides.append(page(10, 'Technology Choices', 'Top technology choices: when A fits and when B fits', '''<div class="grid"><div class="card"><h3>A: Spring Boot + JPA / Hibernate</h3><ul><li><strong>Difference:</strong> object mapping and unit-of-work manage persistence.</li><li><strong>Why pick A:</strong> transactional domain workflows and delivery speed.</li><li><strong>Better than B:</strong> aggregate-heavy systems with evolving models.</li><li><strong>Choose it:</strong> booking or expense-sharing applications.</li><li><strong>Examples:</strong> `@Version` seat reservation; payment audit transaction.</li></ul></div><div class="card"><h3>B: Spring Boot + jOOQ / JDBC</h3><ul><li><strong>Difference:</strong> explicit SQL controls the exact database operation.</li><li><strong>Why pick B:</strong> query shape and batch performance dominate.</li><li><strong>Better than A:</strong> reporting and allocation with complex joins.</li><li><strong>Choose it:</strong> read-heavy analytics or reconciliation.</li><li><strong>Examples:</strong> ranked auction query; million-row ledger export.</li></ul></div></div><div class="grid" style="margin-top:12px"><div class="card"><h3>A: PostgreSQL</h3><p><strong>Choose:</strong> relational integrity and transactions. <strong>Examples:</strong> a booking ledger; inventory allocation. It is the source of truth.</p></div><div class="card"><h3>B: Redis</h3><p><strong>Choose:</strong> TTL, cache, rate limiting, short locks. <strong>Examples:</strong> hot availability cache; OTP throttle. It is not the source of truth.</p></div></div>'''))
    slides.append(page(11, 'Cross Questions', 'Cross questions for every design decision', '''<div class="grid"><div class="card"><h3>Architecture and API</h3><ul><li>Why is this a domain method, not a controller check?</li><li>How does a retry avoid executing twice?</li><li>Which failures retry and which are permanent?</li><li>How will the API evolve without breaking clients?</li></ul></div><div class="card"><h3>Data and concurrency</h3><ul><li>Two callers change the same state. What happens?</li><li>What is committed before an event is published?</li><li>How do you replay an event safely?</li><li>Which index serves the hottest lookup?</li></ul></div></div><div class="why"><strong>Answer pattern:</strong> state the invariant, name the mechanism, then describe the observable outcome. “Only one reservation can own the seat; the version detects the stale write; the loser receives 409 and reloads availability.”</div>'''))
    slides.append(page(12, 'Senior Traps', '15 YOE trap questions with strong model answers', '''<div class="trap"><strong>Trap:</strong> “Does an outbox give exactly-once delivery?”<br><strong>Answer:</strong> “No. It atomically persists state plus an event record. Publisher and consumers are still at-least-once, so I use an event id or idempotent business key in consumers.”</div><div class="trap"><strong>Trap:</strong> “Can the policy be a singleton?”<br><strong>Answer:</strong> “Only when it is stateless and thread-safe. Request state belongs in the command or a scoped object; mutable singleton state introduces races.”</div><div class="trap"><strong>Trap:</strong> “Why not `synchronized` for concurrency?”<br><strong>Answer:</strong> “It protects one JVM, not a fleet. I use database versioning, or a carefully designed distributed lock with expiry and fencing when truly needed.”</div>'''))
    slides.append(page(13, 'Architect Summary', 'Close like an architect', f'''<div class="quote">“For <strong>{safe}</strong>, I begin with the changing policy and the non-negotiable invariant. I keep the invariant inside an aggregate, use composition for variable behaviour, make APIs command-oriented and retry-safe, then protect state plus events using versioning and an outbox. I validate with concurrent-request tests, duplicate-message tests, and metrics for conflicts, retries, and outbox lag.”</div><div class="grid3" style="margin-top:12px"><div class="card"><h3>Before coding</h3><p>Write invariants and transitions.</p></div><div class="card"><h3>While coding</h3><p>Test policies and transactions.</p></div><div class="card"><h3>Before production</h3><p>Inject retries and concurrency.</p></div></div>'''))
    slides[1:12] = [
        page(2, 'Scenario', f'Production scenario: {p["scenario"]}', f'''<div class="quote">“Here is the production conversation I would start with: <strong>{escape(p["scenario"])}</strong>. For {safe}, the non-negotiable rule is: <strong>{escape(p["rule"])}</strong>. That rule, not a pattern name, drives the design.”</div><div class="grid" style="margin-top:12px"><div class="card"><h3>Transcript grounding</h3><p>{intro}</p></div><div class="card"><h3>What I clarify</h3><ul><li>Who owns the state transition?</li><li>What can arrive twice or concurrently?</li><li>Which result must be immediately consistent?</li><li>What can be asynchronous and retried?</li></ul></div></div><div class="why"><strong>Why this scenario:</strong> it exposes the real failure mode before we select classes, a database, or a design pattern.</div>'''),
        page(3, 'Architecture', f'Big picture: {p["aggregate"]} as the decision owner', f'''<div class="diagram">+----------------+    {escape(p["api"]):<25}  +-------------------+
 Client / Caller  --------------------------> | API / Controller  |
+----------------+                             +---------+---------+
                                                     |
                                                     v
                                      +----------------------------+
                                      | {escape(p["aggregate"]):<26} |
                                      | validates and owns rule     |
                                      +-----+------------------+----+
                                            |                  |
                                            v                  v
                         +-------------------------+  +--------------------+
                         | {escape(p["entities"]):<23} |  | DB / Event Store   |
                         +-------------------------+  +--------------------+</div><div class="why"><strong>Why this boundary:</strong> the API translates input; <strong>{escape(p["aggregate"])}</strong> makes the decision; infrastructure records or publishes the result. This prevents UI or vendor details from owning business correctness.</div>'''),
        page(4, 'Object Model', f'LLD model: {p["entities"]}', f'''<div class="diagram">+------------------------+       coordinates      +-----------------------+
    | {escape(p["aggregate"]):<22} |----------------------->| Policy / Collaborator |
| - id, state, version    |                         | + validate / execute  |
| + handle(command)       |                         +-----------+-----------+
+-----------+------------+                                     |
            | owns / references                               | variation
            v                                                  v
+------------------------+                         +-----------------------+
| {escape(p["entities"]):<22} |                         | Concrete behaviour    |
+------------------------+                         +-----------------------+</div><div class="why"><strong>Why these objects:</strong> {escape(p["aggregate"])} owns the invariant; entities model meaningful state; a policy isolates behaviour that will vary. This is the point where I choose composition instead of subclassing when variation is independent.</div>'''),
        page(5, 'API Design', f'API: make {p["aggregate"]} commands retry-safe', f'''<div class="grid"><div class="api">{escape(p["api"])}
Idempotency-Key: client-generated-key

{{
  "action": "EXECUTE",
  "expectedVersion": 7,
  "requestId": "req_456"
}}

201 Created / 409 Conflict
{{ "id": "req_456", "status": "ACCEPTED" }}</div><div class="card"><h3>Architect answer</h3><p>“The endpoint submits intent, not raw database fields. I require an idempotency key for transport retries and an expected version where a stale command would violate <strong>{escape(p["rule"])}</strong>.”</p><h3 style="margin-top:10px">Purpose</h3><ul><li>Idempotency prevents duplicate side effects.</li><li>Version makes write conflicts observable.</li><li>Status resource separates long work from request timeouts.</li></ul></div></div>'''),
        page(6, 'ER Diagram', f'ER model: persist the {p["aggregate"]} invariant', f'''<div class="diagram">+----------------------+       1      *     +----------------------+
    | {escape(p["aggregate"].upper()):<20} |----------------------| ACTION / DETAIL      |
| id (PK), status      |                      | id (PK), type       |
| version              |                      | aggregate_id (FK)   |
+----------+-----------+                      +----------+-----------+
           | 1                                           | 1
           |                                             |
           *                                             *
+----------+-----------+                      +----------+-----------+
| AUDIT_TRAIL          |                      | OUTBOX_EVENT         |
| actor, before, after |                      | event_id, state      |
+----------------------+                      +----------------------+</div><div class="why"><strong>Why this shape:</strong> the root row carries versioned state; child rows retain detail; an audit answers production disputes; the outbox lets state and a follow-up event commit atomically. For this topic, the critical invariant remains: <strong>{escape(p["rule"])}</strong>.</div>'''),
        page(7, 'Sequence Diagram', f'Sequence: enforce {p["rule"]}', f'''<div class="diagram">Caller       API          Service       {escape(p["aggregate"]):<15} DB / Outbox
  | command     |             |                |                |
  |------------>| validate    |                |                |
  |             |------------>| load(version)  |--------------->|
  |             |             |---------------> validate rule   |
  |             |             |                 | update + event|
  |             |             |-------------------------------->|
  |<------------| result / conflict             |                |</div><div class="why"><strong>Why this sequence:</strong> we load state and validate the rule inside the write boundary. A stale version produces a deliberate conflict, not a silent lost update. Events are published from the committed outbox, so a crash cannot leave state and notifications inconsistent.</div>'''),
        page(8, 'Implementation', f'Java implementation: protect {p["aggregate"]}', f'''<div class="api">@Transactional
public Result execute(Command command) {{
    var model = repository.findById(command.id())
        .orElseThrow(NotFound::new);
    model.requireVersion(command.expectedVersion());
    var result = model.handle(command);
    outbox.save(DomainEvent.from(result));
    return result;
}}

public Result handle(Command command) {{
    requireBusinessRule(command); // {escape(p["rule"])}
    return policy.execute(command);
}}</div><div class="trap"><strong>15 YOE implementation trap:</strong> do not rely on a controller check or `synchronized`. A controller can be bypassed and a JVM lock does not protect another service instance. Enforce the invariant in the domain plus a transaction/version constraint.</div>'''),
        page(9, 'Trade-offs', f'Trade-offs specific to {p["aggregate"]}', f'''<table><tr><th>Decision</th><th>Why I choose it here</th><th>Cost and mitigation</th></tr><tr><td>Versioned aggregate</td><td>Detects a stale write against {escape(p["rule"])}</td><td>409/retry path; clients reload fresh state.</td></tr><tr><td>Policy collaboration</td><td>Keeps changing rules out of the aggregate workflow.</td><td>Extra type; only add for real variation.</td></tr><tr><td>Outbox event</td><td>Durably records side effects with the decision.</td><td>Eventual consistency; monitor lag and dedupe consumers.</td></tr><tr><td>Audit trail</td><td>Explains production outcomes and supports reconciliation.</td><td>Storage growth; partition and set retention policy.</td></tr></table><div class="quote" style="margin-top:10px">“The important trade-off is not ‘SQL versus NoSQL’. It is where I pay for correctness: at write time through an invariant, or later through manual production reconciliation.”</div>'''),
        page(10, 'Technology Choices', f'Two technology decisions for {p["aggregate"]}', f'''<div class="grid"><div class="card"><h3>Category 1: Core model - {escape(p["choice_a"])}</h3><ul><li><strong>Why pick A:</strong> it protects <strong>{escape(p["rule"])}</strong> where the decision is made.</li><li><strong>When A wins:</strong> contested or financially meaningful state needs an explainable write path.</li><li><strong>Two examples:</strong> final seat confirmation; wallet or ledger settlement.</li></ul></div><div class="card"><h3>Category 1: Alternative - {escape(p["choice_b"])}</h3><ul><li><strong>Why pick B:</strong> it addresses a separate concern such as latency, integration, or delivery.</li><li><strong>When B wins:</strong> it is bounded away from the durable source of truth.</li><li><strong>Two examples:</strong> cached availability; asynchronous subscriber notification.</li></ul></div></div><div class="grid" style="margin-top:12px"><div class="card"><h3>Category 2: PostgreSQL</h3><ul><li><strong>Difference:</strong> relational constraints, transactions, and durable audit.</li><li><strong>Pick it for:</strong> final state and reconciliation.</li><li><strong>Examples:</strong> unique seat allocation; versioned inventory decrement.</li></ul></div><div class="card"><h3>Category 2: Redis</h3><ul><li><strong>Difference:</strong> in-memory TTL and low latency, not durable relational truth.</li><li><strong>Pick it for:</strong> a bounded cache, hold, lock, or rate limit.</li><li><strong>Examples:</strong> 5-minute seat hold; API retry throttling.</li></ul></div></div><div class="why"><strong>Decision rule:</strong> PostgreSQL records the final answer; Redis accelerates a temporary answer. For {escape(p["aggregate"])}, never let a cache become the only authority for {escape(p["rule"])}.</div>'''),
        page(11, 'Cross Questions', f'Cross questions for {p["aggregate"]}', f'''<div class="grid"><div class="card"><h3>Architecture and API</h3><ul><li>Why does {escape(p["aggregate"])} own this rule instead of the controller?</li><li>What is the idempotency key and how long is it retained?</li><li>Which response is synchronous, and why?</li><li>How does a caller learn that a retry already succeeded?</li></ul></div><div class="card"><h3>Data and failure</h3><ul><li>How does the model preserve: {escape(p["rule"])}?</li><li>What happens on a stale version?</li><li>How do outbox retries avoid duplicate consumption?</li><li>What metric proves the design is healthy in production?</li></ul></div></div><div class="why"><strong>Strong live answer:</strong> “I name the invariant first, then the exact mechanism, then the observable failure behaviour. That makes the decision testable rather than aspirational.”</div>'''),
        page(12, 'Senior Traps', f'15 YOE traps for {p["aggregate"]}', f'''<div class="trap"><strong>Trap:</strong> “The API has an idempotency key. Are duplicate side effects impossible?”<br><strong>Answer:</strong> “No. It deduplicates a command at this boundary. Every asynchronous consumer still needs its own idempotent business key or processed-event record.”</div><div class="trap"><strong>Trap:</strong> “Can Redis alone enforce {escape(p["rule"])}?”<br><strong>Answer:</strong> “Not as the durable source of truth. It can optimize a hold, cache, or rate limit, but final correctness belongs in the transactional write model.”</div><div class="trap"><strong>Trap:</strong> “Why not retry every conflict automatically?”<br><strong>Answer:</strong> “A retry can apply a decision to changed state. I retry only when the command is demonstrably safe; otherwise I surface conflict and let the caller re-evaluate.”</div>'''),
    ]
    slides[12] = page(13, 'Architect Summary', f'Close {safe} like an architect', f'''<div class="quote">“For <strong>{safe}</strong>, I began with <strong>{escape(p["scenario"])}</strong>. The invariant is <strong>{escape(p["rule"])}</strong>. I make <strong>{escape(p["aggregate"])}</strong> the decision owner, keep external concerns behind an interface, and use a versioned transaction plus an outbox when the outcome reaches other systems.”</div><div class="grid3" style="margin-top:12px"><div class="card"><h3>Business</h3><p>Name the invariant and the customer impact.</p></div><div class="card"><h3>Design</h3><p>Show where state and changing policy live.</p></div><div class="card"><h3>Operations</h3><p>Explain retries, conflicts, and observability.</p></div></div>''')
    slides.extend([
        page(14, 'State and Failure', f'Failure handling for {p["aggregate"]}', f'''<div class="diagram">REQUESTED  --->  VALIDATING  --->  ACCEPTED  --->  COMPLETED
    |                  |                 |                 |
    | invalid          | stale / timeout | downstream fail  |
    v                  v                 v                 v
 REJECTED          CONFLICT          PENDING_RETRY      COMPENSATED</div><div class="grid" style="margin-top:12px"><div class="card"><h3>Senior decision</h3><p>“I distinguish a business rejection from a technical retry. A request that breaks <strong>{escape(p["rule"])}</strong> is rejected. A transient provider failure is recorded with enough context for a bounded retry or compensation.”</p></div><div class="card"><h3>Production signals</h3><ul><li>Version-conflict rate and idempotency hits</li><li>Outbox age and failed delivery count</li><li>Invariant violation attempts by action type</li><li>Time spent in pending-retry state</li></ul></div></div><div class="why"><strong>Why model state explicitly:</strong> an enum or state object makes recovery visible. A boolean like `isDone` cannot explain whether work failed, is retrying, or needs compensation.</div>'''),
        page(15, 'Test Strategy', f'How I prove {p["aggregate"]} is safe', f'''<table><tr><th>Test level</th><th>Scenario</th><th>Expected proof</th></tr><tr><td>Unit</td><td>Valid and invalid commands against {escape(p["aggregate"])}</td><td>{escape(p["rule"])}</td></tr><tr><td>Concurrency</td><td>Two commands use the same expected version</td><td>One commits; one receives conflict; no lost update.</td></tr><tr><td>Integration</td><td>Transaction commits while publisher is unavailable</td><td>State and outbox record survive; event later publishes.</td></tr><tr><td>Contract</td><td>Client repeats identical idempotency key</td><td>Same response or resource, never a duplicate effect.</td></tr></table><div class="why"><strong>Why this test stack:</strong> a unit test proves rules, but it cannot prove database isolation or crash recovery. I need all four levels before calling this production-ready.</div>'''),
        page(16, 'Live Interview Script', f'How I would answer {safe} live', f'''<div class="quote">“I will start with the invariant: <strong>{escape(p["rule"])}</strong>. The failure that makes it interesting is <strong>{escape(p["scenario"])}</strong>. I model that decision in <strong>{escape(p["aggregate"])}</strong>, with <strong>{escape(p["entities"])}</strong> as the relevant collaborators. The API carries an idempotency key and expected version. On conflict I do not silently retry a changed business decision. I persist the accepted result and outbox event together, then make consumers idempotent. Finally, I test concurrent commands and publish outage recovery.”</div><div class="trap"><strong>Follow-up trap:</strong> “What would make you simplify this?”<br><strong>Strong answer:</strong> “For a single-process, low-value workflow I may remove the outbox and use a synchronous side effect. I would keep the invariant and tests, and I would document exactly which failure recovery guarantee I am giving up.”</div>'''),
    ])
    js = '''<script>const s=[...document.querySelectorAll('.slide')],d=document.querySelector('.dots'),c=document.querySelector('.counter'),b=document.querySelector('#progress i');let n=Math.max(0,+new URLSearchParams(location.search).get('slide')-1||0);s.forEach((_,i)=>{const x=document.createElement('button');x.className='dot';x.onclick=()=>show(i);d.append(x)});function show(i){n=Math.max(0,Math.min(i,s.length-1));s.forEach((x,j)=>x.classList.toggle('active',j===n));[...d.children].forEach((x,j)=>x.classList.toggle('active',j===n));c.textContent=`${n+1} / ${s.length}`;b.style.width=`${(n+1)*100/s.length}%`;history.replaceState(null,'','?slide='+(n+1))}document.querySelector('#prev').onclick=()=>show(n-1);document.querySelector('#next').onclick=()=>show(n+1);document.addEventListener('keydown',e=>{if(e.key==='ArrowRight'||e.key===' ')show(n+1);if(e.key==='ArrowLeft')show(n-1)});show(n)</script>'''
    return f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{safe} | LLD Interview</title>{CSS}</head><body><main id="p"><header><span class="name">{safe}</span><span class="counter"></span></header><div id="progress"><i></i></div><div class="stage">{"".join(slides)}</div><footer><button class="btn" id="prev">Previous</button><div class="dots"></div><button class="btn" id="next">Next</button></footer></main>{js}</body></html>'

def main():
    transcripts = sorted(ROOT.rglob('transcript.md'))
    for transcript in transcripts:
        source = transcript.read_text(encoding='utf-8')
        (transcript.parent / 'video.html').write_text(build(title_for(source, transcript.parent.name), source), encoding='utf-8')
    print(f'Generated {len(transcripts)} video decks.')

if __name__ == '__main__':
    main()