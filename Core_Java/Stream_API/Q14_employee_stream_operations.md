# Q14: Employee Stream Operations (Comprehensive Java 8 Guide)

**Study Time:** 15-20 minutes | **Frequency:** 80% in interviews 🔥 | **Difficulty:** ⭐⭐⭐⭐

---

## Problem Setup

You have a list of `Employee` objects:

```java
public class Employee {
    private long id;
    private String name;
    private String department;
    private double salary;
    
    // Constructor, getters, setters
    public Employee(long id, String name, String department, double salary) {
        this.id = id;
        this.name = name;
        this.department = department;
        this.salary = salary;
    }
    
    @Override
    public String toString() {
        return "Employee{" + "id=" + id + ", name='" + name + '\'' +
                ", department='" + department + '\'' + 
                ", salary=" + salary + '}';
    }
}

// Sample data:
List<Employee> employees = Arrays.asList(
    new Employee(1, "Alice", "IT", 75000),
    new Employee(2, "Bob", "HR", 60000),
    new Employee(3, "Charlie", "IT", 80000),
    new Employee(4, "Diana", "Finance", 70000),
    new Employee(5, "Eve", "IT", 65000),
    new Employee(6, "Frank", "HR", 55000),
    new Employee(7, "Grace", "Finance", 85000)
);
```

---

## 7 Common Employee Stream Operations

### Operation 1: Find Employee with Second Highest Salary

#### Problem
Get the employee with the **second highest** salary.

#### ❌ WRONG Approach

```java
// Wrong: What if two employees have same highest salary?
Employee secondHighest = employees.stream()
        .sorted(Comparator.comparing(Employee::getSalary).reversed())
        .skip(1)
        .findFirst()
        .orElse(null);

// Duplicate salaries cause issues:
// Salaries: [100, 100, 90, 80]
// skip(1) + findFirst() = 100 (not 90!)
// Should be: 90 (second unique highest)
```

#### ✅ RIGHT Approach

```java
// Approach 1: Skip and find first (works if duplicates okay)
Employee secondHighest = employees.stream()
        .sorted(Comparator.comparing(Employee::getSalary).reversed())
        .skip(1)
        .findFirst()
        .orElse(null);  // Returns second in sorted list

System.out.println(secondHighest);
// Output: Employee{id=3, name='Charlie', department='IT', salary=80000.0}

// Approach 2: Get second UNIQUE highest salary (more correct)
Employee secondHighestUnique = employees.stream()
        .map(Employee::getSalary)
        .distinct()
        .sorted(Collections.reverseOrder())
        .skip(1)
        .findFirst()
        .map(salary -> employees.stream()
                .filter(e -> e.getSalary() == salary)
                .findFirst()
                .orElse(null))
        .orElse(null);

// More elegant using minBy:
Double secondHighestSalary = employees.stream()
        .sorted(Comparator.comparing(Employee::getSalary).reversed())
        .distinct()
        .skip(1)
        .findFirst()
        .map(Employee::getSalary)
        .orElse(null);

System.out.println(secondHighestSalary);  // 75000.0 (Alice)
```

**Explanation:**
- `.sorted(...reversed())` - Sort descending by salary
- `.skip(1)` - Skip the first (highest)
- `.findFirst()` - Get next one (second highest)
- `.orElse(null)` - Return null if not found

---

### Operation 2: Find All IT Department Employees Sorted by Salary

#### Problem
Get all employees from IT department, sorted by salary (ascending).

#### ❌ WRONG Approach

```java
// Wrong: Creates unnecessary variable, less functional
List<Employee> itEmployees = new ArrayList<>();
for (Employee emp : employees) {
    if ("IT".equals(emp.getDepartment())) {
        itEmployees.add(emp);
    }
}
Collections.sort(itEmployees, Comparator.comparing(Employee::getSalary));

itEmployees.forEach(System.out::println);

// Problems:
// - Imperative style (old Java)
// - Multiple statements
// - Not idiomatic Java 8
```

#### ✅ RIGHT Approach

```java
// Stream pipeline: filter → sort → collect
List<Employee> itEmployees = employees.stream()
        .filter(emp -> emp.getDepartment().equals("IT"))
        .sorted(Comparator.comparing(Employee::getSalary))
        .collect(Collectors.toList());

itEmployees.forEach(System.out::println);

// Output:
// Employee{id=5, name='Eve', department='IT', salary=65000.0}
// Employee{id=1, name='Alice', department='IT', salary=75000.0}
// Employee{id=3, name='Charlie', department='IT', salary=80000.0}
```

