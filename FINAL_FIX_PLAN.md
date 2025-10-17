# Final Fix Plan Based on Clean Test Results

## Issues to Fix:

### 1. modules.txt Double Replacement
- Problem: Still getting double replacement in some cases
- Solution: Ensure modules.txt is written AFTER all replacements

### 2. apps.txt Consistency  
- Problem: Not updating all site files consistently
- Solution: Better site discovery and file handling

### 3. Error Recovery
- Problem: One broken app breaks entire system
- Solution: Add graceful error handling for app imports

## Implementation Steps:
1. Fix modules.txt creation timing
2. Improve site apps.txt handling
3. Add error isolation for broken apps
4. Test with progressively complex apps
