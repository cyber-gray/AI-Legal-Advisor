from typing import Dict, List, Optional
from datetime import datetime
import json
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ResourceNotFoundError

class DocumentAnalyzer:
    """Handles document analysis using Azure Document Intelligence and maintains analysis history."""
    
    def __init__(self, endpoint: str, key: str):
        """Initialize the document analyzer with Azure credentials."""
        self.client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))
        self.analysis_history = []
        self.current_document = None

    async def analyze_document(self, document_url: str) -> Dict:
        """Analyze a document and extract its content and key points."""
        try:
            # Create analyze request with URL source
            analyze_request = AnalyzeDocumentRequest(url_source=document_url)
            
            # Start document analysis
            poller = self.client.begin_analyze_document(
                model_id="prebuilt-layout",  # Using the layout model to extract structure
                body=analyze_request
            )
            result = poller.result()

            # Create analysis result
            analysis_result = {
                "timestamp": datetime.now().isoformat(),
                "url": document_url,
                "analysis_result": {
                    "content": result.content,
                    "key_points": self._extract_key_points(result),
                    "sections": self._extract_sections(result),
                    "tables": self._extract_tables(result)
                }
            }

            # Update current document and history
            self.current_document = analysis_result
            self.analysis_history.append(analysis_result)

            return analysis_result

        except ResourceNotFoundError:
            return {"error": "Document not found or inaccessible"}
        except Exception as e:
            return {"error": str(e)}

    def _extract_key_points(self, result) -> List[Dict]:
        """Extract key points from the document analysis result.
        Currently focuses on summary and key sections."""
        key_points = []
        if hasattr(result, 'paragraphs'):
            in_summary = False
            summary_content = []
            
            for paragraph in result.paragraphs:
                text = paragraph.content.strip()
                
                # Check if this is a summary section
                if text.upper() == "SUMMARY":
                    in_summary = True
                    key_points.append({
                        "text": text,
                        "type": "summary_header"
                    })
                # If we're in a summary section, collect the content
                elif in_summary and text and not text.upper() == "SOMMAIRE":
                    summary_content.append(text)
                # Exit summary section when we hit SOMMAIRE
                elif text.upper() == "SOMMAIRE":
                    in_summary = False
                    # Add collected summary as a key point
                    if summary_content:
                        key_points.append({
                            "text": " ".join(summary_content),
                            "type": "summary_content"
                        })
                    summary_content = []
            
            # Add any remaining summary content
            if summary_content:
                key_points.append({
                    "text": " ".join(summary_content),
                    "type": "summary_content"
                })
                
        return key_points

    def _extract_sections(self, result) -> List[Dict]:
        """Extract main document sections."""
        sections = []
        if hasattr(result, 'paragraphs'):
            current_section = None
            section_content = []
            
            for paragraph in result.paragraphs:
                text = paragraph.content.strip()
                # Check if this is a section header (simple heuristic)
                if text.isupper() and len(text) < 100:  # Likely a header
                    if current_section:
                        sections.append({
                            "heading": current_section,
                            "content": "\n".join(section_content)
                        })
                    current_section = text
                    section_content = []
                elif current_section:
                    section_content.append(text)
            
            # Add the last section
            if current_section:
                sections.append({
                    "heading": current_section,
                    "content": "\n".join(section_content)
                })
        
        return sections

    def _extract_tables(self, result) -> List[Dict]:
        """Extract tables with basic structure verification."""
        tables = []
        if hasattr(result, 'tables'):
            for idx, table in enumerate(result.tables):
                try:
                    table_data = []
                    if table.row_count and table.column_count:  # Verify table has structure
                        for row in range(table.row_count):
                            row_data = []
                            for col in range(table.column_count):
                                cell_idx = row * table.column_count + col
                                if cell_idx < len(table.cells):  # Boundary check
                                    cell = table.cells[cell_idx]
                                    row_data.append(cell.content if cell.content else "")
                                else:
                                    row_data.append("")  # Empty cell for missing data
                            table_data.append(row_data)
                        
                        tables.append({
                            "id": f"table_{idx + 1}",
                            "rows": table_data,
                            "row_count": table.row_count,
                            "column_count": table.column_count
                        })
                except Exception as e:
                    # Log error but continue processing other tables
                    print(f"Error processing table {idx}: {str(e)}")
                    continue
        
        return tables

    def save_analysis_history(self, filepath: str) -> None:
        """Save the analysis history to a JSON file."""
        with open(filepath, 'w') as f:
            json.dump({
                "current_document": self.current_document,
                "analysis_history": self.analysis_history
            }, f, indent=2)

    def load_analysis_history(self, filepath: str) -> None:
        """Load analysis history from a JSON file."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                self.current_document = data.get("current_document")
                self.analysis_history = data.get("analysis_history", [])
        except FileNotFoundError:
            print(f"No analysis history found at {filepath}")
        except json.JSONDecodeError:
            print(f"Error reading analysis history from {filepath}: Invalid JSON format")
        except Exception as e:
            print(f"Error loading analysis history: {str(e)}")