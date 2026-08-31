#!/usr/bin/env python3
"""
Generate comprehensive interview guides for all LLD systems
Following the BookMyShow template structure
"""

import os
import re
from pathlib import Path

# Folder configurations with key metadata
SYSTEMS = {
    "21_17_LLD_of_ATM_ATM_Low_Level_System_Design_Design_an_ATM_Low_Level_Design_Interview_question": {
        "title": "ATM System",
        "icon": "🏧",
        "patterns": ["State Design Pattern", "Chain of Responsibility"],
        "key_concepts": ["State Management", "Cash Dispensing", "Transaction Processing"],
        "core_objects": ["ATM", "Card", "BankAccount", "ATMState", "CashWithdrawalProcessor"],
    },
    "11_8_Elevator_System_Low_Level_Design_Hindi_SDE_LLD_interview_question_Design_Elevator_System": {
        "title": "Elevator System",
        "icon": "🛗",
        "patterns": ["Strategy Pattern", "State Pattern"],
        "key_concepts": ["LOOK Algorithm", "Request Dispatching", "Direction Management"],
        "core_objects": ["Building", "Floor", "Elevator", "ElevatorController", "ExternalButton", "InternalButton"],
    },
    "20_16_Design_Vending_Machine_Hindi_LLD_of_Vending_Machine_State_Design_Pattern_LLD_question": {
        "title": "Vending Machine",
        "icon": "🍫",
        "patterns": ["State Design Pattern"],
        "key_concepts": ["State Transitions", "Product Dispensing", "Payment Handling"],
        "core_objects": ["VendingMachine", "State", "IdleState", "HasMoneyState", "SelectionState", "Inventory"],
    },
    "25_21_LLD_of_Splitwise_Low_Level_Design_of_Splitwise_Design_Expense_Sharing_App_like_Splitwise": {
        "title": "Splitwise",
        "icon": "💰",
        "patterns": ["Strategy Pattern", "Observer Pattern"],
        "key_concepts": ["Expense Splitting", "Balance Calculation", "Debt Simplification"],
        "core_objects": ["User", "Group", "Expense", "Split", "ExpenseSplitStrategy", "BalanceSheet"],
    },
    "28_24_LLD_of_CricbuzzCricInfo_Cricbuzz_Low_Level_System_Design_Design_Cricbuzz_Low_Level_Design": {
        "title": "Cricbuzz",
        "icon": "🏏",
        "patterns": ["Observer Pattern", "Composite Pattern"],
        "key_concepts": ["Live Score Updates", "Match Management", "Team Composition"],
        "core_objects": ["Match", "Team", "Player", "Over", "Ball", "ScoreCard", "Commentary"],
    },
    "10_7_Design_Tic_Tac_Toe_game_Hindi_Tic-Tac-Toe_LLD_Java_Low_Level_Design_System_Design": {
        "title": "Tic Tac Toe",
        "icon": "⭕",
        "patterns": ["Strategy Pattern"],
        "key_concepts": ["Game State", "Win Detection", "Player Turns"],
        "core_objects": ["Board", "Player", "Game", "WinningStrategy"],
    },
    "12_9_LLD_of_Car_Rental_System_Hindi_ZoomCar_Low_Level_Design_System_Design_Interview_Question": {
        "title": "Car Rental System",
        "icon": "🚗",
        "patterns": ["Factory Pattern", "Strategy Pattern"],
        "key_concepts": ["Reservation Management", "Pricing Strategy", "Vehicle Inventory"],
        "core_objects": ["Vehicle", "User", "Reservation", "Location", "Payment", "PricingStrategy"],
    },
    "13_10_Design_Logging_System_Hindi_Chain_of_Responsibility_Design_Pattern_System_Design_interview": {
        "title": "Logging System",
        "icon": "📝",
        "patterns": ["Chain of Responsibility"],
        "key_concepts": ["Log Levels", "Log Processors", "Request Chaining"],
        "core_objects": ["Logger", "LogProcessor", "InfoLogProcessor", "DebugLogProcessor", "ErrorLogProcessor"],
    },
    "14_11_LLD_of_Snake_and_Ladder_game_Hindi_SDE_system_design_interview_question_Java_implementation": {
        "title": "Snake and Ladder",
        "icon": "🐍",
        "patterns": ["Strategy Pattern"],
        "key_concepts": ["Board Design", "Player Movement", "Jump Logic"],
        "core_objects": ["Board", "Player", "Snake", "Ladder", "Dice", "Game"],
    },
    "22_18_Design_CHESS_GAME_LLD_Mock_Interview_Low_Level_Design_Coding_Interview_Question": {
        "title": "Chess Game",
        "icon": "♟️",
        "patterns": ["Strategy Pattern", "Command Pattern"],
        "key_concepts": ["Piece Movement", "Move Validation", "Game State"],
        "core_objects": ["Board", "Piece", "Player", "Move", "Game", "MoveValidator"],
    },
    "23_19_Design_File_System_using_Composite_Design_Pattern_Low_Level_Design_Interview_Question_LLD": {
        "title": "File System",
        "icon": "📁",
        "patterns": ["Composite Design Pattern"],
        "key_concepts": ["Tree Structure", "File/Directory Operations", "Hierarchical Organization"],
        "core_objects": ["FileSystem", "File", "Directory", "FileSystemNode"],
    },
    "33_29_LLD_of_Inventory_Management_System_Low_Level_System_Design_of_Inventory_Management_System": {
        "title": "Inventory Management",
        "icon": "📦",
        "patterns": ["Observer Pattern", "Strategy Pattern"],
        "key_concepts": ["Stock Management", "Order Processing", "Warehouse Operations"],
        "core_objects": ["Product", "Warehouse", "Order", "Inventory", "Stock"],
    },
    "34_30_Design_Word_Processor_using_Flyweight_Design_Pattern_Low_Level_System_Design_FlyWeight_Pattern": {
        "title": "Word Processor",
        "icon": "📄",
        "patterns": ["Flyweight Design Pattern"],
        "key_concepts": ["Memory Optimization", "Character Rendering", "Formatting"],
        "core_objects": ["Document", "Character", "CharacterStyle", "FlyweightFactory"],
    },
    "35_31_Design_Undo_Redo_feature_with_Command_Pattern_Command_Design_Pattern_Low_Level_System_Design": {
        "title": "Undo/Redo Feature",
        "icon": "↩️",
        "patterns": ["Command Design Pattern"],
        "key_concepts": ["Command Execution", "History Management", "State Restoration"],
        "core_objects": ["Command", "CommandInvoker", "CommandHistory", "Receiver"],
    },
    "38_34_Design_Online_Auction_System_with_Mediator_Design_Pattern_Low_Level_System_Design": {
        "title": "Online Auction System",
        "icon": "🔨",
        "patterns": ["Mediator Design Pattern", "Observer Pattern"],
        "key_concepts": ["Bid Management", "Auction Lifecycle", "Bidder Communication"],
        "core_objects": ["Auction", "Bidder", "Bid", "AuctionMediator", "Item"],
    },
    "39_35_LLD_Apply_Coupons_on_Shopping_Cart_products_Low_level_design": {
        "title": "Shopping Cart Coupons",
        "icon": "🛒",
        "patterns": ["Strategy Pattern", "Decorator Pattern"],
        "key_concepts": ["Coupon Types", "Discount Calculation", "Validation Rules"],
        "core_objects": ["Cart", "Product", "Coupon", "DiscountStrategy"],
    },
    "46_42_LLD_of_Payment_Gateway_Low_Level_Design_of_Payments_App": {
        "title": "Payment Gateway",
        "icon": "💳",
        "patterns": ["Strategy Pattern", "Factory Pattern"],
        "key_concepts": ["Payment Processing", "Multiple Payment Methods", "Transaction Management"],
        "core_objects": ["Payment", "PaymentMethod", "Transaction", "PaymentGateway"],
    },
    # Design Patterns (shorter guides)
    "16_13_Proxy_Design_Pattern_Explanation_Hindi_LLD_System_Design_Interview_Question_Java": {
        "title": "Proxy Design Pattern",
        "icon": "🔐",
        "patterns": ["Proxy Pattern"],
        "key_concepts": ["Access Control", "Lazy Initialization", "Remote Proxy"],
        "core_objects": ["Subject", "RealSubject", "Proxy"],
    },
    "19_15_LLD_of_NULL_Object_Pattern_Hindi_Design_Null_Object_Pattern_Design_Patterns": {
        "title": "Null Object Pattern",
        "icon": "⭕",
        "patterns": ["Null Object Pattern"],
        "key_concepts": ["Null Handling", "Default Behavior", "Polymorphism"],
        "core_objects": ["AbstractObject", "RealObject", "NullObject"],
    },
    "24_20_Adapter_Design_Pattern_with_Examples_LLD_Low_Level_Design_Interview_Question_System_Design": {
        "title": "Adapter Design Pattern",
        "icon": "🔌",
        "patterns": ["Adapter Pattern"],
        "key_concepts": ["Interface Compatibility", "Wrapper Pattern", "Legacy Integration"],
        "core_objects": ["Target", "Adapter", "Adaptee"],
    },
    "27_23_Builder_Design_Pattern_with_Examples_LLD_Low_Level_Design_Interview_Question_System_Design": {
        "title": "Builder Design Pattern",
        "icon": "🏗️",
        "patterns": ["Builder Pattern"],
        "key_concepts": ["Step-by-Step Construction", "Immutability", "Method Chaining"],
        "core_objects": ["Product", "Builder", "Director"],
    },
    "29_25_Facade_Design_Pattern_with_Example_Facade_Low_Level_Design_Pattern_Facade_Pattern_LLD_Java": {
        "title": "Facade Design Pattern",
        "icon": "🏛️",
        "patterns": ["Facade Pattern"],
        "key_concepts": ["Simplified Interface", "Subsystem Hiding", "Unified API"],
        "core_objects": ["Facade", "Subsystem1", "Subsystem2"],
    },
    "30_26_Bridge_Design_Pattern_LLD_of_Bridge_Pattern_with_Example_Low_Level_Design_of_Bridge_Pattern": {
        "title": "Bridge Design Pattern",
        "icon": "🌉",
        "patterns": ["Bridge Pattern"],
        "key_concepts": ["Abstraction vs Implementation", "Decoupling", "Multiple Dimensions"],
        "core_objects": ["Abstraction", "Implementation", "ConcreteImplementation"],
    },
    "37_33_Iterator_Design_Pattern_Explained_with_Example_Low_Level_Design": {
        "title": "Iterator Design Pattern",
        "icon": "➡️",
        "patterns": ["Iterator Pattern"],
        "key_concepts": ["Sequential Access", "Collection Traversal", "Encapsulation"],
        "core_objects": ["Iterator", "ConcreteIterator", "Aggregate"],
    },
    "40_36_Visitor_Design_Pattern_Double_Dispatch_Low_Level_Design": {
        "title": "Visitor Design Pattern",
        "icon": "👤",
        "patterns": ["Visitor Pattern"],
        "key_concepts": ["Double Dispatch", "Operation Separation", "Open/Closed Principle"],
        "core_objects": ["Visitor", "ConcreteVisitor", "Element"],
    },
    "42_38_Memento_Design_Pattern_explanation_LLD_System_Design_Design_pattern_explanation_in_Java": {
        "title": "Memento Design Pattern",
        "icon": "💾",
        "patterns": ["Memento Pattern"],
        "key_concepts": ["State Preservation", "Undo Capability", "Encapsulation"],
        "core_objects": ["Memento", "Originator", "Caretaker"],
    },
}


