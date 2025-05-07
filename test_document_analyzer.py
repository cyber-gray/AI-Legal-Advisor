import os
import asyncio
from dotenv import load_dotenv
from document_analyzer import DocumentAnalyzer

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