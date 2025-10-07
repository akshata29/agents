"""Export Service for Deep Research Application.

This service handles exporting research reports to various formats:
- Markdown (formatted)
- PDF (using ReportLab)
- HTML (with embedded CSS)
"""

import os
import asyncio
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import structlog
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.colors import HexColor
import markdown

logger = structlog.get_logger(__name__)


class ExportService:
    """Service for exporting research reports to various formats."""
    
    def __init__(self, export_dir: Optional[Path] = None):
        """Initialize export service.
        
        Args:
            export_dir: Directory for temporary export files
        """
        self.export_dir = export_dir or Path(tempfile.gettempdir()) / "deep_research_exports"
        self.export_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Export service initialized", export_dir=str(self.export_dir))
    
    async def export_markdown(
        self,
        report_content: str,
        title: str,
        export_id: str,
        include_metadata: bool = True
    ) -> str:
        """Export research report as Markdown.
        
        Args:
            report_content: The markdown content of the report
            title: Report title
            export_id: Export task identifier
            include_metadata: Whether to include report metadata
            
        Returns:
            Path to the generated Markdown file
        """
        try:
            logger.info("Exporting report as Markdown", export_id=export_id, title=title)
            
            # Prepare markdown content
            lines = []
            
            if include_metadata:
                lines.append(f"# {title}\n")
                lines.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
                lines.append(f"**Export ID**: {export_id}\n")
                lines.append("\n---\n\n")
            
            lines.append(report_content)
            
            markdown_content = "\n".join(lines)
            
            # Save to file
            file_path = self.export_dir / f"report_{export_id}.md"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            logger.info("Markdown export completed", export_id=export_id, file_path=str(file_path))
            return str(file_path)
            
        except Exception as e:
            logger.error("Markdown export failed", export_id=export_id, error=str(e), exc_info=True)
            raise
    
    async def export_pdf(
        self,
        report_content: str,
        title: str,
        export_id: str,
        include_metadata: bool = True
    ) -> str:
        """Export research report as PDF.
        
        Args:
            report_content: The markdown content of the report
            title: Report title
            export_id: Export task identifier
            include_metadata: Whether to include report metadata
            
        Returns:
            Path to the generated PDF file
        """
        try:
            logger.info("Exporting report as PDF", export_id=export_id, title=title)
            
            file_path = self.export_dir / f"report_{export_id}.pdf"
            
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._generate_pdf_with_reportlab(
                    report_content, title, str(file_path), include_metadata
                )
            )
            
            logger.info("PDF export completed", export_id=export_id, file_path=str(file_path))
            return str(file_path)
            
        except Exception as e:
            logger.error("PDF export failed", export_id=export_id, error=str(e), exc_info=True)
            raise
    
    async def export_html(
        self,
        report_content: str,
        title: str,
        export_id: str,
        include_metadata: bool = True,
        custom_css: Optional[str] = None
    ) -> str:
        """Export research report as HTML.
        
        Args:
            report_content: The markdown content of the report
            title: Report title
            export_id: Export task identifier
            include_metadata: Whether to include report metadata
            custom_css: Custom CSS for styling
            
        Returns:
            Path to the generated HTML file
        """
        try:
            logger.info("Exporting report as HTML", export_id=export_id, title=title)
            
            file_path = self.export_dir / f"report_{export_id}.html"
            
            html_content = await self._generate_html_content(
                report_content, title, include_metadata, custom_css
            )
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info("HTML export completed", export_id=export_id, file_path=str(file_path))
            return str(file_path)
            
        except Exception as e:
            logger.error("HTML export failed", export_id=export_id, error=str(e), exc_info=True)
            raise
    
    def _generate_pdf_with_reportlab(
        self,
        report_content: str,
        title: str,
        file_path: str,
        include_metadata: bool
    ) -> None:
        """Generate PDF using ReportLab from Markdown content."""
        from reportlab.platypus import Table, TableStyle
        from reportlab.lib import colors
        import re
        
        doc = SimpleDocTemplate(file_path, pagesize=A4)
        story = []
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=HexColor('#1a365d'),
            alignment=1  # Center alignment
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=20,
            textColor=HexColor('#2d3748')
        )
        
        subheading_style = ParagraphStyle(
            'CustomSubheading',
            parent=styles['Heading3'],
            fontSize=13,
            spaceAfter=10,
            spaceBefore=15,
            textColor=HexColor('#4a5568'),
            fontName='Helvetica-Bold'
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=10,
            leading=16
        )
        
        bullet_style = ParagraphStyle(
            'BulletStyle',
            parent=styles['Normal'],
            fontSize=11,
            leftIndent=20,
            spaceAfter=6,
            leading=14,
            bulletIndent=10
        )
        
        # Add title
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 12))
        
        # Add metadata
        if include_metadata:
            metadata_text = f"<i>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</i>"
            story.append(Paragraph(metadata_text, body_style))
            story.append(Spacer(1, 20))
        
        # Convert markdown to HTML using the markdown library
        html_content = markdown.markdown(
            report_content,
            extensions=['extra', 'codehilite', 'tables', 'fenced_code']
        )
        
        # Parse HTML and convert to ReportLab elements
        # Split by HTML tags to process sections
        lines = report_content.split('\n')
        current_paragraph = []
        in_list = False
        
        for line in lines:
            line_stripped = line.strip()
            
            if not line_stripped:
                # Empty line - end current paragraph
                if current_paragraph:
                    para_text = ' '.join(current_paragraph)
                    # Clean markdown for display
                    para_text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', para_text)
                    para_text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', para_text)
                    para_text = re.sub(r'`(.+?)`', r'<font face="Courier" size="10">\1</font>', para_text)
                    para_text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<link href="\2">\1</link>', para_text)
                    
                    try:
                        story.append(Paragraph(para_text, body_style))
                        story.append(Spacer(1, 6))
                    except:
                        # If paragraph fails, add as plain text
                        story.append(Paragraph(para_text.replace('<', '&lt;').replace('>', '&gt;'), body_style))
                    current_paragraph = []
                if in_list:
                    story.append(Spacer(1, 10))
                    in_list = False
                continue
            
            # Handle headings
            if line_stripped.startswith('# ') and not line_stripped.startswith('## '):
                if current_paragraph:
                    para_text = ' '.join(current_paragraph)
                    story.append(Paragraph(para_text, body_style))
                    current_paragraph = []
                heading_text = line_stripped[2:].strip()
                story.append(Paragraph(heading_text, title_style))
                story.append(Spacer(1, 12))
                continue
            elif line_stripped.startswith('## ') and not line_stripped.startswith('### '):
                if current_paragraph:
                    para_text = ' '.join(current_paragraph)
                    story.append(Paragraph(para_text, body_style))
                    current_paragraph = []
                heading_text = line_stripped[3:].strip()
                story.append(Paragraph(heading_text, heading_style))
                story.append(Spacer(1, 10))
                continue
            elif line_stripped.startswith('### '):
                if current_paragraph:
                    para_text = ' '.join(current_paragraph)
                    story.append(Paragraph(para_text, body_style))
                    current_paragraph = []
                heading_text = line_stripped[4:].strip()
                story.append(Paragraph(heading_text, subheading_style))
                story.append(Spacer(1, 8))
                continue
            
            # Handle bullet points
            if line_stripped.startswith('- ') or line_stripped.startswith('* '):
                if current_paragraph:
                    para_text = ' '.join(current_paragraph)
                    story.append(Paragraph(para_text, body_style))
                    current_paragraph = []
                
                bullet_text = line_stripped[2:].strip()
                # Clean markdown
                bullet_text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', bullet_text)
                bullet_text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', bullet_text)
                bullet_text = re.sub(r'`(.+?)`', r'<font face="Courier" size="10">\1</font>', bullet_text)
                bullet_text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<link href="\2">\1</link>', bullet_text)
                
                try:
                    story.append(Paragraph(f'• {bullet_text}', bullet_style))
                except:
                    story.append(Paragraph(f'• {bullet_text}'.replace('<', '&lt;').replace('>', '&gt;'), bullet_style))
                in_list = True
                continue
            
            # Handle numbered lists
            numbered_match = re.match(r'^(\d+)\.\s+(.+)$', line_stripped)
            if numbered_match:
                if current_paragraph:
                    para_text = ' '.join(current_paragraph)
                    story.append(Paragraph(para_text, body_style))
                    current_paragraph = []
                
                num = numbered_match.group(1)
                bullet_text = numbered_match.group(2).strip()
                # Clean markdown
                bullet_text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', bullet_text)
                bullet_text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', bullet_text)
                bullet_text = re.sub(r'`(.+?)`', r'<font face="Courier" size="10">\1</font>', bullet_text)
                bullet_text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<link href="\2">\1</link>', bullet_text)
                
                try:
                    story.append(Paragraph(f'{num}. {bullet_text}', bullet_style))
                except:
                    story.append(Paragraph(f'{num}. {bullet_text}'.replace('<', '&lt;').replace('>', '&gt;'), bullet_style))
                in_list = True
                continue
            
            # Regular text - accumulate into paragraph
            current_paragraph.append(line_stripped)
        
        # Add any remaining paragraph
        if current_paragraph:
            para_text = ' '.join(current_paragraph)
            para_text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', para_text)
            para_text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', para_text)
            para_text = re.sub(r'`(.+?)`', r'<font face="Courier" size="10">\1</font>', para_text)
            para_text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<link href="\2">\1</link>', para_text)
            
            try:
                story.append(Paragraph(para_text, body_style))
            except:
                story.append(Paragraph(para_text.replace('<', '&lt;').replace('>', '&gt;'), body_style))
        
        # Build PDF
        doc.build(story)
    
    async def _generate_html_content(
        self,
        report_content: str,
        title: str,
        include_metadata: bool,
        custom_css: Optional[str] = None
    ) -> str:
        """Generate HTML content for the report."""
        try:
            # Default CSS
            default_css = """
            <style>
                body { 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; 
                    line-height: 1.6; 
                    margin: 40px auto; 
                    max-width: 900px;
                    padding: 0 20px;
                    color: #333;
                }
                h1 { 
                    color: #1a365d; 
                    border-bottom: 3px solid #3182ce;
                    padding-bottom: 10px; 
                    margin-top: 30px;
                }
                h2 { 
                    color: #2d3748; 
                    border-bottom: 1px solid #cbd5e0;
                    padding-bottom: 5px; 
                    margin-top: 25px;
                }
                h3 { 
                    color: #4a5568; 
                    margin-top: 20px;
                }
                .metadata { 
                    background-color: #f7fafc; 
                    padding: 15px;
                    border-radius: 8px; 
                    margin: 20px 0;
                    border-left: 4px solid #3182ce;
                }
                code {
                    background-color: #edf2f7;
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-family: 'Courier New', monospace;
                }
                pre {
                    background-color: #2d3748;
                    color: #e2e8f0;
                    padding: 15px;
                    border-radius: 8px;
                    overflow-x: auto;
                }
                blockquote {
                    border-left: 4px solid #cbd5e0;
                    padding-left: 20px;
                    margin-left: 0;
                    color: #4a5568;
                    font-style: italic;
                }
                a {
                    color: #3182ce;
                    text-decoration: none;
                }
                a:hover {
                    text-decoration: underline;
                }
                ul, ol {
                    padding-left: 25px;
                }
                li {
                    margin: 8px 0;
                }
            </style>
            """
            
            css = custom_css if custom_css else default_css
            
            html_lines = [
                "<!DOCTYPE html>",
                "<html lang='en'>",
                "<head>",
                "<meta charset='utf-8'>",
                "<meta name='viewport' content='width=device-width, initial-scale=1.0'>",
                f"<title>{title}</title>",
                css,
                "</head>",
                "<body>",
                f"<h1>{title}</h1>"
            ]
            
            # Add metadata if requested
            if include_metadata:
                html_lines.extend([
                    "<div class='metadata'>",
                    "<p><strong>Generated:</strong> " + datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC') + "</p>",
                    "</div>"
                ])
            
            # Convert markdown to HTML
            content_html = markdown.markdown(
                report_content,
                extensions=['fenced_code', 'tables', 'nl2br']
            )
            html_lines.append(content_html)
            
            html_lines.extend([
                "</body>",
                "</html>"
            ])
            
            return "\n".join(html_lines)
            
        except Exception as e:
            logger.error("Failed to generate HTML content", error=str(e))
            raise
    
    def cleanup_export_file(self, file_path: str) -> None:
        """Clean up temporary export file."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug("Export file cleaned up", file_path=file_path)
        except Exception as e:
            logger.warning("Failed to cleanup export file", file_path=file_path, error=str(e))


# Global export service instance
_export_service: Optional[ExportService] = None


def get_export_service() -> ExportService:
    """Get or create the global export service instance."""
    global _export_service
    if _export_service is None:
        _export_service = ExportService()
    return _export_service
