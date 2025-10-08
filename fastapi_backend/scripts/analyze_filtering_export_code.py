#!/usr/bin/env python3
"""
Analyze Filtering and Export Systems Code
Static analysis of the filtering and export functionality
"""

import logging
from pathlib import Path
import re
import ast
import sys
import os
sys.path.append('.')


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CodeAnalyzer:
    def __init__(self):
        self.issues = []
        self.recommendations = []

    def analyze_filtering_system(self):
        """Analyze the filtering system code"""
        print("\n🔍 ANALYZING FILTERING SYSTEM")
        print("=" * 50)

        # Check park_management.py filtering endpoints
        park_mgmt_file = "api/park_management.py"
        if os.path.exists(park_mgmt_file):
            with open(park_mgmt_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for filtering endpoints
            filtering_endpoints = [
                ("get_parks", "Basic filtering endpoint"),
                ("get_saved_park_data", "Advanced filtering with pagination"),
                ("get_filtered_parks", "Advanced filtering with multiple filters")
            ]

            for func_name, description in filtering_endpoints:
                if f"def {func_name}" in content:
                    print(f"✅ Found {description}: {func_name}")
                else:
                    print(f"❌ Missing {description}: {func_name}")
                    self.issues.append(
                        f"Missing filtering endpoint: {func_name}")

            # Check for performance issues
            performance_issues = []

            # Check for missing indexes in queries
            if "query.filter(" in content and "query.count()" in content:
                print("⚠️  Potential performance issue: Using count() after filters")
                performance_issues.append(
                    "Consider using separate count query for better performance")

            # Check for N+1 query problems
            if "query.offset(" in content and "query.limit(" in content:
                print("✅ Pagination implemented correctly")

            # Check for missing error handling
            if "try:" in content and "except" in content:
                print("✅ Error handling present")
            else:
                print("⚠️  Missing error handling in filtering endpoints")
                self.issues.append(
                    "Missing error handling in filtering endpoints")

            # Check for DOT-based permissions
            if "DOTService.get_user_accessible_dots" in content:
                print("✅ DOT-based permission filtering implemented")
            else:
                print("❌ Missing DOT-based permission filtering")
                self.issues.append("Missing DOT-based permission filtering")

        # Check park_analytics.py filtering
        analytics_file = "api/park_analytics.py"
        if os.path.exists(analytics_file):
            with open(analytics_file, 'r', encoding='utf-8') as f:
                content = f.read()

            if "get_available_filters" in content:
                print("✅ Filter options endpoint available")
            else:
                print("❌ Missing filter options endpoint")
                self.issues.append("Missing filter options endpoint")

    def analyze_export_system(self):
        """Analyze the export system code"""
        print("\n📊 ANALYZING EXPORT SYSTEM")
        print("=" * 50)

        # Check park_analytics.py export endpoint
        analytics_file = "api/park_analytics.py"
        if os.path.exists(analytics_file):
            with open(analytics_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for export endpoint
            if "def export_data" in content:
                print("✅ Export endpoint found")

                # Check export functionality
                export_checks = [
                    ("format.*csv.*excel", "Multiple format support"),
                    ("limit.*10000", "Export limit protection"),
                    ("DOTService.get_user_accessible_dots", "Permission filtering"),
                    ("HTTPException.*404", "No data error handling")
                ]

                for pattern, description in export_checks:
                    if re.search(pattern, content):
                        print(f"✅ {description} implemented")
                    else:
                        print(f"⚠️  {description} missing or incomplete")
                        self.issues.append(f"Export system: {description}")

                # Check for performance issues
                if "query.limit(10000)" in content:
                    print("✅ Export limit protection (10,000 records)")
                else:
                    print("⚠️  No export limit protection")
                    self.issues.append("Export system: No limit protection")

                # Check data structure
                if "export_data.append({" in content:
                    print("✅ Proper data structure for export")
                else:
                    print("⚠️  Export data structure needs review")
                    self.issues.append("Export system: Data structure issues")
            else:
                print("❌ Export endpoint not found")
                self.issues.append("Missing export endpoint")

    def analyze_frontend_integration(self):
        """Analyze frontend integration"""
        print("\n🌐 ANALYZING FRONTEND INTEGRATION")
        print("=" * 50)

        # Check API service file
        api_service_file = "../frontend/src/services/api.js"
        if os.path.exists(api_service_file):
            with open(api_service_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for filtering API calls
            filtering_apis = [
                ("getParkDataSavedData", "Park data filtering API"),
                ("getParkAnalyticsAvailableFilters", "Filter options API"),
                ("exportParkAnalyticsData", "Export API")
            ]

            for func_name, description in filtering_apis:
                if f"export const {func_name}" in content:
                    print(f"✅ {description} available")
                else:
                    print(f"❌ {description} missing")
                    self.issues.append(f"Frontend: Missing {description}")

        # Check frontend components
        frontend_components = [
            "../frontend/src/pages/EncaissementPage/index.jsx",
            "../frontend/src/pages/FilePreviewPage/index.jsx"
        ]

        for component_file in frontend_components:
            if os.path.exists(component_file):
                with open(component_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                component_name = os.path.basename(component_file)

                # Check for filtering functionality
                if "useState.*filter" in content or "setFilters" in content:
                    print(f"✅ {component_name}: Filtering state management")
                else:
                    print(
                        f"⚠️  {component_name}: Filtering state management needs review")

                # Check for export functionality
                if "export" in content.lower() and "download" in content.lower():
                    print(f"✅ {component_name}: Export functionality")
                else:
                    print(
                        f"⚠️  {component_name}: Export functionality needs review")

    def check_database_indexes(self):
        """Check if proper database indexes exist for filtering"""
        print("\n🗄️  CHECKING DATABASE INDEXES")
        print("=" * 50)

        # Check if index creation script exists
        index_script = "scripts/create_kpi_indexes.sql"
        if os.path.exists(index_script):
            with open(index_script, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for filtering-related indexes
            filtering_indexes = [
                ("idx_parks_subscriber_status", "Subscriber status filtering"),
                ("idx_parks_telecom_type", "Telecom type filtering"),
                ("idx_parks_customer_l2", "Customer L2 filtering"),
                ("idx_parks_customer_l3", "Customer L3 filtering"),
                ("idx_parks_dot_id", "DOT filtering")
            ]

            for index_name, description in filtering_indexes:
                if index_name in content:
                    print(f"✅ {description} index: {index_name}")
                else:
                    print(f"❌ {description} index missing: {index_name}")
                    self.issues.append(f"Missing database index: {index_name}")
        else:
            print("❌ Database index script not found")
            self.issues.append("Missing database index creation script")

    def generate_recommendations(self):
        """Generate recommendations for improvements"""
        print("\n💡 RECOMMENDATIONS")
        print("=" * 50)

        recommendations = [
            "1. Add database indexes for all filtering columns",
            "2. Implement query result caching for frequently accessed filters",
            "3. Add export progress tracking for large datasets",
            "4. Implement export format validation",
            "5. Add rate limiting for export endpoints",
            "6. Implement export job queue for large datasets",
            "7. Add export history and audit logging",
            "8. Implement client-side filtering for better UX",
            "9. Add export data validation and sanitization",
            "10. Implement export compression for large files"
        ]

        for rec in recommendations:
            print(f"💡 {rec}")
            self.recommendations.append(rec)

    def generate_report(self):
        """Generate analysis report"""
        print("\n📋 ANALYSIS REPORT")
        print("=" * 50)

        print(f"Total Issues Found: {len(self.issues)}")
        print(f"Total Recommendations: {len(self.recommendations)}")

        if self.issues:
            print("\n🚨 Issues Found:")
            for i, issue in enumerate(self.issues, 1):
                print(f"{i}. {issue}")

        if self.recommendations:
            print("\n💡 Recommendations:")
            for i, rec in enumerate(self.recommendations, 1):
                print(f"{i}. {rec}")

        # Save report
        report_content = f"""
# Filtering & Export Systems Analysis Report

## Summary
- Total Issues: {len(self.issues)}
- Total Recommendations: {len(self.recommendations)}

## Issues Found
{chr(10).join(f"- {issue}" for issue in self.issues) if self.issues else "No issues found"}

## Recommendations
{chr(10).join(f"- {rec}" for rec in self.recommendations) if self.recommendations else "No recommendations"}

## Next Steps
1. Address critical issues first
2. Implement performance optimizations
3. Add proper error handling
4. Implement caching strategies
5. Add comprehensive testing
"""

        with open("filtering_export_analysis_report.md", "w", encoding='utf-8') as f:
            f.write(report_content)

        print(f"\n📄 Detailed report saved to: filtering_export_analysis_report.md")


def main():
    """Main analysis function"""
    print("🔍 FILTERING & EXPORT SYSTEMS CODE ANALYSIS")
    print("=" * 50)

    analyzer = CodeAnalyzer()

    # Run analyses
    analyzer.analyze_filtering_system()
    analyzer.analyze_export_system()
    analyzer.analyze_frontend_integration()
    analyzer.check_database_indexes()
    analyzer.generate_recommendations()
    analyzer.generate_report()

    print("\n✅ Analysis complete!")


if __name__ == "__main__":
    main()
