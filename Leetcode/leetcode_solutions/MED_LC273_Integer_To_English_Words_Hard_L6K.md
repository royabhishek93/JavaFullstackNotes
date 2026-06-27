# LC 273: Integer to English Words

**Link**: [leetcode.com/problems/integer-to-english-words](https://leetcode.com/problems/integer-to-english-words/)

## Problem
Convert a non-negative integer `num` to its English words representation.

**Example 1:**
```
Input: num = 123
Output: "One Hundred Twenty Three"
```

**Example 2:**
```
Input: num = 12345
Output: "Twelve Thousand Three Hundred Forty Five"
```

**Example 3:**
```
Input: num = 1234567
Output: "One Million Two Hundred Thirty Four Thousand Five Hundred Sixty Seven"
```

**Constraints:**
- 0 <= num <= 2^31 - 1

## Visual Explanation with ASCII Diagrams

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    INTEGER TO ENGLISH WORDS                      │
│                                                                   │
│  Input: 1,234,567,890                                            │
│                                                                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐│
│  │  Billions  │  │  Millions  │  │ Thousands  │  │    Ones    ││
│  │            │  │            │  │            │  │            ││
│  │     1      │  │    234     │  │    567     │  │    890     ││
│  │            │  │            │  │            │  │            ││
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘│
│        │               │               │               │        │
│        ▼               ▼               ▼               ▼        │
│   ┌─────────┐    ┌──────────┐   ┌──────────┐   ┌──────────┐   │
│   │  "One"  │    │  "Two    │   │  "Five   │   │  "Eight  │   │
│   │ "Billion"│   │ Hundred  │   │ Hundred  │   │ Hundred  │   │
│   │         │    │ Thirty   │   │ Sixty    │   │ Ninety"  │   │
│   │         │    │ Four"    │   │ Seven"   │   │          │   │
│   │         │    │"Million" │   │"Thousand"│   │          │   │
│   └────┬────┘    └────┬─────┘   └────┬─────┘   └────┬─────┘   │
│        │              │              │              │           │
│        └──────────────┴──────────────┴──────────────┘           │
│                            │                                     │
│                            ▼                                     │
│  Output: "One Billion Two Hundred Thirty Four Million           │
│           Five Hundred Sixty Seven Thousand Eight Hundred Ninety"│
└─────────────────────────────────────────────────────────────────┘
```

### Step-by-Step Visualization (Example: 1,234,567)

```
STEP 1: Split into Groups of 3 Digits (Right to Left)
════════════════════════════════════════════════════════

   1,234,567
   │  │   │
   │  │   └─── Group 0: 567 (Ones)
   │  └─────── Group 1: 234 (Thousands)
   └────────── Group 2: 001 (Millions)

┌──────────────────────────────────────────────────────┐
│ Group Index │  Value  │  Scale Word  │  Process?    │
├─────────────┼─────────┼──────────────┼──────────────┤
│      0      │   567   │      ""      │     ✓        │
│      1      │   234   │  "Thousand"  │     ✓        │
│      2      │   001   │  "Million"   │     ✓        │
│      3      │   000   │  "Billion"   │     ✗ (skip) │
└──────────────────────────────────────────────────────┘


STEP 2: Process Each Group with Helper Function
════════════════════════════════════════════════

Group 0: 567 → helper(567)
┌─────────────────────────────────────┐
│  567                                 │
│   │                                  │
│   ├── Hundreds place: 5             │
│   │   → "Five Hundred"              │
│   │                                  │
│   └── Remainder: 67                 │
│       ├── Tens place: 6             │
│       │   → "Sixty"                 │
│       │                              │
│       └── Ones place: 7             │
│           → "Seven"                 │
│                                      │
│  Result: "Five Hundred Sixty Seven" │
└─────────────────────────────────────┘

Group 1: 234 → helper(234)
┌──────────────────────────────────────┐
│  234                                  │
│   │                                   │
│   ├── Hundreds place: 2              │
│   │   → "Two Hundred"                │
│   │                                   │
│   └── Remainder: 34                  │
│       ├── Tens place: 3              │
│       │   → "Thirty"                 │
│       │                               │
│       └── Ones place: 4              │
│           → "Four"                   │
│                                       │
│  Result: "Two Hundred Thirty Four"   │
└──────────────────────────────────────┘

Group 2: 001 → helper(1)
┌─────────────────────────┐
│  1                       │
│   │                      │
│   └── < 20              │
│       → "One"           │
│                          │
│  Result: "One"          │
└─────────────────────────┘


STEP 3: Combine Results (Insert at Beginning)
══════════════════════════════════════════════

StringBuilder result = ""

Iteration 0 (Group 0, groupIndex=0):
  group = 567 (non-zero)
  groupWords = "Five Hundred Sixty Seven"
  scale = thousands[0] = ""
  result = "Five Hundred Sixty Seven " + ""
         = "Five Hundred Sixty Seven "

Iteration 1 (Group 1, groupIndex=1):
  group = 234 (non-zero)
  groupWords = "Two Hundred Thirty Four"
  scale = thousands[1] = "Thousand"
  result = "Two Hundred Thirty Four Thousand " + "Five Hundred Sixty Seven "
         = "Two Hundred Thirty Four Thousand Five Hundred Sixty Seven "

Iteration 2 (Group 2, groupIndex=2):
  group = 1 (non-zero)
  groupWords = "One"
  scale = thousands[2] = "Million"
  result = "One Million " + "Two Hundred Thirty Four Thousand Five Hundred Sixty Seven "
         = "One Million Two Hundred Thirty Four Thousand Five Hundred Sixty Seven "

Final: result.trim()
     = "One Million Two Hundred Thirty Four Thousand Five Hundred Sixty Seven"
```

### Helper Function Flow Chart (Numbers < 1000)

```
                    helper(num)
                        │
                        ▼
              ┌─────────────────┐
              │   num == 0?     │
              └────────┬────────┘
                   Yes │ No
                   ▼   │
               return ""│
                       │
              ┌────────▼────────┐
              │   num < 20?     │
              └────────┬────────┘
                   Yes │ No
                   ▼   │
          below20[num] │
               + " "   │
                       │
              ┌────────▼────────┐
              │   num < 100?    │
              └────────┬────────┘
                   Yes │ No
                   ▼   │
        tens[num/10]   │
        + " " +        │
        helper(num%10) │
                       │
              ┌────────▼─────────┐
              │   num >= 100     │
              └────────┬─────────┘
                       │
                       ▼
              below20[num/100]
              + " Hundred " +
              helper(num%100)


Example Traces:
───────────────

helper(7):     7 < 20  →  "Seven "

helper(15):    15 < 20  →  "Fifteen "

helper(42):    42 < 100
               tens[42/10] = tens[4] = "Forty"
               helper(42%10) = helper(2) = "Two "
               Result: "Forty Two "

helper(123):   123 >= 100
               below20[123/100] = below20[1] = "One"
               helper(123%100) = helper(23)
                                = 23 < 100
                                = tens[2] = "Twenty"
                                  helper(3) = "Three "
                                = "Twenty Three "
               Result: "One Hundred Twenty Three "
```

### Data Structure Visualization

```
┌─────────────────────────────────────────────────────────────────┐
│                      LOOKUP ARRAYS                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  below20[]:                                                       │
│  ┌───┬─────┬─────┬───────┬──────┬──────┬─────┬───────┬─────┐   │
│  │ 0 │  1  │  2  │   3   │  4   │  5   │  6  │  ...  │ 19  │   │
│  ├───┼─────┼─────┼───────┼──────┼──────┼─────┼───────┼─────┤   │
│  │"" │"One"│"Two"│"Three"│"Four"│"Five"│"Six"│  ...  │"19" │   │
│  └───┴─────┴─────┴───────┴──────┴──────┴─────┴───────┴─────┘   │
│                                                                   │
│  tens[]:                                                          │
│  ┌───┬────┬─────────┬─────────┬────────┬─────────┬───────┐     │
│  │ 0 │ 1  │    2    │    3    │   4    │    5    │  ...  │     │
│  ├───┼────┼─────────┼─────────┼────────┼─────────┼───────┤     │
│  │"" │ "" │"Twenty" │"Thirty" │"Forty" │"Fifty"  │  ...  │     │
│  └───┴────┴─────────┴─────────┴────────┴─────────┴───────┘     │
│                                                                   │
│  thousands[]:                                                     │
│  ┌───┬───────────┬──────────┬──────────┐                        │
│  │ 0 │     1     │     2    │     3    │                        │
│  ├───┼───────────┼──────────┼──────────┤                        │
│  │"" │"Thousand" │"Million" │"Billion" │                        │
│  └───┴───────────┴──────────┴──────────┘                        │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Edge Case Handling Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                       EDGE CASES                              │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Case 1: Zero                                                 │
│  ┌─────┐                                                      │
│  │  0  │  →  Check at start  →  Return "Zero"               │
│  └─────┘      (Special case)                                 │
│                                                               │
│  Case 2: Teens (10-19)                                        │
│  ┌──────┐                                                     │
│  │  12  │  →  12 < 20  →  below20[12] = "Twelve"           │
│  └──────┘     (Use below20 array directly)                   │
│                                                               │
│  Case 3: Round Thousands                                      │
│  ┌─────────┐                                                  │
│  │ 1,000   │  →  Group 0: 000 (skip!)                        │
│  └─────────┘     Group 1: 001 → "One Thousand"              │
│                  (Avoid "One Thousand Zero")                 │
│                                                               │
│  Case 4: Gaps (1,000,007)                                     │
│  ┌───────────┐                                                │
│  │1,000,007  │  →  Group 0: 007 → "Seven"                   │
│  └───────────┘     Group 1: 000 (skip!)                      │
│                    Group 2: 001 → "One Million"              │
│                    Result: "One Million Seven"               │
│                    (Skip empty thousands group)              │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

## Optimized Approach: Divide and Conquer with Grouping

### Strategy
Process the number in groups of three digits (thousands, millions, billions) from right to left. Convert each group to words and append the appropriate scale word.

```java
public String numberToWords(int num) {
    if (num == 0) return "Zero";
    
    // Define lookup arrays
    String[] below20 = {"", "One", "Two", "Three", "Four", "Five", "Six", 
                        "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve", 
                        "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", 
                        "Eighteen", "Nineteen"};
    
    String[] tens = {"", "", "Twenty", "Thirty", "Forty", "Fifty", 
                     "Sixty", "Seventy", "Eighty", "Ninety"};
    
    String[] thousands = {"", "Thousand", "Million", "Billion"};
    
    StringBuilder result = new StringBuilder();
    int groupIndex = 0;
    
    // Process each group of 3 digits from right to left
    while (num > 0) {
        int group = num % 1000;
        if (group != 0) {
            String groupWords = helper(group, below20, tens);
            result.insert(0, groupWords + thousands[groupIndex] + " ");
        }
        num /= 1000;
        groupIndex++;
    }
    
    return result.toString().trim();
}

// Helper function to convert numbers < 1000 to words
private String helper(int num, String[] below20, String[] tens) {
    if (num == 0) {
        return "";
    } else if (num < 20) {
        return below20[num] + " ";
    } else if (num < 100) {
        return tens[num / 10] + " " + helper(num % 10, below20, tens);
    } else {
        return below20[num / 100] + " Hundred " + helper(num % 100, below20, tens);
    }
}
```

**Time Complexity**: O(1) - number has at most 10 digits (max 2^31-1)  
**Space Complexity**: O(1) - fixed size lookup arrays and string builder

### Alternative Approach: Iterative with String Building

```java
public String numberToWords(int num) {
    if (num == 0) return "Zero";
    
    String[] below20 = {"", "One", "Two", "Three", "Four", "Five", "Six", 
                        "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve", 
                        "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", 
                        "Eighteen", "Nineteen"};
    
    String[] tens = {"", "", "Twenty", "Thirty", "Forty", "Fifty", 
                     "Sixty", "Seventy", "Eighty", "Ninety"};
    
    String[] thousands = {"Billion", "Million", "Thousand", ""};
    int[] divisors = {1_000_000_000, 1_000_000, 1_000, 1};
    
    StringBuilder result = new StringBuilder();
    
    for (int i = 0; i < 4; i++) {
        int group = num / divisors[i];
        if (group > 0) {
            result.append(convertHundreds(group, below20, tens));
            result.append(thousands[i]).append(" ");
            num %= divisors[i];
        }
    }
    
    return result.toString().trim();
}

private String convertHundreds(int num, String[] below20, String[] tens) {
    StringBuilder sb = new StringBuilder();
    
    if (num >= 100) {
        sb.append(below20[num / 100]).append(" Hundred ");
        num %= 100;
    }
    
    if (num >= 20) {
        sb.append(tens[num / 10]).append(" ");
        num %= 10;
    }
    
    if (num > 0 && num < 20) {
        sb.append(below20[num]).append(" ");
    }
    
    return sb.toString();
}
```

## Key Insights

1. **Group by Thousands**: Split number into groups of 3 digits (ones, thousands, millions, billions)
2. **Reusable Helper**: Create a helper function for converting numbers < 1000 to words
3. **Handle Special Cases**:
   - Zero is the only number that returns "Zero" directly
   - Numbers 10-19 are irregular ("Eleven", "Twelve", etc.)
   - Empty groups should not produce output (e.g., 1,000,000 should not say "Zero Thousand")
4. **String Building**: Use StringBuilder and trim final result to avoid extra spaces

## Edge Cases to Handle

1. **Zero**: `num = 0` → "Zero"
2. **Single digit**: `num = 7` → "Seven"
3. **Teen numbers**: `num = 12` → "Twelve"
4. **Round thousands**: `num = 1000` → "One Thousand" (not "One Thousand Zero")
5. **Maximum value**: `num = 2147483647` → "Two Billion One Hundred Forty Seven Million Four Hundred Eighty Three Thousand Six Hundred Forty Seven"
6. **Hundreds**: `num = 100` → "One Hundred" (not "One Hundred Zero")

## Common Pitfalls

1. **Extra Spaces**: Ensure proper trimming and space handling
2. **Irregular Teens**: Numbers 10-19 need special handling
3. **Empty Groups**: Skip groups that are zero (e.g., 1,000,007 should not say "Zero Thousand")
4. **Off-by-One**: Be careful with array indices and modulo operations
5. **Concatenation Order**: Process groups from highest to lowest scale

## Pattern Recognition

This problem uses the **Divide and Conquer** pattern:
- **Divide**: Split the problem into groups of 3 digits
- **Conquer**: Solve each group independently using a helper function
- **Combine**: Merge results with appropriate scale words (Thousand, Million, Billion)

Similar to:
- Number formatting problems
- Base conversion problems
- Recursive decomposition problems

## Tips and Tricks

1. **Lookup Arrays**: Pre-define all word mappings to avoid complex conditionals
2. **Helper Function**: Extract the logic for numbers < 1000 into a reusable function
3. **Recursive vs Iterative**: Both approaches work; choose based on preference
4. **String Building**: Use StringBuilder for efficiency when concatenating multiple strings
5. **Test Boundaries**: Test with 0, 19, 20, 99, 100, 1000, 1000000, and max value

## Related Problems

- LC 12: Integer to Roman
- LC 13: Roman to Integer
- LC 166: Fraction to Recurring Decimal
- LC 38: Count and Say
- LC 65: Valid Number
