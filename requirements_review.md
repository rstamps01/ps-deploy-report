# VAST Diagram Requirements Review

## Architecture Diagram Requirements

### ✅ COMPLETED REQUIREMENTS:
1. **Switch positioning**: Switches side-by-side with Switch A on the right ✅
2. **Inter-switch connections**: 2 connections from switch to switch ✅
3. **CBox connections**: Each CBox connects to both Switch A & B with color-coded lines ✅
4. **DBox connections**: Each DBox connects to both Switch A & B with color-coded lines ✅
5. **Remove bottom lines**: No lines drawn from DBoxes to bottom of page ✅
6. **Customer network**: Connected directly to Switch A & B ✅
7. **Remove duplicate DBox-4**: Only 4 DBoxes total ✅
8. **Simplified connections**: Only 1 line per component to each switch ✅

### ❌ MISSING REQUIREMENTS:
**DBox Numbering**: Should be DBox-100, DBox-101, DBox-102, DBox-103 (currently shows DBox-1, DBox-2, DBox-3, DBox-4)

## Rack Layout Diagram Requirements

### ✅ COMPLETED REQUIREMENTS:
1. **Remove network port images**: No port graphics on switches ✅
2. **Component heights**: CBoxes 2U, Switches 1U, DBoxes 1U ✅
3. **Visual proportions**: Switches and DBoxes half height of CBoxes ✅

### ❌ MISSING REQUIREMENTS:
1. **DBox numbering**: Should be DBox-100, DBox-101, DBox-102, DBox-103
2. **Exact U positioning**:
   - U31-30: CBox-4 (2U)
   - U29-28: CBox-3 (2U)
   - U27-26: CBox-2 (2U)
   - U25-24: CBox-1 (2U)
   - U23: Empty
   - U22: Switch B (1U)
   - U21: Empty
   - U20: Switch A (1U)
   - U19: Empty
   - U18: DBox-100 (1U)
   - U17: DBox-101 (1U)
   - U16: DBox-102 (1U)
   - U15: DBox-103 (1U)

## Switch Port Map Requirements

### ✅ COMPLETED REQUIREMENTS:
1. **Professional format**: Matches example switch port map style ✅
2. **32-port switches**: Both switches show 32 ports ✅
3. **Cable labels table**: Proper naming convention ✅
4. **A/B port orientation**: Documented in table ✅

### ❌ MISSING REQUIREMENTS:
**DBox references**: Should reference DBox-100 through DBox-103 in cable labels

## Summary of Required Changes

1. **Update DBox numbering** in ALL diagrams from DBox-1,2,3,4 to DBox-100,101,102,103
2. **Fix rack layout positioning** to match exact U specifications
3. **Update switch port map** to reference correct DBox numbers
4. **Update report content** to reflect DBox-100 series numbering

