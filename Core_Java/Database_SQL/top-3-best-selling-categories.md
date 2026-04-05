# SQL: Top 3 Best-Selling Product Categories

**Study Time:** 5-7 minutes | **Frequency:** 65% in interviews | **Difficulty:** ⭐⭐⭐

---

## 🤔 Problem Statement

Find the **top 3 best-selling product categories** based on the **total quantity of products sold**, along with the total number of products sold in each category.

**Requirements:**
- Only categories with actual sales (in orderdetails)
- Sort by highest total quantity first
- Limit to top 3 categories
- Include category name and total quantity sold

---

## 📋 Table Schema

### `products` table
```
product_id (PK)  | name           | category    | price
1                | Laptop         | Electronics | 999.99
2                | USB Cable      | Accessories | 9.99
3                | T-Shirt        | Clothing    | 29.99
4                | Monitor        | Electronics | 399.99
5                | Jeans          | Clothing    | 59.99
```

### `orders` table
```
order_id (PK) | customer_id | order_date
1             | 101         | 2026-01-15
2             | 102         | 2026-01-20
3             | 101         | 2026-02-10
```

### `orderdetails` table
```
order_details_id (PK) | order_id (FK) | product_id (FK) | quantity
1                     | 1             | 1               | 2
2                     | 1             | 2               | 5
3                     | 2             | 3               | 3
4                     | 2             | 4               | 1
5                     | 3             | 1               | 1
6                     | 3             | 5               | 2
```

---

## ✅ SQL Query (Solution)

```sql
SELECT 
    p.category AS product_category,
    SUM(od.quantity) AS total_products_sold
FROM orderdetails od
JOIN products p 
    ON od.product_id = p.product_id
GROUP BY p.category
ORDER BY total_products_sold DESC
LIMIT 3;
```

---

## 🧠 Step-by-Step Explanation

### **Step 1: JOIN the Tables**
```sql
FROM orderdetails od
JOIN products p ON od.product_id = p.product_id
```

**What happens:**
- Connects `orderdetails` with `products` using `product_id`
- Each row in orderdetails is matched with its corresponding product and category

**After JOIN (intermediate result):**
```
order_details_id | product_id | quantity | category
1                | 1          | 2        | Electronics
2                | 2          | 5        | Accessories
3                | 3          | 3        | Clothing
4                | 4          | 1        | Electronics
5                | 1          | 1        | Electronics
6                | 5          | 2        | Clothing
```

---

### **Step 2: GROUP BY Category**
```sql
GROUP BY p.category
```

**What happens:**
- Groups all rows by category
- Prepares to aggregate the quantity for each category

**After GROUP BY (logically):**
```
category      | rows
Electronics   | [2, 1] quantities
Accessories   | [5] quantities
Clothing      | [3, 2] quantities
```

---

### **Step 3: Calculate Total Quantity**
```sql
SUM(od.quantity) AS total_products_sold
```

**What happens:**
- Sums all quantities within each category group

**After SUM (intermediate result):**
```
category      | total_products_sold
Electronics   | 2+1 = 3
Accessories   | 5 = 5
Clothing      | 3+2 = 5
```

---

### **Step 4: Sort by Highest Sales First**
```sql
ORDER BY total_products_sold DESC
```

**What happens:**
- Sorts categories by total quantity in descending order (highest first)

**After ORDER BY:**
```
category      | total_products_sold
Accessories   | 5
Clothing      | 5
Electronics   | 3
```

---

### **Step 5: Get Top 3**
```sql
LIMIT 3;
```

**What happens:**
- Returns only the first 3 rows

**Final Result:**
```
product_category | total_products_sold
Accessories      | 5
Clothing         | 5
Electronics      | 3
```

---

## 📊 Visual Execution Flow