**Without storing in list (direct output):**
```java
employees.stream()
        .filter(emp -> emp.getDepartment().equals("IT"))
        .sorted(Comparator.comparing(Employee::getSalary))
        .forEach(System.out::println);
```

---

### Operation 3: IT Employees Sorted by Salary (Descending)

#### Problem
Get IT employees, sorted by salary from highest to lowest.

#### Code

```java
employees.stream()
        .filter(emp -> emp.getDepartment().equals("IT"))
        .sorted(Comparator.comparing(Employee::getSalary).reversed())
        .forEach(System.out::println);

// Output:
// Employee{id=3, name='Charlie', department='IT', salary=80000.0}
// Employee{id=1, name='Alice', department='IT', salary=75000.0}
// Employee{id=5, name='Eve', department='IT', salary=65000.0}
```

**Key:** Use `.reversed()` to flip sort order.

---

### Operation 4: Find Highest Paid Employee

#### Problem
Get the employee with the **maximum salary**.

#### ❌ WRONG Approach

```java
// Wrong: Manual comparison
double maxSalary = Double.MIN_VALUE;
Employee highest = null;

for (Employee emp : employees) {
    if (emp.getSalary() > maxSalary) {
        maxSalary = emp.getSalary();
        highest = emp;
    }
}

System.out.println(highest);

// Problems:
// - Not using streams
// - Manual tracking of max
// - Verbose
```

#### ✅ RIGHT Approach

```java
Employee highestPaid = employees.stream()
        .max(Comparator.comparing(Employee::getSalary))
        .orElse(null);

System.out.println(highestPaid);
// Output: Employee{id=7, name='Grace', department='Finance', salary=85000.0}
```

**Why better:**
- `.max()` clearly expresses intent
- `.orElse(null)` handles empty stream
- One-liner with stream

**Alternative - Get just the salary:**
```java
Double maxSalary = employees.stream()
        .mapToDouble(Employee::getSalary)
        .max()
        .orElse(0.0);

System.out.println("Max salary: " + maxSalary);  // 85000.0
```

---

### Operation 5: Group Employees by Department

#### Problem
Create a map: Department → List of Employees.

#### ❌ WRONG Approach

```java
// Wrong: Manual grouping
Map<String, List<Employee>> groupedByDept = new LinkedHashMap<>();

for (Employee emp : employees) {
    String dept = emp.getDepartment();
    if (!groupedByDept.containsKey(dept)) {
        groupedByDept.put(dept, new ArrayList<>());
    }
    groupedByDept.get(dept).add(emp);
}

groupedByDept.forEach((dept, empList) -> {
    System.out.println(dept + " -> " + empList);
});

// Problems:
// - Verbose setup
// - Manual null checking
// - Not using collectors
```

#### ✅ RIGHT Approach

```java
Map<String, List<Employee>> groupedByDept = employees.stream()
        .collect(Collectors.groupingBy(Employee::getDepartment));

groupedByDept.forEach((dept, empList) -> {
    System.out.println(dept + " -> " + empList);
});

// Output:
// Finance -> [Employee{...id=4...}, Employee{...id=7...}]
// HR -> [Employee{...id=2...}, Employee{...id=6...}]
// IT -> [Employee{...id=1...}, Employee{...id=3...}, Employee{...id=5...}]
```

**With LinkedHashMap (maintains insertion order):**
```java
Map<String, List<Employee>> groupedByDept = employees.stream()
        .collect(Collectors.groupingBy(
                Employee::getDepartment,
                LinkedHashMap::new,  // ← Maintains order
                Collectors.toList()
        ));
```

---

### Operation 6: Find Average Salary by Department

#### Problem
Create a map: Department → Average Salary.

#### ❌ WRONG Approach

```java
// Wrong: Two passes, manual grouping
Map<String, Double> avgSalaryByDept = new HashMap<>();
Map<String, Integer> countByDept = new HashMap<>();

for (Employee emp : employees) {
    String dept = emp.getDepartment();
    
    // Track sum
    avgSalaryByDept.put(dept, 
        avgSalaryByDept.getOrDefault(dept, 0.0) + emp.getSalary());
    
    // Track count
    countByDept.put(dept, countByDept.getOrDefault(dept, 0) + 1);
}

// Calculate averages
for (String dept : avgSalaryByDept.keySet()) {
    avgSalaryByDept.put(dept, 
        avgSalaryByDept.get(dept) / countByDept.get(dept));
}

// Problems:
// - Complex logic spread across code
// - Two separate maps
// - Manual average calculation
```

#### ✅ RIGHT Approach

