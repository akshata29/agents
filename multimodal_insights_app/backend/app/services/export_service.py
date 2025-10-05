"""
Export Service - Multimodal Insights Application

Handles exporting analysis results in various formats (Markdown, HTML, PDF, JSON).
Built from scratch for multimodal content processing results.
"""

import json
import asyncio
import tempfile
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import structlog
import aiofiles
import markdown

# PDF generation using pdfkit (wkhtmltopdf)
try:
    import pdfkit
    PDFKIT_AVAILABLE = True
except ImportError:
    PDFKIT_AVAILABLE = False

# Fallback to ReportLab
if not PDFKIT_AVAILABLE:
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        REPORTLAB_AVAILABLE = True
    except ImportError:
        REPORTLAB_AVAILABLE = False

from ..models.task_models import PlanWithSteps, StepStatus
from ..persistence.cosmos_memory import CosmosMemoryStore
from ..infra.settings import Settings

logger = structlog.get_logger(__name__)


class ExportService:
    """
    Service for exporting analysis results to various formats.
    
    Supports:
    - Markdown (.md)
    - PDF (.pdf)
    - JSON (.json)
    - HTML (.html)
    """
    
    def __init__(self, settings: Settings):
        """Initialize export service."""
        self.settings = settings
        self.memory_store = CosmosMemoryStore(settings)
        
        # Create exports directory
        self.exports_dir = Path("exports")
        self.exports_dir.mkdir(exist_ok=True)
        
        logger.info("Export Service initialized", exports_dir=str(self.exports_dir))
    
    async def initialize(self):
        """Initialize service resources."""
        await self.memory_store.initialize()
        logger.info("Export Service ready")
    
    async def shutdown(self):
        """Cleanup service resources."""
        await self.memory_store.close()
        logger.info("Export Service shutdown")
    
    async def export_results(
        self,
        plan_id: str,
        session_id: str,
        export_format: str = "markdown",
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Export plan execution results in specified format.
        
        Args:
            plan_id: Plan ID to export
            session_id: Session ID
            export_format: Format to export (markdown, pdf, json, html)
            include_metadata: Whether to include execution metadata
        
        Returns:
            Dict with file_path and metadata
        """
        logger.info(
            "Exporting results",
            plan_id=plan_id,
            format=export_format
        )
        
        try:
            # Get plan with steps
            plan_with_steps = await self.memory_store.get_plan_with_steps(plan_id, session_id)
            if not plan_with_steps:
                raise ValueError(f"Plan {plan_id} not found")
            
            # Get messages for context
            messages = await self.memory_store.get_messages_for_plan(plan_id, session_id)
            
            # Get file metadata
            files_metadata = []
            for file_id in plan_with_steps.file_ids:
                file_meta = await self.memory_store.get_file_metadata(file_id, session_id)
                if file_meta:
                    files_metadata.append(file_meta)
            
            # Build export data structure
            export_data = {
                "plan": plan_with_steps,
                "messages": messages,
                "files": files_metadata,
                "include_metadata": include_metadata
            }
            
            # Export based on format
            if export_format.lower() == "markdown" or export_format.lower() == "md":
                result = await self._export_markdown(export_data, plan_id, session_id)
            elif export_format.lower() == "pdf":
                result = await self._export_pdf(export_data, plan_id, session_id)
            elif export_format.lower() == "json":
                result = await self._export_json(export_data, plan_id, session_id)
            elif export_format.lower() == "html":
                result = await self._export_html(export_data, plan_id, session_id)
            else:
                raise ValueError(f"Unsupported export format: {export_format}")
            
            logger.info(
                "Export completed successfully",
                plan_id=plan_id,
                format=export_format,
                file_path=result["file_path"]
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Export failed", error=str(e), plan_id=plan_id)
            raise
    
    async def _export_markdown(
        self,
        export_data: Dict[str, Any],
        plan_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """Export results as Markdown."""
        plan = export_data["plan"]
        messages = export_data["messages"]
        files = export_data["files"]
        include_metadata = export_data["include_metadata"]
        
        # Build Markdown content
        md_lines = []
        
        # Header
        md_lines.append("# Multimodal Insights Report")
        md_lines.append("")
        md_lines.append(f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        md_lines.append(f"**Session ID:** {session_id}")
        md_lines.append(f"**Plan ID:** {plan_id}")
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")
        
        # Executive Summary
        md_lines.append("## Executive Summary")
        md_lines.append("")
        md_lines.append(f"**Objective:** {plan.initial_goal}")
        md_lines.append("")
        md_lines.append(f"**Status:** {plan.overall_status.value.upper()}")
        md_lines.append(f"**Completed Steps:** {plan.completed_steps}/{plan.total_steps}")
        if plan.failed_steps > 0:
            md_lines.append(f"**Failed Steps:** {plan.failed_steps}")
        md_lines.append("")
        
        # Files Processed
        if files:
            md_lines.append("## Processed Files")
            md_lines.append("")
            for file in files:
                md_lines.append(f"- **{file.filename}** ({file.file_type.value})")
                md_lines.append(f"  - Size: {file.file_size} bytes")
                md_lines.append(f"  - Status: {file.processing_status}")
                if file.processed_at:
                    md_lines.append(f"  - Processed: {file.processed_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            md_lines.append("")
        
        # Execution Steps and Results
        md_lines.append("## Analysis Results")
        md_lines.append("")
        
        for idx, step in enumerate(plan.steps, 1):
            md_lines.append(f"### Step {idx}: {step.action}")
            md_lines.append("")
            md_lines.append(f"**Agent:** {step.agent.value}")
            md_lines.append(f"**Status:** {step.status.value}")
            md_lines.append("")
            
            if step.agent_reply:
                md_lines.append("**Results:**")
                md_lines.append("")
                
                # Try to parse JSON response for better formatting
                try:
                    reply_data = json.loads(step.agent_reply)
                    md_lines.append("```json")
                    md_lines.append(json.dumps(reply_data, indent=2))
                    md_lines.append("```")
                except:
                    md_lines.append(step.agent_reply)
                
                md_lines.append("")
            
            if step.error_message:
                md_lines.append(f"**Error:** {step.error_message}")
                md_lines.append("")
        
        # Metadata section
        if include_metadata:
            md_lines.append("---")
            md_lines.append("")
            md_lines.append("## Metadata")
            md_lines.append("")
            md_lines.append(f"- **Plan Created:** {plan.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            md_lines.append(f"- **Total Messages:** {len(messages)}")
            md_lines.append(f"- **User ID:** {plan.user_id}")
            md_lines.append("")
        
        # Write to file
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"insights_report_{plan_id[:8]}_{timestamp}.md"
        file_path = self.exports_dir / filename
        
        async with asyncio.Lock():
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(md_lines))
        
        return {
            "file_path": str(file_path),
            "filename": filename,
            "format": "markdown",
            "size_bytes": file_path.stat().st_size
        }
    
    async def _export_html(
        self,
        export_data: Dict[str, Any],
        plan_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """Export results as HTML."""
        plan = export_data["plan"]
        messages = export_data["messages"]
        files = export_data["files"]
        include_metadata = export_data["include_metadata"]
        
        # Build HTML content
        html_lines = []
        
        # HTML Header
        html_lines.append("<!DOCTYPE html>")
        html_lines.append("<html lang='en'>")
        html_lines.append("<head>")
        html_lines.append("    <meta charset='UTF-8'>")
        html_lines.append("    <meta name='viewport' content='width=device-width, initial-scale=1.0'>")
        html_lines.append("    <title>Multimodal Insights Report</title>")
        html_lines.append("    <style>")
        html_lines.append("        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }")
        html_lines.append("        .container { background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }")
        html_lines.append("        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }")
        html_lines.append("        h2 { color: #34495e; margin-top: 30px; border-bottom: 2px solid #ecf0f1; padding-bottom: 8px; }")
        html_lines.append("        h3 { color: #7f8c8d; margin-top: 20px; }")
        html_lines.append("        .metadata { background: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0; }")
        html_lines.append("        .metadata p { margin: 5px 0; }")
        html_lines.append("        .step { background: #f8f9fa; padding: 20px; margin: 15px 0; border-left: 4px solid #3498db; border-radius: 4px; }")
        html_lines.append("        .step.failed { border-left-color: #e74c3c; }")
        html_lines.append("        .step.completed { border-left-color: #2ecc71; }")
        html_lines.append("        .badge { display: inline-block; padding: 4px 8px; border-radius: 3px; font-size: 0.85em; font-weight: bold; }")
        html_lines.append("        .badge.success { background: #2ecc71; color: white; }")
        html_lines.append("        .badge.failed { background: #e74c3c; color: white; }")
        html_lines.append("        .badge.executing { background: #f39c12; color: white; }")
        html_lines.append("        .badge.pending { background: #95a5a6; color: white; }")
        html_lines.append("        .file-list { list-style: none; padding: 0; }")
        html_lines.append("        .file-list li { background: white; padding: 10px; margin: 8px 0; border: 1px solid #ddd; border-radius: 4px; }")
        html_lines.append("        pre { background: #2c3e50; color: #ecf0f1; padding: 15px; border-radius: 5px; overflow-x: auto; }")
        html_lines.append("        code { font-family: 'Courier New', monospace; }")
        html_lines.append("    </style>")
        html_lines.append("</head>")
        html_lines.append("<body>")
        html_lines.append("    <div class='container'>")
        
        # Header
        html_lines.append("        <h1>🎯 Multimodal Insights Report</h1>")
        html_lines.append("        <div class='metadata'>")
        html_lines.append(f"            <p><strong>Generated:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>")
        html_lines.append(f"            <p><strong>Session ID:</strong> {session_id}</p>")
        html_lines.append(f"            <p><strong>Plan ID:</strong> {plan_id}</p>")
        html_lines.append("        </div>")
        
        # Executive Summary
        html_lines.append("        <h2>Executive Summary</h2>")
        html_lines.append(f"        <p><strong>Objective:</strong> {plan.initial_goal}</p>")
        
        status_badge_class = "success" if plan.overall_status.value == "completed" else "failed"
        html_lines.append(f"        <p><strong>Status:</strong> <span class='badge {status_badge_class}'>{plan.overall_status.value.upper()}</span></p>")
        html_lines.append(f"        <p><strong>Progress:</strong> {plan.completed_steps}/{plan.total_steps} steps completed</p>")
        
        # Files Processed
        if files:
            html_lines.append("        <h2>📁 Processed Files</h2>")
            html_lines.append("        <ul class='file-list'>")
            for file in files:
                html_lines.append(f"            <li>")
                html_lines.append(f"                <strong>{file.filename}</strong> ({file.file_type.value})<br>")
                html_lines.append(f"                Size: {file.file_size} bytes | Status: {file.processing_status}")
                if file.processed_at:
                    html_lines.append(f" | Processed: {file.processed_at.strftime('%Y-%m-%d %H:%M:%S')}")
                html_lines.append(f"            </li>")
            html_lines.append("        </ul>")
        
        # Analysis Results
        html_lines.append("        <h2>🔍 Analysis Results</h2>")
        
        for idx, step in enumerate(plan.steps, 1):
            step_class = step.status.value.lower()
            html_lines.append(f"        <div class='step {step_class}'>")
            html_lines.append(f"            <h3>Step {idx}: {step.action}</h3>")
            html_lines.append(f"            <p><strong>Agent:</strong> {step.agent.value} | <strong>Status:</strong> <span class='badge {step_class}'>{step.status.value}</span></p>")
            
            if step.agent_reply:
                html_lines.append("            <h4>Results:</h4>")
                try:
                    reply_data = json.loads(step.agent_reply)
                    html_lines.append("            <pre><code>")
                    html_lines.append(json.dumps(reply_data, indent=2))
                    html_lines.append("            </code></pre>")
                except:
                    html_lines.append(f"            <p>{step.agent_reply}</p>")
            
            if step.error_message:
                html_lines.append(f"            <p style='color: #e74c3c;'><strong>Error:</strong> {step.error_message}</p>")
            
            html_lines.append("        </div>")
        
        # Metadata
        if include_metadata:
            html_lines.append("        <h2>ℹ️ Metadata</h2>")
            html_lines.append("        <div class='metadata'>")
            html_lines.append(f"            <p><strong>Plan Created:</strong> {plan.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>")
            html_lines.append(f"            <p><strong>Total Messages:</strong> {len(messages)}</p>")
            html_lines.append(f"            <p><strong>User ID:</strong> {plan.user_id}</p>")
            html_lines.append("        </div>")
        
        # HTML Footer
        html_lines.append("    </div>")
        html_lines.append("</body>")
        html_lines.append("</html>")
        
        # Write to file
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"insights_report_{plan_id[:8]}_{timestamp}.html"
        file_path = self.exports_dir / filename
        
        async with asyncio.Lock():
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(html_lines))
        
        return {
            "file_path": str(file_path),
            "filename": filename,
            "format": "html",
            "size_bytes": file_path.stat().st_size
        }
    
    async def _export_pdf(
        self,
        export_data: Dict[str, Any],
        plan_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """Export results as PDF using pdfkit (wkhtmltopdf) or ReportLab as fallback."""
        
        # First generate HTML
        html_result = await self._export_html(export_data, plan_id, session_id)
        html_path = Path(html_result["file_path"])
        
        # Generate PDF filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"insights_report_{plan_id[:8]}_{timestamp}.pdf"
        pdf_path = self.exports_dir / pdf_filename
        
        try:
            if PDFKIT_AVAILABLE:
                # Use pdfkit (wkhtmltopdf) for better PDF quality
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._html_to_pdf_pdfkit(str(html_path), str(pdf_path))
                )
                logger.info("PDF generated using pdfkit")
            elif REPORTLAB_AVAILABLE:
                # Fallback to ReportLab
                await self._generate_pdf_reportlab(export_data, pdf_path)
                logger.info("PDF generated using ReportLab")
            else:
                # No PDF library available, keep HTML
                logger.warning("No PDF library available, returning HTML instead")
                return {
                    "file_path": str(html_path),
                    "filename": html_result["filename"],
                    "format": "html",
                    "size_bytes": html_path.stat().st_size,
                    "warning": "PDF generation not available, HTML returned instead"
                }
            
            # Clean up temporary HTML file
            html_path.unlink(missing_ok=True)
            
            return {
                "file_path": str(pdf_path),
                "filename": pdf_filename,
                "format": "pdf",
                "size_bytes": pdf_path.stat().st_size
            }
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            # Return HTML as fallback
            return {
                "file_path": str(html_path),
                "filename": html_result["filename"],
                "format": "html",
                "size_bytes": html_path.stat().st_size,
                "warning": f"PDF generation failed: {str(e)}. HTML returned instead"
            }
    
    def _html_to_pdf_pdfkit(self, html_file_path: str, pdf_file_path: str) -> None:
        """Convert HTML file to PDF using pdfkit (wkhtmltopdf)."""
        # Configuration options for wkhtmltopdf
        options = {
            'page-size': 'A4',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
            'no-outline': None,
            'enable-local-file-access': None,
            'quiet': '',
        }
        
        # Try to find wkhtmltopdf executable on Windows
        import os
        possible_paths = [
            r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe",
            r"C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe",
            "wkhtmltopdf"  # If it's in PATH
        ]
        
        wkhtmltopdf_path = None
        for path in possible_paths:
            if path == "wkhtmltopdf" or os.path.exists(path):
                wkhtmltopdf_path = path
                break
        
        if wkhtmltopdf_path:
            config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
            pdfkit.from_file(html_file_path, pdf_file_path, options=options, configuration=config)
        else:
            # Try without explicit path (assumes it's in PATH)
            pdfkit.from_file(html_file_path, pdf_file_path, options=options)
    
    async def _generate_pdf_reportlab(
        self,
        export_data: Dict[str, Any],
        pdf_path: Path
    ):
        """Generate PDF using ReportLab (fallback method)."""
        plan = export_data["plan"]
        files = export_data["files"]
        
        doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor='#2c3e50',
            alignment=TA_CENTER
        )
        story.append(Paragraph("Multimodal Insights Report", title_style))
        story.append(Spacer(1, 0.3 * inch))
        
        # Metadata
        story.append(Paragraph(f"<b>Session ID:</b> {plan.session_id}", styles['Normal']))
        story.append(Paragraph(f"<b>Plan ID:</b> {plan.id}", styles['Normal']))
        story.append(Paragraph(f"<b>Generated:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}", styles['Normal']))
        story.append(Spacer(1, 0.3 * inch))
        
        # Executive Summary
        story.append(Paragraph("Executive Summary", styles['Heading2']))
        story.append(Paragraph(f"<b>Objective:</b> {plan.initial_goal}", styles['Normal']))
        story.append(Paragraph(f"<b>Status:</b> {plan.overall_status.value.upper()}", styles['Normal']))
        story.append(Paragraph(f"<b>Progress:</b> {plan.completed_steps}/{plan.total_steps} steps", styles['Normal']))
        story.append(Spacer(1, 0.2 * inch))
        
        # Files
        if files:
            story.append(Paragraph("Processed Files", styles['Heading2']))
            for file in files:
                story.append(Paragraph(f"• {file.filename} ({file.file_type.value})", styles['Normal']))
            story.append(Spacer(1, 0.2 * inch))
        
        # Steps
        story.append(Paragraph("Analysis Results", styles['Heading2']))
        for idx, step in enumerate(plan.steps, 1):
            story.append(Paragraph(f"Step {idx}: {step.action}", styles['Heading3']))
            story.append(Paragraph(f"<b>Agent:</b> {step.agent.value}", styles['Normal']))
            story.append(Paragraph(f"<b>Status:</b> {step.status.value}", styles['Normal']))
            if step.agent_reply:
                reply_preview = step.agent_reply[:500] + "..." if len(step.agent_reply) > 500 else step.agent_reply
                story.append(Paragraph(f"<b>Results:</b> {reply_preview}", styles['Normal']))
            story.append(Spacer(1, 0.1 * inch))
        
        # Build PDF
        doc.build(story)
    
    async def _export_json(
        self,
        export_data: Dict[str, Any],
        plan_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """Export results as JSON."""
        plan = export_data["plan"]
        messages = export_data["messages"]
        files = export_data["files"]
        include_metadata = export_data["include_metadata"]
        
        # Build JSON structure
        json_data = {
            "report_metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "session_id": session_id,
                "plan_id": plan_id,
                "format_version": "1.0"
            },
            "plan": {
                "id": plan.id,
                "session_id": plan.session_id,
                "user_id": plan.user_id,
                "initial_goal": plan.initial_goal,
                "summary": plan.summary,
                "overall_status": plan.overall_status.value,
                "total_steps": plan.total_steps,
                "completed_steps": plan.completed_steps,
                "failed_steps": plan.failed_steps,
                "timestamp": plan.timestamp.isoformat()
            },
            "files": [
                {
                    "id": f.id,
                    "filename": f.filename,
                    "file_type": f.file_type.value,
                    "file_size": f.file_size,
                    "processing_status": f.processing_status,
                    "uploaded_at": f.uploaded_at.isoformat(),
                    "processed_at": f.processed_at.isoformat() if f.processed_at else None
                }
                for f in files
            ],
            "steps": [
                {
                    "order": step.order,
                    "action": step.action,
                    "agent": step.agent.value,
                    "status": step.status.value,
                    "agent_reply": step.agent_reply,
                    "error_message": step.error_message,
                    "file_ids": step.file_ids,
                    "parameters": step.parameters
                }
                for step in plan.steps
            ]
        }
        
        if include_metadata:
            json_data["messages"] = [
                {
                    "id": msg.id,
                    "content": msg.content,
                    "source": msg.source,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in messages
            ]
        
        # Write to file
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"insights_report_{plan_id[:8]}_{timestamp}.json"
        file_path = self.exports_dir / filename
        
        async with asyncio.Lock():
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        return {
            "file_path": str(file_path),
            "filename": filename,
            "format": "json",
            "size_bytes": file_path.stat().st_size
        }
    
    async def list_exports(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all available exports, optionally filtered by session."""
        exports = []
        
        for export_file in self.exports_dir.glob("insights_report_*.*"):
            if export_file.is_file():
                stat = export_file.stat()
                exports.append({
                    "filename": export_file.name,
                    "file_path": str(export_file),
                    "format": export_file.suffix[1:],  # Remove the dot
                    "size_bytes": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat()
                })
        
        # Sort by creation time (newest first)
        exports.sort(key=lambda x: x["created_at"], reverse=True)
        
        return exports
    
    async def get_export_file(self, filename: str) -> Optional[Path]:
        """Get path to an export file."""
        file_path = self.exports_dir / filename
        if file_path.exists() and file_path.is_file():
            return file_path
        return None
