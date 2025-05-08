import os
import asyncio
from dotenv import load_dotenv
from document_analyzer import DocumentAnalyzer
import unittest
from unittest.mock import Mock, patch
import json
from datetime import datetime

# Load environment variables
load_dotenv()

async def main():
    # Initialize document analyzer with correct environment variable names
    analyzer = DocumentAnalyzer(
        endpoint=os.getenv("DOCUMENT_INTELLIGENCE_ENDPOINT"),
        key=os.getenv("DOCUMENT_INTELLIGENCE_KEY")
    )
    
    # Test document URL (Bill C-27)
    document_url = "https://www.parl.ca/Content/Bills/441/Government/C-27/C-27_1/C-27_1.PDF"
    
    print("Analyzing document...")
    result = await analyzer.analyze_document(document_url)
    
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print("\nDocument Analysis Results:")
        print(f"Timestamp: {result['timestamp']}")
        print(f"\nKey Points Found: {len(result['analysis_result']['key_points'])}")
        print(f"Sections Found: {len(result['analysis_result']['sections'])}")
        print(f"Tables Found: {len(result['analysis_result']['tables'])}")
        
        # Print first few key points if any
        if result['analysis_result']['key_points']:
            print("\nSample Key Points:")
            for point in result['analysis_result']['key_points'][:3]:
                print(f"- {point['text'][:200]}...")
        
        # Save the analysis results
        analyzer.save_analysis_history("legal_document_analysis.json")
        print("\nAnalysis results saved to legal_document_analysis.json")

if __name__ == "__main__":
    asyncio.run(main())

class TestDocumentAnalyzer(unittest.TestCase):
    @patch('document_analyzer.DocumentIntelligenceClient')
    def setUp(self, mock_client):
        """Set up test cases."""
        self.endpoint = "mock_endpoint"
        self.key = "mock_key"
        self.analyzer = DocumentAnalyzer(self.endpoint, self.key)
        
        # Mock the Azure client
        mock_client.return_value.begin_analyze_document.return_value = Mock()
        
        self.test_document = {
            "url": "test_url",
            "timestamp": "2025-05-06T14:25:24.390855",
            "analysis_result": {
                "content": """
                Regarding Privacy Protection
                Organizations must protect personal information
                Data breaches must be reported
                
                Concerning AI Systems
                High-impact systems require risk mitigation
                Bias must be monitored and addressed
                """,
                "sections": [
                    {
                        "heading": "Privacy Section",
                        "content": "This section refers to AI Systems section below."
                    },
                    {
                        "heading": "AI Systems",
                        "content": "AI systems must comply with privacy requirements."
                    }
                ]
            }
        }
        self.analyzer.current_document = self.test_document
        
    def test_theme_extraction(self):
        """Test that themes are correctly extracted from document content"""
        result = self.analyzer.analyze_document_content()
        themes = result["key_themes"]
        
        self.assertTrue(any(t["theme"].strip() == "Privacy Protection" for t in themes))
        self.assertTrue(any(t["theme"].strip() == "AI Systems" for t in themes))
        
    def test_cross_references(self):
        """Test that cross-references between sections are identified"""
        result = self.analyzer.analyze_document_content()
        refs = result["cross_references"]
        
        self.assertTrue(any(
            ref["from_section"] == "Privacy Section" and 
            ref["to_section"] == "AI Systems" 
            for ref in refs
        ))
        
    def test_semantic_analysis(self):
        """Test complete semantic analysis functionality"""
        result = self.analyzer.analyze_document_content()
        
        self.assertIn("key_themes", result)
        self.assertIn("semantic_structure", result)
        self.assertIn("cross_references", result)
        self.assertIn("definitions", result)
        
        # Verify semantic structure analysis
        structure = result["semantic_structure"]
        self.assertIn("hierarchical_sections", structure)
        self.assertIn("section_relationships", structure)
        self.assertIn("section_types", structure)

if __name__ == '__main__':
    unittest.main()