# Git Commands to Upload to GitHub

## Step 1: Initialize Git Repository
```bash
cd "/Users/I771246/Abhi Personal/Leetcode"
git init
```

## Step 2: Add All Files
```bash
git add .
```

## Step 3: Create Initial Commit
```bash
git commit -m "Initial commit: Add LeetCode solutions with DP problems"
```

## Step 4: Create Repository on GitHub
1. Go to https://github.com/new
2. Name it: `leetcode-solutions` (or your preferred name)
3. Don't initialize with README (we already have one)
4. Click "Create repository"

## Step 5: Connect to GitHub and Push
```bash
# Replace YOUR_USERNAME with your GitHub username
git remote add origin https://github.com/YOUR_USERNAME/leetcode-solutions.git
git branch -M main
git push -u origin main
```

## Future Updates (After Making Changes)
```bash
# After adding new solutions
git add .
git commit -m "Add: [Problem Number] - [Problem Name]"
git push
```

## Examples of Good Commit Messages
- `git commit -m "Add: 70 - Climbing Stairs (DP solution)"`
- `git commit -m "Add: 198 - House Robber with test cases"`
- `git commit -m "Update: README with new DP template section"`
