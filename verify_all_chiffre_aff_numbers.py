#!/usr/bin/env python3
"""
Script to verify all Chiffre Aff Exe Dzd numbers from the markdown file
Checks lines 205-5219 (approximately 5015 numbers)
"""

def smart_parse_numeric(value):
    """
    Standalone version of smart_parse_numeric for testing
    Intelligently parse numeric values handling multiple formats
    """
    if value is None:
        return None
    
    text = str(value).strip()
    if not text or text.lower() in ['nan', 'none', 'null', '']:
        return None
    
    # Handle negative numbers
    is_negative = text.startswith('-')
    if is_negative:
        text = text[1:]
    
    try:
        # Case 1: Has comma - French format (dots=thousands, comma=decimal)
        if ',' in text:
            # Remove all dots (thousands separators), replace comma with dot
            cleaned = text.replace('.', '').replace(',', '.')
            result = float(cleaned)
            return -result if is_negative else result
        
        # Case 2: Has dots but no comma - need to detect decimal position
        if '.' in text:
            parts = text.rsplit('.', 1)  # Split from right, keep last part
            
            # Check if last part after dot has 2 digits (likely decimals)
            if len(parts) == 2 and parts[1].isdigit() and len(parts[1]) == 2:
                # Last dot is decimal separator
                # Remove all other dots (thousands separators) from integer part
                integer_part = parts[0].replace('.', '')
                cleaned = integer_part + '.' + parts[1]
                result = float(cleaned)
                return -result if is_negative else result
            else:
                # All dots are thousands separators
                cleaned = text.replace('.', '')
                result = float(cleaned)
                return -result if is_negative else result
        
        # Case 3: No separators - just parse directly
        result = float(text)
        return -result if is_negative else result
        
    except (ValueError, TypeError) as e:
        return None

def extract_and_verify_numbers():
    """Extract all numbers from the markdown file and verify processing"""
    
    filename = "CHIFFRE_AFF_EXE_DZD_NUMBER_PROCESSING.md"
    
    print("="*80)
    print("CHIFFRE AFF EXE DZD NUMBERS VERIFICATION")
    print("="*80)
    print()
    
    # Read the file
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading file: {e}")
        return
    
    print(f"Total lines in file: {len(lines)}")
    print(f"Analyzing lines 205-5219...")
    print()
    
    # Extract numbers from lines 205-5219
    numbers = []
    issues = []
    
    for line_num in range(204, min(5219, len(lines))):  # Line 205 is index 204 (0-based)
        line = lines[line_num].strip()
        
        # Skip empty lines
        if not line:
            continue
        
        # Skip header line
        if "Chiffre Aff Exe Dzd" in line:
            continue
        
        # Try to extract number (may have commas, dots, negative sign)
        # Pattern: optional minus, digits, optional dots/commas, optional decimal part
        if line and (line[0].isdigit() or line[0] == '-'):
            original = line
            
            # Parse the number
            parsed = smart_parse_numeric(original)
            
            if parsed is None:
                issues.append({
                    'line': line_num + 1,
                    'original': original,
                    'issue': 'Failed to parse'
                })
            else:
                numbers.append({
                    'line': line_num + 1,
                    'original': original,
                    'parsed': parsed
                })
    
    print("="*80)
    print("PROCESSING SUMMARY")
    print("="*80)
    print()
    print(f"Total numbers found: {len(numbers)}")
    print(f"Failed to parse: {len(issues)}")
    print()
    
    if issues:
        print("⚠️  ISSUES FOUND:")
        print("-" * 80)
        for issue in issues[:20]:  # Show first 20 issues
            print(f"Line {issue['line']:5}: '{issue['original']}' - {issue['issue']}")
        if len(issues) > 20:
            print(f"... and {len(issues) - 20} more issues")
        print()
    
    # Statistics
    if numbers:
        parsed_values = [n['parsed'] for n in numbers]
        positive = [v for v in parsed_values if v >= 0]
        negative = [v for v in parsed_values if v < 0]
        
        print("="*80)
        print("STATISTICS")
        print("="*80)
        print()
        print(f"Total numbers processed: {len(numbers)}")
        print(f"Positive values: {len(positive)}")
        print(f"Negative values: {len(negative)}")
        print()
        print(f"Sum: {sum(parsed_values):,.2f}")
        print(f"Min: {min(parsed_values):,.2f}")
        print(f"Max: {max(parsed_values):,.2f}")
        print(f"Average: {sum(parsed_values)/len(parsed_values):,.2f}")
        print()
        
        # Check for very large numbers (potential issues)
        large_numbers = [n for n in numbers if abs(n['parsed']) > 10000000]
        if large_numbers:
            print(f"Large numbers (>10M): {len(large_numbers)}")
            print("First 10 large numbers:")
            for num in large_numbers[:10]:
                print(f"  Line {num['line']:5}: {num['original']:20} → {num['parsed']:>15,.2f}")
            print()
        
        # Check format distribution
        comma_format = [n for n in numbers if ',' in n['original']]
        dot_format = [n for n in numbers if '.' in n['original'] and ',' not in n['original']]
        simple_format = [n for n in numbers if ',' not in n['original'] and '.' not in n['original']]
        
        print("Format distribution:")
        print(f"  French format (comma decimal): {len(comma_format)}")
        print(f"  Dot format: {len(dot_format)}")
        print(f"  Simple format: {len(simple_format)}")
        print()
    
    # Sample of first and last numbers
    print("="*80)
    print("SAMPLE VALUES (First 20)")
    print("="*80)
    print()
    print(f"{'Line':>6} | {'Original':>25} | {'Parsed Value':>18}")
    print("-" * 60)
    for num in numbers[:20]:
        print(f"{num['line']:6} | {num['original']:>25} | {num['parsed']:>18,.2f}")
    
    if len(numbers) > 20:
        print()
        print(f"... and {len(numbers) - 20} more numbers")
        print()
        print("Last 10 numbers:")
        print(f"{'Line':>6} | {'Original':>25} | {'Parsed Value':>18}")
        print("-" * 60)
        for num in numbers[-10:]:
            print(f"{num['line']:6} | {num['original']:>25} | {num['parsed']:>18,.2f}")
    
    print()
    print("="*80)
    print("VERIFICATION COMPLETE")
    print("="*80)
    
    if not issues:
        print("✅ All numbers processed successfully!")
    else:
        print(f"⚠️  {len(issues)} numbers had parsing issues")
    
    return numbers, issues

if __name__ == "__main__":
    numbers, issues = extract_and_verify_numbers()
    
    # Save results to file
    if numbers:
        with open("parsed_chiffre_aff_numbers.txt", "w") as f:
            f.write("Line | Original | Parsed Value\n")
            f.write("-" * 60 + "\n")
            for num in numbers:
                f.write(f"{num['line']} | {num['original']} | {num['parsed']:.2f}\n")
        print(f"\n✅ Results saved to: parsed_chiffre_aff_numbers.txt")





