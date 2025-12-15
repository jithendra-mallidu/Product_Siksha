#!/usr/bin/env python3
"""
PM Interview Questions Cleanup Script
Normalizes company names and categorizes questions into 7 standard buckets.
"""

import csv
import re
from collections import Counter

# ============================================================================
# COMPANY NAME NORMALIZATION MAPPING
# ============================================================================
COMPANY_NORMALIZATION = {
    # Meta / Facebook variations
    'meta': 'Meta',
    'META': 'Meta',
    'MEta': 'Meta',
    'Meta (team match)': 'Meta',
    'Meta / Facebook': 'Meta',
    'Meta/ Facebook': 'Meta',
    'Meta/Facebook': 'Meta',
    'Facebook': 'Meta',
    'facebook': 'Meta',
    'FACEBOOK': 'Meta',
    'FaceBook': 'Meta',
    'Faceboook': 'Meta',
    'Facebook/Meta': 'Meta',
    'Facbook': 'Meta',
    'FB': 'Meta',
    'fb': 'Meta',
    
    # Google variations
    'google': 'Google',
    'Googlw': 'Google',
    'Google`': 'Google',
    'Google (GCP)': 'Google',
    'Google Cloud': 'Google',
    'StraGoogletegic Insights': 'Google',
    'Google/Amazon': 'Google',
    
    # Amazon variations
    'amazon': 'Amazon',
    'Amazxon': 'Amazon',
    'Amzon': 'Amazon',
    'Amazon AWS': 'Amazon',
    'AWS': 'Amazon',
    
    # DoorDash variations
    'Doordash': 'DoorDash',
    'doordash': 'DoorDash',
    'Door Dash': 'DoorDash',
    
    # Microsoft variations
    'MICROSOFT': 'Microsoft',
    'Microsoft Round 1': 'Microsoft',
    
    # LinkedIn variations
    'LInkedIn': 'LinkedIn',
    'Linkedin': 'LinkedIn',
    
    # TikTok variations
    'Tiktok': 'TikTok',
    'Tik Tok': 'TikTok',
    
    # eBay variations
    'ebay': 'eBay',
    'Ebay': 'eBay',
    
    # PayPal variations
    'Paypal': 'PayPal',
    
    # SoFi variations
    'Sofi': 'SoFi',
    
    # Intuit variations
    'Inuit': 'Intuit',
    'Intuit Mailchimp': 'Intuit',
    
    # Adobe variations
    'adobe': 'Adobe',
    
    # Capital One variations
    'Capital one': 'Capital One',
    'CapitalOne': 'Capital One',
    
    # Nubank variations
    'Nu Bank': 'Nubank',
    
    # DocuSign variations
    'Docusign': 'DocuSign',
    
    # Wayfair variations
    'wayfair': 'Wayfair',
    
    # T-Mobile variations
    'T-mobile': 'T-Mobile',
    'TMobile': 'T-Mobile',
    
    # Lyft variations
    'lyft': 'Lyft',
    
    # 7Shifts variations
    '7shifts': '7Shifts',
    
    # Oscar Health variations
    'Oscar Health': 'Oscar Health',
    
    # NA / Test / Invalid entries
    'NA': 'Other',
    'Na': 'Other',
    'Test': 'Other',
    '-': 'Other',
    '<>': 'Other',
}

