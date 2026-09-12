# 🗂️ Interview Guide Index — Start Here

This repo contains one `transcript.md` (raw lecture transcript, untouched) and one `INTERVIEW_GUIDE.md` (scenario-based, architect-to-new-developer rewrite with ASCII diagrams and a real production-issue example) per topic.

**New to this repo?** Read in this order — each guide references what came before it, exactly like the [LLD & HLD Roadmap guide](01_Ultimate_LLD_and_HLD_Roadmap_System_Design_RoadMap_LLD_HLD_Topics_to_be_covered_for_Interview/INTERVIEW_GUIDE.md) recommends:

```
1. Fundamentals  →  2. Individual Patterns  →  3. Pattern Round-ups  →  4. Applied System-Design Questions
```

Unfamiliar acronym? Check the [Glossary](GLOSSARY.md).

Difficulty legend: 📗 Beginner · 📘 Intermediate · 📕 Advanced

---

## 1. Fundamentals (read first)

| Guide | Difficulty |
|---|---|
| [LLD & HLD Interview Roadmap](01_Ultimate_LLD_and_HLD_Roadmap_System_Design_RoadMap_LLD_HLD_Topics_to_be_covered_for_Interview/INTERVIEW_GUIDE.md) | 📗 |
| [What is LLD](02_What_is_LLD_Low_Level_Design/INTERVIEW_GUIDE.md) | 📗 |
| [SOLID Principles](03_1_SOLID_Principles_with_Easy_Examples_Hindi_OOPs_SOLID_Principles_-_Low_Level_Design/INTERVIEW_GUIDE.md) | 📗 |
| [Liskov Substitution Principle (LSP) deep-dive](04_11_Liskov_Substitution_Principle_LSP_with_Solution_in_Java_-_SOLID_Principles_of_Low_Level_Design/INTERVIEW_GUIDE.md) | 📗 |

## 2. Individual Design Patterns

### Creational
| Guide | Difficulty |
|---|---|
| [Builder Pattern](27_23_Builder_Design_Pattern_with_Examples_LLD_Low_Level_Design_Interview_Question_System_Design/INTERVIEW_GUIDE.md) | 📗 |
| [Factory vs Abstract Factory](08_5_Factory_Pattern_Vs_Abstract_Factory_Pattern_Explanation_Hindi_Low_Level_System_Design/INTERVIEW_GUIDE.md) | 📗 |
| [Object Pool Pattern](49_43_LLD_Object_Pool_Design_Pattern_Creational_Design_Pattern_Low_Level_Design/INTERVIEW_GUIDE.md) | 📗 |
| [All Creational Patterns (Prototype, Singleton, Factory, Abstract Factory, Builder — rapid revision)](31_27_All_Creational_Design_Patterns_Prototype_Singleton_Factory_AbstractFactory_Builder_Pattern/INTERVIEW_GUIDE.md) | 📘 |

### Structural
| Guide | Difficulty |
|---|---|
| [Decorator Pattern](07_4_Decorator_Design_Pattern_Explanation_with_Java_Coding_Hindi_LLD_System_Design/INTERVIEW_GUIDE.md) | 📗 |
| [Proxy Pattern](16_13_Proxy_Design_Pattern_Explanation_Hindi_LLD_System_Design_Interview_Question_Java/INTERVIEW_GUIDE.md) | 📗 |
| [Adapter Pattern](24_20_Adapter_Design_Pattern_with_Examples_LLD_Low_Level_Design_Interview_Question_System_Design/INTERVIEW_GUIDE.md) | 📗 |
| [Facade Pattern](29_25_Facade_Design_Pattern_with_Example_Facade_Low_Level_Design_Pattern_Facade_Pattern_LLD_Java/INTERVIEW_GUIDE.md) | 📗 |
| [Bridge Pattern](30_26_Bridge_Design_Pattern_LLD_of_Bridge_Pattern_with_Example_Low_Level_Design_of_Bridge_Pattern/INTERVIEW_GUIDE.md) | 📗 |
| [Composite Pattern (via File System question)](23_19_Design_File_System_using_Composite_Design_Pattern_Low_Level_Design_Interview_Question_LLD/INTERVIEW_GUIDE.md) | 📘 |
| [Flyweight Pattern (via Word Processor question)](34_30_Design_Word_Processor_using_Flyweight_Design_Pattern_Low_Level_System_Design_FlyWeight_Pattern/INTERVIEW_GUIDE.md) | 📘 |
| [All Structural Patterns (rapid revision)](36_32_All_Structural_Design_Patterns_Decorator_Proxy_Composite_Adapter_Bridge_Facade_FlyWeight/INTERVIEW_GUIDE.md) | 📘 |

