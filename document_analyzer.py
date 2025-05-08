from typing import Dict, List, Optional
from datetime import datetime
import json
import logging
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ResourceNotFoundError, ServiceRequestError

class DocumentAnalyzer:
    """Handles document analysis using Azure Document Intelligence and maintains analysis history."""
    
    def __init__(self, endpoint: str, key: str):
        """Initialize the document analyzer with Azure credentials."""
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(handler)
        
        try:
            self.client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))
            self.analysis_history = []
            self.current_document = None
            self.languages = []
            self.logger.info("Document analyzer initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize document analyzer: {str(e)}")
            raise

    def _handle_error(self, error: Exception, context: str) -> Dict:
        """Handle errors consistently throughout the analyzer."""
        error_msg = f"Error in {context}: {str(error)}"
        self.logger.error(error_msg)
        
        if isinstance(error, ResourceNotFoundError):
            return {"error": "Document not found or inaccessible", "error_type": "not_found"}
        elif isinstance(error, ServiceRequestError):
            return {"error": "Service request failed", "error_type": "service_error"}
        else:
            return {"error": error_msg, "error_type": "general_error"}

    async def analyze_document(self, document_url: str) -> Dict:
        """Analyze a document and extract its content and key points."""
        self.logger.info(f"Starting analysis of document: {document_url}")
        try:
            # Create analyze request with URL source
            analyze_request = AnalyzeDocumentRequest(url_source=document_url)
            
            # Start document analysis with language detection
            poller = self.client.begin_analyze_document(
                model_id="prebuilt-layout",
                body=analyze_request
            )
            result = poller.result()

            # Detect languages in the document
            self.languages = self._detect_languages(result)
            self.logger.info(f"Detected languages: {self.languages}")

            # Create analysis result
            analysis_result = {
                "timestamp": datetime.now().isoformat(),
                "url": document_url,
                "analysis_result": {
                    "content": result.content,
                    "languages": self.languages,
                    "key_points": self._extract_key_points(result),
                    "sections": self._extract_sections(result),
                    "tables": self._extract_tables(result)
                }
            }

            # Update current document and history
            self.current_document = analysis_result
            self.analysis_history.append(analysis_result)
            self.logger.info("Document analysis completed successfully")

            return analysis_result

        except Exception as e:
            return self._handle_error(e, "document analysis")

    def _detect_languages(self, result) -> List[Dict[str, str]]:
        """Detect languages present in the document."""
        detected_languages = []
        if hasattr(result, 'languages'):
            for lang in result.languages:
                detected_languages.append({
                    "language": lang.locale,
                    "confidence": lang.confidence
                })
        return detected_languages

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

    def save_analysis_history(self, filepath: str) -> Dict:
        """Save the analysis history to a JSON file."""
        try:
            with open(filepath, 'w') as f:
                json.dump({
                    "current_document": self.current_document,
                    "analysis_history": self.analysis_history
                }, f, indent=2)
            self.logger.info(f"Analysis history saved to {filepath}")
            return {"success": True, "message": "Analysis history saved successfully"}
        except Exception as e:
            return self._handle_error(e, "saving analysis history")

    def load_analysis_history(self, filepath: str) -> Dict:
        """Load analysis history from a JSON file."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                self.current_document = data.get("current_document")
                self.analysis_history = data.get("analysis_history", [])
            self.logger.info(f"Analysis history loaded from {filepath}")
            return {"success": True, "message": "Analysis history loaded successfully"}
        except FileNotFoundError:
            return {"error": f"No analysis history found at {filepath}", "error_type": "not_found"}
        except json.JSONDecodeError:
            return {"error": f"Invalid JSON format in {filepath}", "error_type": "format_error"}
        except Exception as e:
            return self._handle_error(e, "loading analysis history")

    def compare_documents(self, doc1_url: str, doc2_url: str) -> Dict:
        """Compare two documents and identify similarities and differences."""
        try:
            # Get analysis results for both documents
            doc1_analysis = self.current_document if self.current_document and self.current_document['url'] == doc1_url else \
                          next((doc for doc in self.analysis_history if doc['url'] == doc1_url), None)
            doc2_analysis = next((doc for doc in self.analysis_history if doc['url'] == doc2_url), None)

            # If either document hasn't been analyzed yet, return error
            if not doc1_analysis or not doc2_analysis:
                return {"error": "One or both documents have not been analyzed yet"}

            comparison_result = {
                "timestamp": datetime.now().isoformat(),
                "document1": doc1_url,
                "document2": doc2_url,
                "common_sections": [],
                "unique_sections": {
                    "document1": [],
                    "document2": []
                },
                "language_comparison": self._compare_languages(
                    doc1_analysis['analysis_result'].get('languages', []),
                    doc2_analysis['analysis_result'].get('languages', [])
                )
            }

            # Compare sections
            sections1 = {s['heading']: s['content'] for s in doc1_analysis['analysis_result']['sections']}
            sections2 = {s['heading']: s['content'] for s in doc2_analysis['analysis_result']['sections']}

            # Find common and unique sections
            common_headers = set(sections1.keys()) & set(sections2.keys())
            unique_to_doc1 = set(sections1.keys()) - set(sections2.keys())
            unique_to_doc2 = set(sections2.keys()) - set(sections1.keys())

            for header in common_headers:
                comparison_result['common_sections'].append({
                    'heading': header,
                    'similarity_score': self._calculate_text_similarity(sections1[header], sections2[header])
                })

            comparison_result['unique_sections']['document1'] = list(unique_to_doc1)
            comparison_result['unique_sections']['document2'] = list(unique_to_doc2)

            return comparison_result

        except Exception as e:
            return self._handle_error(e, "document comparison")

    def _compare_languages(self, langs1: List[Dict], langs2: List[Dict]) -> Dict:
        """Compare detected languages between two documents."""
        return {
            "common_languages": [l1['language'] for l1 in langs1 if any(l2['language'] == l1['language'] for l2 in langs2)],
            "unique_to_first": [l1['language'] for l1 in langs1 if not any(l2['language'] == l1['language'] for l2 in langs2)],
            "unique_to_second": [l2['language'] for l2 in langs2 if not any(l1['language'] == l2['language'] for l1 in langs1)]
        }

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity score between two text sections using simple token overlap."""
        tokens1 = set(text1.lower().split())
        tokens2 = set(text2.lower().split())
        
        if not tokens1 or not tokens2:
            return 0.0
            
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        
        return len(intersection) / len(union)  # Jaccard similarity

    def analyze_document_content(self, document_url: str = None) -> Dict:
        """Perform deeper semantic analysis of the current document or a specific one."""
        try:
            # Use current document if no URL provided
            doc = self.current_document if document_url is None else next(
                (doc for doc in self.analysis_history if doc["url"] == document_url),
                None
            )
            
            if not doc:
                return self._handle_error(ValueError("Document not found"), "analyze_document_content")
            
            content = doc["analysis_result"].get("content", "")
            sections = doc["analysis_result"].get("sections", [])
            
            return {
                "key_themes": self._extract_themes(content),
                "semantic_structure": self._analyze_semantic_structure(sections),
                "cross_references": self._find_cross_references(sections),
                "definitions": self._extract_definitions('\n'.join(s.get("content", "") for s in sections))
            }
            
        except Exception as e:
            return self._handle_error(e, "analyze_document_content")

    def _extract_themes(self, content: str) -> List[Dict]:
        """Extract key themes from document content."""
        themes = []
        if not content:
            return themes
            
        # Split content into paragraphs and clean them
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        for para in paragraphs:
            lines = [l.strip() for l in para.split('\n') if l.strip()]
            if not lines:
                continue
                
            # Process each line that starts with a theme indicator
            for line in lines:
                if line.startswith(("Regarding", "Concerning")):
                    # Extract theme by removing the prefix
                    theme = line
                    for prefix in ("Regarding", "Concerning"):
                        if theme.startswith(prefix):
                            theme = theme[len(prefix):].strip()
                            break
                    
                    # Get supporting points from subsequent lines
                    line_idx = lines.index(line)
                    supporting_points = []
                    
                    # Collect supporting points until we hit another theme or end of paragraph
                    for next_line in lines[line_idx + 1:]:
                        if next_line.startswith(("Regarding", "Concerning")):
                            break
                        supporting_points.append(next_line)
                    
                    themes.append({
                        "theme": theme,
                        "supporting_points": supporting_points,
                        "confidence": 0.8
                    })
                
        return themes

    def _analyze_semantic_structure(self, sections: List[Dict]) -> Dict:
        """Analyze the semantic structure of document sections."""
        if not sections:
            return {
                "hierarchical_sections": [],
                "section_relationships": [],
                "section_types": {}
            }
            
        structure = {
            "hierarchical_sections": [],
            "section_relationships": [],
            "section_types": {}
        }
        
        for section in sections:
            if not isinstance(section, dict) or "heading" not in section or "content" not in section:
                continue
                
            heading = section["heading"]
            content = section["content"]
            
            # Determine section type
            section_type = self._determine_section_type(heading, content)
            
            # Add to hierarchical structure
            section_info = {
                "heading": heading,
                "level": 0,  # Default to top level
                "type": section_type,
                "subsections": []
            }
            
            structure["hierarchical_sections"].append(section_info)
            
            # Track section types
            if section_type not in structure["section_types"]:
                structure["section_types"][section_type] = []
            structure["section_types"][section_type].append(heading)
            
        return structure

    def _determine_section_type(self, heading: str, content: str) -> str:
        """Determine the type of a section based on its heading and content."""
        heading_lower = heading.lower() if heading else ""
        
        if any(term in heading_lower for term in ["summary", "sommaire"]):
            return "summary"
        elif any(term in heading_lower for term in ["définition", "definition", "interpretation"]):
            return "definitions"
        elif "ai" in heading_lower or "privacy" in heading_lower:
            return "topic_section"
        else:
            return "content"

    def _find_cross_references(self, sections: List[Dict]) -> List[Dict]:
        """Identify cross-references between document sections."""
        references = []
        if not sections:
            return references
            
        section_headings = {s.get("heading", "") for s in sections if s.get("heading")}
        
        for section in sections:
            heading = section.get("heading")
            content = section.get("content", "")
            
            if not heading or not content:
                continue
                
            for other_heading in section_headings:
                if other_heading and other_heading in content and other_heading != heading:
                    references.append({
                        "from_section": heading,
                        "to_section": other_heading,
                        "context": content[:100]  # First 100 chars for context
                    })
        
        return references

    def _extract_definitions(self, content: str) -> List[Dict]:
        """Extract defined terms and their definitions from the document."""
        definitions = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            # Look for common definition patterns
            if '"' in line and ('means' in line.lower() or 'définit' in line.lower()):
                try:
                    term = line[line.index('"'):line.rindex('"')+1]
                    definition = line[line.rindex('"')+1:].trip()
                    if definition.startswith('means') or definition.startswith('définit'):
                        definitions.append({
                            "term": term.strip('"'),
                            "definition": definition.strip(),
                            "language": "en" if "means" in definition.lower() else "fr"
                        })
                except ValueError:
                    continue
        
        return definitions