#!/bin/bash
# Quick test script to verify filters via API calls

echo "🔍 Testing Revenue Filters via API"
echo "=================================="

BASE_URL="http://localhost:8001"
TOKEN=$(curl -s -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' | jq -r '.access_token')

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
  echo "❌ Failed to get token"
  exit 1
fi

echo "✅ Got token"

echo ""
echo "Test 1: DOT Filter (org_name)"
echo "-----------------------------"
curl -s -X GET "$BASE_URL/api/revenue/overview?org_name=ALGER%20CENTRE" \
  -H "Authorization: Bearer $TOKEN" | jq '{total_revenue, total_records, by_org_name: (.by_org_name | keys | length)}'

echo ""
echo "Test 2: Type Fact Filter (typ_fact)"
echo "------------------------------------"
curl -s -X GET "$BASE_URL/api/revenue/overview?typ_fact=A" \
  -H "Authorization: Bearer $TOKEN" | jq '{total_revenue, total_records}'

echo ""
echo "Test 3: Compte Comptable Filter (cpt_comptable)"
echo "------------------------------------------------"
curl -s -X GET "$BASE_URL/api/revenue/overview?cpt_comptable=7048000000" \
  -H "Authorization: Bearer $TOKEN" | jq '{total_revenue, total_records}'

echo ""
echo "Test 4: Date GL Filter (start_date, end_date)"
echo "---------------------------------------------"
curl -s -X GET "$BASE_URL/api/revenue/overview?start_date=2025-01-01&end_date=2025-03-31" \
  -H "Authorization: Bearer $TOKEN" | jq '{total_revenue, total_records, by_month: (.by_month | keys)}'

echo ""
echo "✅ All filter tests completed!"