```java
Map<String, Double> avgSalaryByDept = employees.stream()
        .collect(Collectors.groupingBy(
                Employee::getDepartment,
                Collectors.averagingDouble(Employee::getSalary)
        ));

avgSalaryByDept.forEach((dept, avgSalary) ->
        System.out.println(dept + " -> " + avgSalary));

// Output:
// Finance -> 77500.0
// HR -> 57500.0
// IT -> 73333.33333333333
```

**Explanation:**
- `.groupingBy()` - Group by department
- `.averagingDouble()` - Automatically calculate average
- One operation, clean result

**To also count employees per department:**
```java
Map<String, Long> countByDept = employees.stream()
        .collect(Collectors.groupingBy(
                Employee::getDepartment,
                Collectors.counting()  // Count elements
        ));

countByDept.forEach((dept, count) ->
        System.out.println(dept + " -> " + count + " employees"));

// Output:
// Finance -> 2 employees
// HR -> 2 employees
// IT -> 3 employees
```

---

### Operation 7: Find Minimum Salary

#### Problem
Get the employee with the **minimum salary**.

#### Code

```java
Employee lowestPaid = employees.stream()
        .min(Comparator.comparing(Employee::getSalary))
        .orElse(null);

System.out.println(lowestPaid);
// Output: Employee{id=6, name='Frank', department='HR', salary=55000.0}
```

**Get just the salary:**
```java
Double minSalary = employees.stream()
        .mapToDouble(Employee::getSalary)
        .min()
        .orElse(0.0);

System.out.println("Min salary: " + minSalary);  // 55000.0
```

---

## Complete Working Code

```java
import java.util.*;
import java.util.stream.Collectors;

public class EmployeeStreamDemo {
    
    public static void main(String[] args) {
        List<Employee> employees = Arrays.asList(
            new Employee(1, "Alice", "IT", 75000),
            new Employee(2, "Bob", "HR", 60000),
            new Employee(3, "Charlie", "IT", 80000),
            new Employee(4, "Diana", "Finance", 70000),
            new Employee(5, "Eve", "IT", 65000),
            new Employee(6, "Frank", "HR", 55000),
            new Employee(7, "Grace", "Finance", 85000)
        );
        
        // 1. Second highest salary
        System.out.println("1. Second Highest Salary:");
        Employee secondHighest = employees.stream()
                .sorted(Comparator.comparing(Employee::getSalary).reversed())
                .skip(1)
                .findFirst()
                .orElse(null);
        System.out.println(secondHighest);
        
        // 2. IT employees sorted by salary (ascending)
        System.out.println("\n2. IT Employees (Ascending Salary):");
        employees.stream()
                .filter(emp -> emp.getDepartment().equals("IT"))
                .sorted(Comparator.comparing(Employee::getSalary))
                .forEach(System.out::println);
        
        // 3. IT employees sorted by salary (descending)
        System.out.println("\n3. IT Employees (Descending Salary):");
        employees.stream()
                .filter(emp -> emp.getDepartment().equals("IT"))
                .sorted(Comparator.comparing(Employee::getSalary).reversed())
                .forEach(System.out::println);
        
        // 4. Highest paid employee
        System.out.println("\n4. Highest Paid Employee:");
        Employee highestPaid = employees.stream()
                .max(Comparator.comparing(Employee::getSalary))
                .orElse(null);
        System.out.println(highestPaid);
        
        // 5. Group by department
        System.out.println("\n5. Group by Department:");
        Map<String, List<Employee>> groupedByDept = employees.stream()
                .collect(Collectors.groupingBy(Employee::getDepartment));
        groupedByDept.forEach((dept, empList) ->
                System.out.println(dept + " -> " + empList.size() + " employees"));
        
        // 6. Average salary by department
        System.out.println("\n6. Average Salary by Department:");
        Map<String, Double> avgSalaryByDept = employees.stream()
                .collect(Collectors.groupingBy(
                        Employee::getDepartment,
                        Collectors.averagingDouble(Employee::getSalary)
                ));
        avgSalaryByDept.forEach((dept, avgSalary) ->
                System.out.println(String.format("%s -> $%.2f", dept, avgSalary)));
        
        // 7. Lowest paid employee
        System.out.println("\n7. Lowest Paid Employee:");
        Employee lowestPaid = employees.stream()
                .min(Comparator.comparing(Employee::getSalary))
                .orElse(null);
        System.out.println(lowestPaid);
    }
}
```

---

## Interview Patterns to Know

### Pattern 1: Filter + Map + Collect

```java
// Get all IT employee names
List<String> itNames = employees.stream()
        .filter(e -> e.getDepartment().equals("IT"))
        .map(Employee::getName)  // Transform to names
        .collect(Collectors.toList());

// Get all salaries as double[]
double[] allSalaries = employees.stream()
        .mapToDouble(Employee::getSalary)
        .toArray();
```

