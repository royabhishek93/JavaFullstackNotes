# LeetCode Solutions - Current Structure

This folder contains Markdown-based LeetCode notes organized for interview preparation in 2026.

## Current Status
- `162` solution files currently exist in this folder tree.
- All questions from the tracked Top 150 target list have matching solutions.
- Filenames now include both interview priority and approximate LeetCode likes.

## Filename Convention
Each solution file follows this format:

```text
HIGH_LC1_Two_Sum_L55K.md
MED_LC189_Rotate_Array_L12K.md
LOW_LC65_Valid_Number_L5K.md
```

Meaning:
- `HIGH`, `MED`, `LOW` = interview priority for 2026 prep
- `LC<number>` = LeetCode problem number
- descriptive title = problem name
- `_L<number>K` = approximate likes count in thousands

## Solution Format
Each note generally includes:
- LeetCode link
- optimized approach
- Java implementation
- time and space complexity
- key insights
- edge cases or common mistakes

## Top-Level Structure

```text
leetcode_solutions/
├── Arrays_Strings/
├── Backtracking/
├── Binary_Search/
├── Design/
├── Dynamic_Programming/
├── Graphs/
├── Graphs_Topological_Sort/
├── Greedy_DP/
├── Greedy_Intervals/
├── Heap_Priority_Queue/
├── Linked_Lists/
├── Math_Divide_Conquer/
├── Stack_Queue/
└── Trees/
```

## Arrays_Strings Structure
`Arrays_Strings` has been fully reorganized by implementation approach. It currently contains `46` categorized solution files under these subfolders:

- `Array_Reversal_Approach`
- `Array_Simulation_Approach`
- `Bit_Manipulation_Approach`
- `Cycle_Detection_Approach`
- `Cyclic_Sort_Approach`
- `Expand_Around_Center_Approach`
- `Greedy_Approach`
- `Hashing_Counting_Approach`
- `Matrix_Simulation_Approach`
- `Monotonic_Queue_Approach`
- `Permutation_Simulation_Approach`
- `Prefix_Suffix_Approach`
- `Sliding_Window_Approach`
- `String_Matching_Approach`
- `String_Parsing_Approach`
- `String_Scanning_Approach`
- `String_Simulation_Approach`
- `Two_Pointers_Approach`
- `Voting_Algorithm_Approach`

Representative examples:
- `Hashing_Counting_Approach` -> `LC1`, `LC49`, `LC128`, `LC560`
- `Two_Pointers_Approach` -> `LC11`, `LC15`, `LC42`, `LC88`
- `Sliding_Window_Approach` -> `LC3`, `LC76`, `LC438`, `LC567`
- `Matrix_Simulation_Approach` -> `LC36`, `LC48`, `LC54`, `LC73`
- `Prefix_Suffix_Approach` -> `LC238`
- `Cyclic_Sort_Approach` -> `LC41`
- `Expand_Around_Center_Approach` -> `LC5`

## Other Folder Structure

### Dynamic_Programming
- `Basic_DP`
- `Grid_Paths`
- `Kadane_Algorithm`
- `Kadane_Variants`
- `Stock_Trading`
- `BFS_DP_Coin_Change`

### Linked_Lists
- `Cycle_Detection`
- `Graph_Copy`
- `Node_Manipulation`
- `Pointer_Manipulation_Approach`

### Trees
- `BFS_Queue_Approach`
- `DFS_Recursion_Approach`
- `Trie_Approach`

### Graphs
- `BFS_Grid_Traversal`
- `Island_Components`

## How To Use This Folder
- Start with `HIGH_` problems first.
- Use likes count as a signal for popularity, not difficulty.
- Study by folder if you want pattern repetition.
- Study by filename prefix if you want interview-priority-first revision.

## Recommended Prep Order
1. `HIGH_` problems in core folders: `Arrays_Strings`, `Linked_Lists`, `Trees`, `Dynamic_Programming`
2. `MED_` problems for coverage expansion
3. `LOW_` problems only after fundamentals are stable
4. Revise by approach, not only by problem number

## Tips and Tricks
- Revise in priority order: HIGH first, then MED, and use LOW only after the core set feels automatic.
- Group problems by implementation approach during revision because pattern recall is stronger than problem-order recall.
- Use likes count as a popularity signal, but let interview frequency and pattern coverage drive your prep order.