# ============================================================================
# QUESTION CATEGORY MAPPING
# ============================================================================
def categorize_question(question_type):
    """
    Categorize question type into one of 7 standard buckets.
    """
    if not question_type:
        return 'Other'
    
    qt = question_type.strip().lower()
    
    # Product Design - designing new products or features
    product_design_keywords = [
        'product sense', 'product design', 'sense', 'design',
        'produce sense', 'product improvement', 'product',
    ]
    
    # Product Strategy - vision, roadmaps, market entry
    strategy_keywords = [
        'strategy', 'product strategy', 'roadmap', 'market',
        'go-to-market', 'gtm', 'vision',
    ]
    
    # Execution & Metrics - goals, KPIs, analytics, trade-offs
    execution_keywords = [
        'execution', 'product execution', 'metrics', 'analytics',
        'analytical', 'analytical thinking', 'product analytics',
        'product analytical', 'tradeoff', 'trade-off', 'prioritization',
        'product prioritization', 'product metrics', 'goal',
        'product retrospective', 'product values',
    ]
    
    # Estimation & Pricing
    estimation_keywords = [
        'estimation', 'estimate', 'pricing', 'market sizing',
    ]
    
    # Technical - system design, API, technical questions
    technical_keywords = [
        'technical', 'system design', 'api', 'engineering',
    ]
    
    # Behavioral - leadership, interpersonal
    behavioral_keywords = [
        'behavioral', 'behaviour', 'behavioural', 'behav', 'behavior',
        'leadership', 'leadership & drive', 'leadership and drive',
    ]
    
    # Check categories in priority order
    # Technical first (to catch system design before generic design)
    for kw in technical_keywords:
        if kw in qt:
            return 'Technical'
    
    # Behavioral
    for kw in behavioral_keywords:
        if kw in qt:
            return 'Behavioral'
    
    # Estimation & Pricing
    for kw in estimation_keywords:
        if kw in qt:
            return 'Estimation & Pricing'
    
    # Execution & Metrics (check before strategy due to overlap)
    for kw in execution_keywords:
        if kw in qt:
            return 'Execution & Metrics'
    
    # Product Strategy
    for kw in strategy_keywords:
        if kw in qt:
            return 'Product Strategy'
    
    # Product Design (most common, check last as catch-all for product-related)
    for kw in product_design_keywords:
        if kw in qt:
            return 'Product Design'
    
    # Default
    return 'Other'


def normalize_company(company_name):
    """
    Normalize company name using the mapping dictionary.
    If not in mapping, return original name with proper title case.
    """
    if not company_name:
        return 'Unknown'
    
    company_name = company_name.strip()
    
    # Check if in normalization mapping
    if company_name in COMPANY_NORMALIZATION:
        return COMPANY_NORMALIZATION[company_name]
    
    # Return as-is (already normalized)
    return company_name


def main():
    input_file = 'PM Interview Questions.csv'
    output_file = 'PM_Interview_Questions_Cleaned.csv'
    
    rows_processed = 0
    rows_written = 0
    
    # Read and process
    with open(input_file, 'r', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        header = next(reader)
        
        # Add new columns
        new_header = header[:7] + ['Company_Normalized', 'Question_Category']
        
        all_rows = []
        
        for row in reader:
            rows_processed += 1
            
            # Skip empty rows
            if len(row) < 4:
                continue
            
            # Extract relevant columns
            timestamp = row[0] if len(row) > 0 else ''
            company = row[1] if len(row) > 1 else ''
            question = row[2] if len(row) > 2 else ''
            question_type = row[3] if len(row) > 3 else ''
            interview_type = row[4] if len(row) > 4 else ''
            comments = row[5] if len(row) > 5 else ''
            job_title = row[6] if len(row) > 6 else ''
            
            # Normalize company and categorize question
            company_normalized = normalize_company(company)
            question_category = categorize_question(question_type)
            
            # Build output row
            output_row = [
                timestamp, company, question, question_type, 
                interview_type, comments, job_title,
                company_normalized, question_category
            ]
            
            all_rows.append(output_row)
            rows_written += 1
    
    # Write output
    with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
        writer = csv.writer(outfile)
        writer.writerow(new_header)
        writer.writerows(all_rows)
    
    print(f"✅ Processing complete!")
    print(f"   Rows processed: {rows_processed}")
    print(f"   Rows written: {rows_written}")
    print(f"   Output file: {output_file}")
    
    # Print summary statistics
    print("\n📊 Summary Statistics:")
    
    # Company distribution
    company_counts = Counter(row[7] for row in all_rows)
    print(f"\n   Unique normalized companies: {len(company_counts)}")
    print("   Top 15 companies:")
    for company, count in company_counts.most_common(15):
        print(f"      {count:4d} | {company}")
    
    # Category distribution
    category_counts = Counter(row[8] for row in all_rows)
    print(f"\n   Question categories ({len(category_counts)}):")
    for category, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        print(f"      {count:4d} | {category}")


if __name__ == '__main__':
    main()
