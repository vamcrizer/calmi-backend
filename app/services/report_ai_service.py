"""
Report AI Service - Severity analysis using OpenAI.
Supports text + image input for multimodal analysis.

OPTIMIZED: Uses shared AsyncOpenAI client with connection pooling.
"""
import base64
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.reports import Report, ReportAIAnalysis
from app.repositories.report_repository import (
    ReportAIAnalysisRepository,
    ReportAttachmentRepository,
    ReportRepository,
)

settings = get_settings()


@dataclass
class AIAnalysisResult:
    """Result from AI analysis."""
    severity_level: str  # LOW, MEDIUM, HIGH, EMERGENCY
    risk_type: str | None  # BULLYING, SELF_HARM, HARASSMENT, OTHER
    guidance: str  # For student
    receiver_guidance: str  # For teacher/counselor
    raw_result: dict[str, Any]
    model_name: str


# System prompt for AI analysis
# System prompt for AI analysis
ANALYSIS_PROMPT = """Bạn là chuyên gia tâm lý học đường với 20 năm kinh nghiệm tư vấn học sinh. Phân tích báo cáo bạo lực học đường và đưa ra lời khuyên cụ thể.

Báo cáo từ học sinh:
{content}

Loại sự cố: {incident_type}
Địa điểm: {location}

NHIỆM VỤ CỦA BẠN:
1. Đánh giá mức độ nghiêm trọng (severity_level):
   - EMERGENCY: Nguy hiểm tức thì, cần can thiệp ngay (tự hại, bạo lực nghiêm trọng)
   - HIGH: Cần xử lý khẩn cấp trong 24h (bắt nạt liên tục, đe dọa)
   - MEDIUM: Cần theo dõi và hỗ trợ (xung đột, cô lập nhẹ)
   - LOW: Vấn đề nhỏ, cần tư vấn (hiểu lầm, xích mích)

2. Xác định loại rủi ro (risk_type):
   - BULLYING: Bắt nạt, trêu chọc, đánh đập
   - SELF_HARM: Tự gây thương tích
   - HARASSMENT: Quấy rối tình dục
   - OTHER: Các vấn đề khác

3. Đưa ra lời khuyên cho HỌC SINH (guidance):
   - 3-5 bước CỤ THỂ và DỄ THỰC HIỆN
   - Ngôn ngữ thân thiện, đồng cảm
   - Động viên tinh thần
   - Hướng dẫn hành động an toàn
   
4. Đưa ra hướng dẫn cho TỔ CHỨC/CƠ QUAN TIẾP NHẬN (receiver_guidance):
   - Đây là hướng dẫn gửi qua EMAIL cho tổ chức hỗ trợ, CÔNG AN, hoặc CƠ QUAN BẢO VỆ TRẺ EM
   - KHÔNG phải lời khuyên cho học sinh
   - 3-5 HÀNH ĐỘNG CỤ THỂ mà TỔ CHỨC cần thực hiện
   - Sử dụng ngôn ngữ CHUYÊN NGHIỆP, HÀNH CHÍNH
   - Ví dụ: "Tiếp nhận thông tin và kiểm tra xác minh vụ việc", "Phối hợp với nhà trường", "Phản hồi tình trạng xử lý"

ĐỊNH DẠNG XUẤT RA (JSON):
{{
    "severity_level": "LOW|MEDIUM|HIGH|EMERGENCY",
    "risk_type": "BULLYING|SELF_HARM|HARASSMENT|OTHER",
    "guidance": "• Bước 1: Mô tả cụ thể hành động\\n• Bước 2: Mô tả tiếp\\n• Bước 3: Động viên",
    "receiver_guidance": "• Tiếp nhận thông tin và kiểm tra xác minh vụ việc\\n• Phối hợp với nhà trường để có biện pháp bảo vệ nạn nhân\\n• Phản hồi tình trạng xử lý để cập nhật trên hệ thống"
}}

VÍ DỤ TỐT:
{{
    "severity_level": "MEDIUM",
    "risk_type": "BULLYING",
    "guidance": "• Hãy bình tĩnh, con đã rất dũng cảm khi báo cáo điều này\\n• Tránh xa những người đã trêu chọc con trong thời gian tới\\n• Nói chuyện với thầy cô hoặc bố mẹ về việc này\\n• Ghi lại chi tiết nếu việc này tiếp tục xảy ra\\n• Nhớ rằng con không có lỗi gì cả",
    "receiver_guidance": "• Tiếp nhận thông tin và kiểm tra xác minh vụ việc qua liên hệ với nhà trường\\n• Phối hợp với nhà trường {{tên_trường}} để có biện pháp bảo vệ nạn nhân\\n• Phản hồi tình trạng xử lý để chúng tôi cập nhật trên hệ thống"
}}

LƯU Ý: Dùng \\n để xuống dòng. Mỗi bullet point phải là hành động CỤ THỂ, KHÔNG chung chung."""


