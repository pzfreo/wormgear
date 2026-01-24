# Virtual Hobbing Debug Session

## Problem Summary

Virtual hobbing was failing because build123d's `+` operator creates a `ShapeList` (Python list of shapes) instead of actually fusing them into a single solid Part. This caused:
1. Envelope to be invalid (list instead of Part)
2. Optimizations to fail silently
3. Phase 2 subtraction to produce blank cylinder

## Root Cause

```python
envelope = envelope + hob_rotated  # Creates ShapeList, doesn't fuse!
```

The `+` operator in build123d **collects shapes** into a list, it doesn't perform boolean union. This is why we had 27 shapes in the list after 18 steps (some transformations create multi-part shapes).

## Attempted Fixes

### Fix 1: Post-Phase-1 conversion (FAILED)
- Convert ShapeList to Part after Phase 1 completes
- Problem: Had to fuse 27 shapes sequentially - very slow

### Fix 2: Use OCP fuse during Phase 1 (TESTING)
- Use `BRepAlgoAPI_Fuse` for each union step
- Should keep envelope as single Part throughout
- Currently testing with 9 and 18 steps

## Current Code

```python
from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse

# In Phase 1 loop:
fuser = BRepAlgoAPI_Fuse(env_shape, hob_shape)
fuser.Build()
if fuser.IsDone():
    envelope = Part(fuser.Shape())
```

## Test Plan

1. **Test cylindrical (9 steps)** - fastest iteration
2. **Test cylindrical (18 steps)** - full quality
3. **Test globoid (18 steps)** - complex geometry
4. **Verify result** - teeth should be visible, proper depth

## Performance Notes

- Cylindrical Phase 1 was ~46s with 18 steps (+ operator)
- With OCP fuse, expecting slower but valid results
- Optimizations (trim, simplify) should still work once envelope is valid

## Next Steps

If OCP fuse is too slow:
- Option A: Use simpler geometry (fewer hob sections)
- Option B: Skip virtual hobbing for globoid, only use for cylindrical
- Option C: Periodic simplification every N steps to prevent complexity buildup
- Option D: Use different hobbing approach (incremental subtraction instead of envelope)

## Alternative Approach: Incremental Subtraction

Instead of:
1. Build envelope (union all hob positions)
2. Subtract envelope from blank

Do:
1. Start with blank
2. At each step, subtract hob from wheel directly
3. Result is already the final wheel

Pros:
- No complex envelope to manage
- Each operation is simpler (subtraction vs union)
- Memory usage more predictable

Cons:
- More boolean operations (18 subtractions vs 17 unions + 1 subtraction)
- Overlapping cuts might cause issues
- Potentially slower overall

## Tests Running

- PID 96241: User's test (18 steps, OCP fuse) - running 14+ min
- PID 98465: My test (9 steps, OCP fuse) - running 3+ min

Both using 99% CPU, actively working. Waiting to see if they complete...
