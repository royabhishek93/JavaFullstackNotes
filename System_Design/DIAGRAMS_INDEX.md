# System Design Diagrams Index

**54 editable draw.io diagrams** created for priority system designs.

## 📂 How to Access

Each design folder now has a `diagrams/` subfolder with architecture diagrams:

```
System_Design/
  ├── 09_YouTube_System_Design/diagrams/
  ├── 11_News_Feed_Instagram_SystemDesign/diagrams/
  ├── 18_GoogleDocs_System_Design/diagrams/
  ├── 19_UPI_Payment_System/diagrams/
  └── ... (12 total)
```

## 🎨 How to Open Diagrams

1. **Online**: [diagrams.net](https://app.diagrams.net) → File → Open → select `.drawio` file
2. **VS Code**: Install "Draw.io Integration" extension → click any `.drawio` file  
3. **Desktop**: Download [draw.io app](https://github.com/jgraph/drawio-desktop/releases)

## 📋 Available Systems (Priority Batch)

### Platform/HLD Systems (5 diagrams each)

| System | Location | Diagrams |
|--------|----------|----------|
| **TinyURL** | [system_design_interviewwithbunny/01_Tiny_URL_Design/diagrams/](system_design_interviewwithbunny/01_Tiny_URL_Design/diagrams/) | Context, Components, Sequence, Data Model, Scale/Failures |
| **BookMyShow** | [system_design_interviewwithbunny/11_Ticket_Booking_System_like_BookMyShow/diagrams/](system_design_interviewwithbunny/11_Ticket_Booking_System_like_BookMyShow/diagrams/) | Context, Components, Sequence, Data Model, Scale/Failures |
| **UPI Payment** | [19_UPI_Payment_System/diagrams/](19_UPI_Payment_System/diagrams/) | Context, Components, Sequence, Data Model, Scale/Failures |
| **Google Docs** | [18_GoogleDocs_System_Design/diagrams/](18_GoogleDocs_System_Design/diagrams/) | Context, Components, Sequence, Data Model, Scale/Failures |
| **YouTube** | [09_YouTube_System_Design/diagrams/](09_YouTube_System_Design/diagrams/) | Context, Components, Sequence, Data Model, Scale/Failures |
| **Instagram News Feed** | [11_News_Feed_Instagram_SystemDesign/diagrams/](11_News_Feed_Instagram_SystemDesign/diagrams/) | Context, Components, Sequence, Data Model, Scale/Failures |
| **Search Engine** | [23_design_search_engine/diagrams/](23_design_search_engine/diagrams/) | Context, Components, Sequence, Data Model, Scale/Failures |
| **Rate Limiter** | [system_design_interviewwithbunny/02_Distributed_Rate_Limiter_Token_Bucket_Leaky_Bucket_Sliding_Window_HLD_LLD/diagrams/](system_design_interviewwithbunny/02_Distributed_Rate_Limiter_Token_Bucket_Leaky_Bucket_Sliding_Window_HLD_LLD/diagrams/) | Context, Components, Sequence, Data Model, Scale/Failures |
| **Multitenant SaaS** | [Multitenancy_SAAS_System_Design/diagrams/](Multitenancy_SAAS_System_Design/diagrams/) | Context, Components, Sequence, Data Model, Scale/Failures |

### LLD Systems (3 diagrams each)

| System | Location | Diagrams |
|--------|----------|----------|
| **Parking Lot** | [25_Parking_Lot_System/LLD/diagrams/](25_Parking_Lot_System/LLD/diagrams/) | Sequence, Class UML, State Machine |
| **Elevator System** | [26_Elevator_System/LLD/diagrams/](26_Elevator_System/LLD/diagrams/) | Sequence, Class UML, State Machine |
| **Airline Management** | [27_Airline_Management_System/LLD/diagrams/](27_Airline_Management_System/LLD/diagrams/) | Sequence, Class UML, State Machine |

## 📊 Diagram Types Explained

### For HLD (Platform Systems)

1. **01-context.drawio**: System boundary, actors, external systems
2. **02-hld-components.drawio**: Services, databases, queues, caches, connections
3. **03-primary-sequence.drawio**: Step-by-step user request flow
4. **04-data-model.drawio**: Database entities, relationships, key fields
5. **05-scale-failures.drawio**: Replicas, failover, retries, circuit breakers

### For LLD (Object-Oriented Systems)

1. **03-primary-sequence.drawio**: Step-by-step workflow
2. **06-class-uml.drawio**: Classes, methods, inheritance, composition
3. **07-state-machine.drawio**: State transitions, lifecycle, events

## ✏️ Customization Tips

- All diagrams are **fully editable** - modify for your interview prep
- Export to PNG/SVG: File → Export as... (for presentations/notes)
- Use as templates for other system designs
- Add your own notes/annotations directly in the diagrams

## 🎯 Interview Usage

1. **Study**: Open diagrams in draw.io to understand architecture visually
2. **Practice**: Explain each diagram out loud as if in an interview
3. **Customize**: Add your own improvements/trade-offs to the designs
4. **Export**: Create PNG snapshots to include in your portfolio

---

**Need more systems?** Let me know which designs from the remaining 100+ topics need diagrams next!