def generate_guide_header(system_name, metadata):
    """Generate the guide header with table of contents"""
    return f"""# {metadata['icon']} {metadata['title']} - Low Level Design Interview Guide
## _15 YOE Architect-Level Conversational Script_

---

## 📋 **Table of Contents**
1. [Architecture Diagram](#1-architecture-diagram)
2. [API Design](#2-api-design)
3. [ER Diagram & Database Design](#3-er-diagram--database-design)
4. [Sequence Diagrams](#4-sequence-diagrams)
5. [Scenario-First Explanations](#5-scenario-first-explanations)
6. [Cross Questions](#6-cross-questions)
7. [Trade-offs](#7-trade-offs)
8. [Senior Trap Questions](#8-senior-trap-questions)
9. [Technology Choices](#9-technology-choices)

---

## **Design Patterns Used**: {', '.join(metadata['patterns'])}

**Interviewer**: "Design {metadata['title']}."

**You**: "Great question! Let me start by understanding the requirements and identifying the key components..."

"""


def main():
    base_path = Path("/Users/I771246/Abhi Personal/JavaFullstackNotes/LLD by Shrayansh")
    
    print("🚀 Generating Interview Guides for All Systems...")
    print(f"📊 Total systems to process: {len(SYSTEMS)}\n")
    
    for folder_name, metadata in SYSTEMS.items():
        folder_path = base_path / folder_name
        guide_path = folder_path / "INTERVIEW_GUIDE.md"
        
        # Skip if already exists
        if guide_path.exists():
            print(f"✅ {metadata['title']} - Already exists, skipping")
            continue
        
        print(f"📝 Creating guide for: {metadata['title']}")
        
        # Generate guide content
        content = generate_guide_header(folder_name, metadata)
        content += "\n\n_(Note: This is a template. Complete the sections based on transcript analysis)_\n"
        
        # Write the file
        with open(guide_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"   ✓ Created: {guide_path.name}")
    
    print(f"\n✨ Done! Check the folders for INTERVIEW_GUIDE.md files")


if __name__ == "__main__":
    main()