```
orderdetails (6 rows)
       ↓
   JOIN products
       ↓
   GROUP BY category
       ↓
   Electronics: 3 products
   Accessories: 5 products
   Clothing: 5 products
       ↓
   ORDER BY total DESC
       ↓
   Accessories (5)
   Clothing (5)
   Electronics (3)
       ↓
   LIMIT 3
       ↓
   Return top 3 ✓
```

---

## 🎯 Interview Q&A

### Q1: "Why do we need the JOIN?"

**Answer:**
```
Orderdetails stores sales data (quantity), but the category is in products.
We need to JOIN them to get the category for each sale.

Without JOIN: Orderdetails has product_id, but not category
With JOIN: We can access p.category from the products table

Example:
orderdetails: [order_id=1, product_id=1, quantity=2]
               ↓ (need to know what category product_id=1 is)
products: [product_id=1, category='Electronics']
               ↓
Result: [order_id=1, quantity=2, category='Electronics']
```

---

### Q2: "What if a category has no sales?"

**Answer:**
```
Current query: Shows only categories that have at least one order

If you want ALL categories (even with 0 sales):
Use LEFT JOIN from products instead:

SELECT 
    p.category,
    COALESCE(SUM(od.quantity), 0) AS total_products_sold
FROM products p
LEFT JOIN orderdetails od 
    ON od.product_id = p.product_id
GROUP BY p.category
ORDER BY total_products_sold DESC
LIMIT 3;

COALESCE: Returns 0 if SUM is NULL (no sales)
```

---

### Q3: "Can we tie-break between categories with equal sales?"

**Answer:**
```
If two categories have the same total quantity, which one appears first
depends on the database's default ordering (usually arbitrary).

To make it deterministic:

SELECT 
    p.category,
    SUM(od.quantity) AS total_products_sold,
    COUNT(DISTINCT od.order_id) AS number_of_orders
FROM orderdetails od
JOIN products p ON od.product_id = p.product_id
GROUP BY p.category
ORDER BY total_products_sold DESC, 
         number_of_orders DESC,
         p.category ASC
LIMIT 3;

This tie-breaks by:
1. Most quantity (DESC)
2. Most orders (DESC) - if tied
3. Category name alphabetically (ASC) - if still tied
```

---

### Q4: "How do you optimize this query for large datasets?"

**Answer:**
```
1. CREATE INDEX on foreign keys (if not already present):
   CREATE INDEX idx_orderdetails_product_id 
   ON orderdetails(product_id);

2. Partition by category (in production databases):
   Useful if you need this query frequently

3. Cache the result:
   Store top 3 in Redis/cache, refresh daily

4. Use materialized view (if available):
   CREATE MATERIALIZED VIEW category_sales AS
   SELECT ...
   (query runs once, results stored)

5. Add EXPLAIN PLAN to see execution:
   EXPLAIN SELECT ... (shows query optimization details)
```

---

### Q5: "What if you want top 3 by revenue instead of quantity?"

**Answer:**
```
Replace SUM(od.quantity) with SUM(od.quantity * p.price):

SELECT 
    p.category AS product_category,
    SUM(od.quantity * p.price) AS total_revenue
FROM orderdetails od
JOIN products p ON od.product_id = p.product_id
GROUP BY p.category
ORDER BY total_revenue DESC
LIMIT 3;

Example:
Electronics: (2 * 999.99) + (1 * 399.99) = 2399.97
Accessories: 5 * 9.99 = 49.95
Clothing: (3 * 29.99) + (2 * 59.99) = 209.95
```

---

### Q6: "How would you write this in a Spring/Java application?"