class ReportAIService:
    """
    Service for AI-based report analysis.
    Supports multimodal input (text + images).
    
    OPTIMIZED: Uses shared AsyncOpenAI client with connection pooling.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.report_repo = ReportRepository(session)
        self.analysis_repo = ReportAIAnalysisRepository(session)
        self.attach_repo = ReportAttachmentRepository(session)
        self.model_name = settings.OPENAI_MODEL
        # OPTIMIZED: Use shared client with connection pooling
        from app.core.openai_client import get_async_openai_client
        self.client = get_async_openai_client()
    
    def _encode_image_to_base64(self, file_path: str) -> str | None:
        """Encode image file to base64 string."""
        path = Path(file_path)
        if not path.exists():
            return None
        try:
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception:
            return None
    
    def _get_mime_type(self, file_path: str) -> str:
        """Get MIME type from file extension."""
        ext = Path(file_path).suffix.lower()
        mime_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        return mime_map.get(ext, "image/jpeg")
    
    async def analyze_report(
        self,
        report: Report,
        image_paths: list[str] = None,
    ) -> AIAnalysisResult:
        """
        Analyze a report with optional images.
        
        Args:
            report: Report to analyze
            image_paths: List of image file paths for vision analysis
        """
        incident_type_name = report.incident_type.name if report.incident_type else "Không xác định"
        location = report.location_text or "Không xác định"
        
        prompt = ANALYSIS_PROMPT.format(
            content=report.content,
            incident_type=incident_type_name,
            location=location,
        )
        
        # Prepare messages
        messages = [
            {"role": "system", "content": "Bạn là chuyên gia tâm lý học đường. Phân tích báo cáo và hình ảnh bằng chứng (nếu có), trả lời JSON."},
        ]
        
        user_content = []
        user_content.append({"type": "text", "text": prompt})
        
        # Add images if provided
        if image_paths:
            for img_path in image_paths[:3]:  # Max 3 images
                base64_img = self._encode_image_to_base64(img_path)
                if base64_img:
                    mime_type = self._get_mime_type(img_path)
                    user_content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_img}"
                        }
                    })
        
        messages.append({"role": "user", "content": user_content})
        
        try:
            # OPTIMIZED: Use async client for non-blocking
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                response_format={"type": "json_object"},
                max_tokens=500,  # Limit response for speed
            )
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from OpenAI")
            result = json.loads(content)
        except Exception as e:
            # Fallback for error handling
            print(f"[ReportAI] Analysis Error: {e}")
            result = {}
        
        severity_level = result.get("severity_level", "LOW")
        risk_type = result.get("risk_type", "OTHER")
        guidance = result.get("guidance", "• Cảm ơn con đã dũng cảm báo cáo\n• Hãy nói chuyện với thầy cô hoặc bố mẹ về điều này\n• Chúng mình sẽ hỗ trợ con")
        receiver_guidance = result.get("receiver_guidance", "• Gặp học sinh để thể hiện sự quan tâm\n• Thu thập thêm thông tin chi tiết\n• Theo dõi tình hình")
        
        if severity_level not in ["LOW", "MEDIUM", "HIGH", "EMERGENCY"]:
            severity_level = "LOW"
        
        raw_result = {
            "analyzed_at": datetime.utcnow().isoformat(),
            "model": self.model_name,
            "response": result,
            "images_count": len(image_paths) if image_paths else 0,
        }
        
        return AIAnalysisResult(
            severity_level=severity_level,
            risk_type=risk_type,
            guidance=guidance,
            receiver_guidance=receiver_guidance,
            raw_result=raw_result,
            model_name=self.model_name,
        )
    
    async def analyze_and_save(self, report: Report) -> AIAnalysisResult:
        """Analyze report (with attachments) and save results to database."""
        report_id = report.id # Cache ID prevent expiration issue after commit
        
        # Get image attachments
        image_paths = []
        attachments = await self.attach_repo.list_by_report(report_id)
        for att in attachments:
            if att.file and att.attachment_type == "IMAGE":
                file_path = att.file.anonymized_path or att.file.storage_path
                if file_path:
                    image_paths.append(file_path)
        
        result = await self.analyze_report(report, image_paths)
        
        await self.analysis_repo.create({
            "report_id": report_id,
            "model_name": result.model_name,
            "severity_level": result.severity_level,
            "risk_type": result.risk_type,
            "guidance": result.guidance,
            "raw_result": result.raw_result,
        })
        
        await self.report_repo.update_ai_result(
            report_id,
            result.severity_level,
            result.guidance,
        )
        
        return result