---

### Pattern 2: Grouping with Aggregation

```java
// Count employees per department
Map<String, Long> countByDept = employees.stream()
        .collect(Collectors.groupingBy(
                Employee::getDepartment,
                Collectors.counting()
        ));

// Sum of salaries per department
Map<String, Double> salaryByDept = employees.stream()
        .collect(Collectors.groupingBy(
                Employee::getDepartment,
                Collectors.summingDouble(Employee::getSalary)
        ));
```

---

### Pattern 3: Finding with Fallback

```java
// Find or default to null
Employee found = employees.stream()
        .filter(e -> e.getId() == 999)
        .findFirst()
        .orElse(null);

// Find or throw exception
Employee mustFind = employees.stream()
        .filter(e -> e.getId() == 1)
        .findFirst()
        .orElseThrow(() -> new RuntimeException("Employee not found"));
```

---

## Common Mistakes

```java
❌ MISTAKE 1: forEach for transformation  
employees.stream()
    .map(e -> e.getSalary() * 1.1)  // 10% raise
    .forEach(System.out::println);
    
// Problem: Results are printed but not collected

✅ CORRECT: Collect if you need results
List<Double> newSalaries = employees.stream()
    .map(e -> e.getSalary() * 1.1)
    .collect(Collectors.toList());

❌ MISTAKE 2: Not handling Optional
Employee emp = employees.stream()
    .filter(e -> e.getId() == 999)
    .findFirst();  // Returns Optional!
emp.getSalary();  // NoSuchElementException!

✅ CORRECT: Handle Optional
Employee emp = employees.stream()
    .filter(e -> e.getId() == 999)
    .findFirst()
    .orElse(null);

❌ MISTAKE 3: Multiple streams for same operation
employees.stream().filter(...).count();
employees.stream().filter(...).collect(...);  // Second stream!

✅ CORRECT: Single stream
long count = employees.stream()
    .filter(...)
    .peek(...)  // Intermediate
    .collect(Collectors.toList())
    .size();
```

---

## Interview Cheat Sheet

| Operation | Code | Returns |
|-----------|------|---------|
| **Second highest** | `.sorted(...).skip(1).findFirst()` | Optional<T> |
| **Filter + Sort** | `.filter().sorted()` | Stream |
| **Max** | `.max(Comparator.comparing(...))` | Optional<T> |
| **Group by** | `.collect(groupingBy(...))` | Map |
| **Average** | `.collect(groupingBy(..., averagingDouble(...)))` | Map<K, Double> |
| **Count** | `.collect(counting())` | Long |
| **All numbers** | `.mapToDouble(...).toArray()` | double[] |

---

## Interview Answer (Complete)

**Q: "Show me 5 stream operations with employees."**

**Answer:**

> "I'll demonstrate with the `Employee` class having fields: id, name, department, salary.
>
> **1. Find second highest salary:**
> ```java
> Employee second = employees.stream()
>     .sorted(Comparator.comparing(Employee::getSalary).reversed())
>     .skip(1)
>     .findFirst()
>     .orElse(null);
> ```
>
> **2. IT employees sorted by salary:**
> ```java
> employees.stream()
>     .filter(e -> e.getDepartment().equals("IT"))
>     .sorted(Comparator.comparing(Employee::getSalary))
>     .forEach(System.out::println);
> ```
>
> **3. Highest paid employee:**
> ```java
> Employee highest = employees.stream()
>     .max(Comparator.comparing(Employee::getSalary))
>     .orElse(null);
> ```
>
> **4. Group by department:**
> ```java
> Map<String, List<Employee>> grouped = employees.stream()
>     .collect(Collectors.groupingBy(Employee::getDepartment));
> ```
>
> **5. Average salary per department:**
> ```java
> Map<String, Double> avgByDept = employees.stream()
>     .collect(Collectors.groupingBy(
>         Employee::getDepartment,
>         Collectors.averagingDouble(Employee::getSalary)
>     ));
> ```
>
> All demonstrate core stream patterns: filter, map, sort, collect, and terminal operations."

---

## Key Takeaways

| Concept | Why Matters | Score |
|---------|------------|-------|
| **Filter + Collect** | Most common pattern | ⭐⭐⭐⭐⭐ |
| **Comparators** | Sorting logic | ⭐⭐⭐⭐⭐ |
| **Optional handling** | Null safety | ⭐⭐⭐⭐⭐ |
| **Grouping** | Data aggregation | ⭐⭐⭐⭐ |
| **Terminal vs Intermediate** | Understanding pipelines | ⭐⭐⭐⭐ |