**Answer (if using Spring Data JPA):**
```java
@Repository
public interface OrderDetailRepository extends JpaRepository<OrderDetail, Long> {
    
    @Query("""
        SELECT new Map(
            p.category as category,
            CAST(SUM(od.quantity) as Long) as totalSold
        )
        FROM OrderDetail od
        JOIN od.product p
        GROUP BY p.category
        ORDER BY SUM(od.quantity) DESC
    """)
    List<Map<String, Object>> getTop3BestSellingCategories(Pageable pageable);
}

// In service layer:
public List<CategorySalesDTO> getTopCategories() {
    Pageable pageable = PageRequest.of(0, 3);
    return orderDetailRepository.getTop3BestSellingCategories(pageable)
        .stream()
        .map(row -> new CategorySalesDTO(
            (String) row.get("category"),
            (Long) row.get("totalSold")
        ))
        .collect(Collectors.toList());
}
```

---

## ❌ Common Mistakes

### ❌ Mistake 1: Forgetting the JOIN

```sql
-- WRONG - No JOIN, can't access category
SELECT 
    category,
    SUM(od.quantity)
FROM orderdetails od
GROUP BY category;

-- ERROR: "Unknown column 'category' in 'field list'"
-- category doesn't exist in orderdetails table!

-- CORRECT
SELECT 
    p.category,
    SUM(od.quantity)
FROM orderdetails od
JOIN products p ON od.product_id = p.product_id
GROUP BY p.category;
```

---

### ❌ Mistake 2: Using LIMIT Without ORDER BY

```sql
-- WRONG - No ORDER BY, LIMIT returns arbitrary 3 rows
SELECT 
    p.category,
    SUM(od.quantity) AS total
FROM orderdetails od
JOIN products p ON od.product_id = p.product_id
GROUP BY p.category
LIMIT 3;

-- Returns any 3 categories, NOT the top 3!

-- CORRECT
SELECT 
    p.category,
    SUM(od.quantity) AS total
FROM orderdetails od
JOIN products p ON od.product_id = p.product_id
GROUP BY p.category
ORDER BY total DESC
LIMIT 3;
```

---

### ❌ Mistake 3: Including Non-Aggregated Column in SELECT

```sql
-- WRONG - product_name is not aggregated and not in GROUP BY
SELECT 
    p.category,
    p.product_name,  -- ERROR in MySQL (strict mode)
    SUM(od.quantity)
FROM orderdetails od
JOIN products p ON od.product_id = p.product_id
GROUP BY p.category;

-- ERROR: "product_name is not in GROUP BY"

-- CORRECT - Only aggregated columns or GROUP BY columns
SELECT 
    p.category,
    SUM(od.quantity)
FROM orderdetails od
JOIN products p ON od.product_id = p.product_id
GROUP BY p.category;
```

---

### ❌ Mistake 4: Using WHERE Instead of HAVING for Aggregates

```sql
-- WRONG - Using WHERE on SUM aggregate
SELECT 
    p.category,
    SUM(od.quantity) AS total
FROM orderdetails od
JOIN products p ON od.product_id = p.product_id
GROUP BY p.category
WHERE SUM(od.quantity) > 10  -- ERROR!
LIMIT 3;

-- ERROR: "Cannot use aggregate function in WHERE clause"

-- CORRECT - Use HAVING for aggregate filters
SELECT 
    p.category,
    SUM(od.quantity) AS total
FROM orderdetails od
JOIN products p ON od.product_id = p.product_id
GROUP BY p.category
HAVING SUM(od.quantity) > 10
ORDER BY total DESC
LIMIT 3;
```

---

### ❌ Mistake 5: Counting Wrong Column

```sql
-- WRONG - Counts orders, not quantity of products
SELECT 
    p.category,
    COUNT(od.order_id) AS total_products_sold  -- This counts orders!
FROM orderdetails od
JOIN products p ON od.product_id = p.product_id
GROUP BY p.category
ORDER BY total_products_sold DESC
LIMIT 3;

-- Example: Category A could have 2 orders with 100 items each
-- COUNT returns 2, but total is actually 200 items!

-- CORRECT - SUM the quantity
SELECT 
    p.category,
    SUM(od.quantity) AS total_products_sold  -- This sums items
FROM orderdetails od
JOIN products p ON od.product_id = p.product_id
GROUP BY p.category
ORDER BY total_products_sold DESC
LIMIT 3;
```

