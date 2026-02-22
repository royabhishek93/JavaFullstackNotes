# 🎯 Q39: Pagination, Filtering, and Sorting Best Practices

> **Interview Frequency:** 52% | **Difficulty:** ⭐⭐⭐ | **Study Time:** 3 minutes

---

## 🤔 Problem

Return 1M products. How to let client filter, sort, and paginate?

---

## 📌 Query Parameters

```
GET /api/products?page=1&size=20&sort=price,desc&category=Electronics&minPrice=100
```

---

## 📌 Response Format

```json
{
  "content": [
    {"id": 1, "name": "Phone", "price": 500},
    {"id": 2, "name": "Laptop", "price": 1000}
  ],
  "page": 1,
  "pageSize": 20,
  "totalElements": 5000,
  "totalPages": 250,
  "hasNext": true
}
```

---

## ✅ Best Practices

1. **Limit page size** - Min 1, max 100 (prevent DOS)
2. **Default sort** - By relevance or date
3. **Filter validation** - Only allow whitelisted fields
4. **Offset vs cursor** - Offset for small datasets, cursor for large

---

## 💬 Interview Tip (Say This Exactly)

"Use query params: page, size (max 100), sort, filters. Return total count, hasNext flag. Validate filters server-side. For large datasets (>10M), use cursor-based pagination (page token) not offset."

---

**Last Updated:** February 22, 2026  
**Next: [Q40_api_security.md](Q40_api_security.md)**