### Behavioral
| Guide | Difficulty |
|---|---|
| [Strategy Pattern](05_2_Strategy_Design_Pattern_explanation_Hindi_LLD_System_Design_Design_pattern_in_Java/INTERVIEW_GUIDE.md) | 📗 |
| [Observer Pattern](06_3_Observer_Design_Pattern_Explanation_Hindi_Design_Interview_Question_LLD_System_Design/INTERVIEW_GUIDE.md) | 📗 |
| [Null Object Pattern](19_15_LLD_of_NULL_Object_Pattern_Hindi_Design_Null_Object_Pattern_Design_Patterns/INTERVIEW_GUIDE.md) | 📗 |
| [Iterator Pattern](37_33_Iterator_Design_Pattern_Explained_with_Example_Low_Level_Design/INTERVIEW_GUIDE.md) | 📗 |
| [Visitor Pattern / Double Dispatch](40_36_Visitor_Design_Pattern_Double_Dispatch_Low_Level_Design/INTERVIEW_GUIDE.md) | 📗 |
| [Memento Pattern](42_38_Memento_Design_Pattern_explanation_LLD_System_Design_Design_pattern_explanation_in_Java/INTERVIEW_GUIDE.md) | 📗 |
| [Template Method Pattern](43_39_Template_Method_Design_Pattern_Explanation_in_Java_Concept_and_Coding_LLD_Low_Level_Design/INTERVIEW_GUIDE.md) | 📗 |
| [Interpreter Pattern](44_40_Interpreter_Design_Pattern_LLD_System_Design_Design_pattern_explanation_in_Java/INTERVIEW_GUIDE.md) | 📗 |
| [Chain of Responsibility (via Logging System question)](13_10_Design_Logging_System_Hindi_Chain_of_Responsibility_Design_Pattern_System_Design_interview/INTERVIEW_GUIDE.md) | 📘 |
| [Command Pattern (via Undo/Redo question)](35_31_Design_Undo_Redo_feature_with_Command_Pattern_Command_Design_Pattern_Low_Level_System_Design/INTERVIEW_GUIDE.md) | 📘 |
| [Mediator Pattern (via Online Auction question)](38_34_Design_Online_Auction_System_with_Mediator_Design_Pattern_Low_Level_System_Design/INTERVIEW_GUIDE.md) | 📘 |
| [All Behavioral Patterns (rapid revision, all 11)](45_41_All_Behavioral_Design_Patterns_Strategy_Observer_State_Template_Command_Visitor_Memento/INTERVIEW_GUIDE.md) | 📘 |

### Architectural Style
| Guide | Difficulty |
|---|---|
| [MVC Pattern](41_37_MVC_Design_Pattern_MVC_Architecture_Overview_Low_Level_System_Design/INTERVIEW_GUIDE.md) | 📗 |

## 3. Applied System-Design Questions (combine multiple patterns)

| Guide | Primary Pattern(s) | Difficulty |
|---|---|---|
| [Tic-Tac-Toe](10_7_Design_Tic_Tac_Toe_game_Hindi_Tic-Tac-Toe_LLD_Java_Low_Level_Design_System_Design/INTERVIEW_GUIDE.md) | Strategy | 📘 |
| [Snake and Ladder](14_11_LLD_of_Snake_and_Ladder_game_Hindi_SDE_system_design_interview_question_Java_implementation/INTERVIEW_GUIDE.md) | Strategy | 📘 |
| [Vending Machine](20_16_Design_Vending_Machine_Hindi_LLD_of_Vending_Machine_State_Design_Pattern_LLD_question/INTERVIEW_GUIDE.md) | State | 📘 |
| [Chess Game](22_18_Design_CHESS_GAME_LLD_Mock_Interview_Low_Level_Design_Coding_Interview_Question/INTERVIEW_GUIDE.md) | Strategy, Command | 📘 |
| [Car Rental System](12_9_LLD_of_Car_Rental_System_Hindi_ZoomCar_Low_Level_Design_System_Design_Interview_Question/INTERVIEW_GUIDE.md) | Factory, Strategy | 📘 |
| [Shopping Cart Coupons](39_35_LLD_Apply_Coupons_on_Shopping_Cart_products_Low_level_design/INTERVIEW_GUIDE.md) | Strategy, Chain of Responsibility | 📘 |
| [Elevator System](11_8_Elevator_System_Low_Level_Design_Hindi_SDE_LLD_interview_question_Design_Elevator_System/INTERVIEW_GUIDE.md) | Strategy, State | 📕 |
| [BookMyShow](17_14_LLD_of_BookMyShow_Hindi_Design_MovieTicketBooking_Low_Level_System_Design_Concurrency/INTERVIEW_GUIDE.md) | Multiple + heavy concurrency | 📕 |
| [ATM System](21_17_LLD_of_ATM_ATM_Low_Level_System_Design_Design_an_ATM_Low_Level_Design_Interview_question/INTERVIEW_GUIDE.md) | State, Chain of Responsibility | 📕 |
| [Splitwise](25_21_LLD_of_Splitwise_Low_Level_Design_of_Splitwise_Design_Expense_Sharing_App_like_Splitwise/INTERVIEW_GUIDE.md) | Strategy, Observer | 📕 |
| [Cricbuzz/CricInfo](28_24_LLD_of_CricbuzzCricInfo_Cricbuzz_Low_Level_System_Design_Design_Cricbuzz_Low_Level_Design/INTERVIEW_GUIDE.md) | Observer, Composite | 📕 |
| [Inventory Management System](33_29_LLD_of_Inventory_Management_System_Low_Level_System_Design_of_Inventory_Management_System/INTERVIEW_GUIDE.md) | Observer, Strategy | 📕 |
| [Payment Gateway](46_42_LLD_of_Payment_Gateway_Low_Level_Design_of_Payments_App/INTERVIEW_GUIDE.md) | Strategy, Factory, Adapter | 📕 |

---

## How each guide is structured

Every `INTERVIEW_GUIDE.md` follows the same shape so you always know what to expect:

1. **Difficulty tag** — so you know if you're ready for it.
2. **Interviewer/You dialogue opener** — frames the problem as a live interview conversation.
3. **ASCII architecture diagram(s)** — visual before code.
4. **Code walkthrough** — minimal Java, annotated.
5. **Scenario-first explanation / Cross questions / Trade-offs / Senior trap questions** — the "why", not just the "what".
6. **🔥 Real-World Production Issue** — a realistic incident caused by getting this pattern wrong in production, its root cause, the fix, and a one-line lesson. Starts with a *"In plain English: ..."* summary so you get the takeaway even before the full story.
7. **🎓 Final Tips** — the 3-5 bullet points to remember right before you walk into the interview.

`transcript.md` files are the original raw lecture transcripts and are left untouched — they're there if you want to go back to the original source material.