---

## 📊 Alternative Approaches

### **Approach 1: Using WITH (CTE)**
```sql
WITH CategorySales AS (
    SELECT 
        p.category,
        SUM(od.quantity) AS total
    FROM orderdetails od
    JOIN products p ON od.product_id = p.product_id
    GROUP BY p.category
)
SELECT *
FROM CategorySales
ORDER BY total DESC
LIMIT 3;
```

**Advantage:** More readable for complex queries

---

### **Approach 2: Using Subquery**
```sql
SELECT *
FROM (
    SELECT 
        p.category,
        SUM(od.quantity) AS total
    FROM orderdetails od
    JOIN products p ON od.product_id = p.product_id
    GROUP BY p.category
) AS category_totals
ORDER BY total DESC
LIMIT 3;
```

**Advantage:** Can filter subquery results with WHERE

---

### **Approach 3: Using Window Functions (if database supports)**
```sql
SELECT 
    category,
    total,
    ROW_NUMBER() OVER (ORDER BY total DESC) AS rank
FROM (
    SELECT 
        p.category,
        SUM(od.quantity) AS total
    FROM orderdetails od
    JOIN products p ON od.product_id = p.product_id
    GROUP BY p.category
) AS category_totals
WHERE ROW_NUMBER() OVER (ORDER BY total DESC) <= 3;
```

**Advantage:** More control over ranking (handles ties better)

---

## ✅ Best Practices

| Practice | Reason |
|----------|--------|
| Use table aliases (od, p) | Makes query more readable |
| Always order before LIMIT | Ensures consistent top-N results |
| Use descriptive column names (AS) | Improves clarity |
| Test with EXPLAIN PLAN | Verify query optimization |
| Index foreign keys | Speeds up JOINs |
| Use HAVING for aggregates | WHERE is for pre-grouping filters |
| Consider edge cases | Empty results, ties, NULL values |

---

## 🎯 Interview Winning Answers

### **20-Second Answer:**
```
"I'd JOIN orderdetails with products on product_id to get categories,
then GROUP BY category to calculate SUM of quantities per category,
ORDER BY total quantity descending, and LIMIT to 3."
```

### **60-Second Answer (with optimization):**
```
"First, I'd JOIN orderdetails with products to access category names.
Then GROUP BY category to aggregate quantities. I'd use SUM() for
aggregation, ORDER BY total quantity descending, and LIMIT 3 for
top 3 results. For optimization, I'd ensure there's an index on
product_id foreign key. If performance is critical, I might cache
the result or use a materialized view since this doesn't change
frequently."
```

---

## 🔑 Key Concepts Tested

| Concept | Why Important | Interview Score |
|---------|---------------|-----------------|
| JOIN syntax and logic | Core SQL skill | ⭐⭐⭐⭐⭐ |
| GROUP BY and aggregates | Foundational | ⭐⭐⭐⭐⭐ |
| ORDER BY with LIMIT | Data ranking | ⭐⭐⭐⭐ |
| Table relationships (FK) | Database design | ⭐⭐⭐⭐ |
| Query optimization | Production readiness | ⭐⭐⭐ |

---

## 📚 Related Problems

- Find customers who haven't placed orders (LEFT JOIN with NULL check)
- Top N items by region (GROUP BY with multiple criteria)
- Monthly sales trend (GROUP BY with date functions)
- Products above category average (subquery with aggregates)
- Running total sales (window functions)

---

**Priority:** ✅ SHOULD KNOW (Very common in interviews, tests core SQL skills)

**Difficulty Range:** Easy to Medium (straightforward once you know JOIN + GROUP BY)

**Companies Asking:** Amazon, Microsoft, Google, Meta, Netflix (data analyst / backend roles)

---

**Last Updated:** March 5, 2026
