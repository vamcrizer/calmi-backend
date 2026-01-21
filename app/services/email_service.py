"""
Email Service - Using Resend API.
Supports embedding images as attachments.
"""
import base64
from pathlib import Path

import resend

from app.core.config import get_settings

settings = get_settings()


class EmailService:
    """
    Service gửi email sử dụng Resend API.
    Hỗ trợ nhúng ảnh inline.
    """
    
    def __init__(self):
        self.from_email = settings.EMAIL_FROM or "Calmi <onboarding@resend.dev>"
        self.enabled = settings.EMAIL_ENABLED
        self.resend_api_key = settings.RESEND_API_KEY
        
        if self.resend_api_key:
            resend.api_key = self.resend_api_key
    
    def send(
        self,
        to: str | list[str],
        subject: str,
        html: str,
        attachments: list[dict] = None,
    ) -> dict | None:
        """
        Gửi email qua Resend.
        
        Args:
            to: Email người nhận
            subject: Tiêu đề
            html: Nội dung HTML
            attachments: List of {"path": str, "filename": str}
        """
        if not self.enabled:
            print(f"[EMAIL DISABLED] Would send to {to}: {subject}")
            return None
        
        if not self.resend_api_key:
            print(f"[EMAIL ERROR] No Resend API key")
            return None
        
        recipients = to if isinstance(to, list) else [to]
        
        params = {
            "from": self.from_email,
            "to": recipients,
            "subject": subject,
            "html": html,
        }
        
        # Add attachments
        if attachments:
            resend_attachments = []
            for att in attachments:
                file_path = att.get("path")
                if file_path and Path(file_path).exists():
                    with open(file_path, "rb") as f:
                        content = base64.b64encode(f.read()).decode()
                    resend_attachments.append({
                        "filename": att.get("filename", "attachment"),
                        "content": content,
                    })
            if resend_attachments:
                params["attachments"] = resend_attachments
        
        response = resend.Emails.send(params)
        print(f"[EMAIL SENT] To: {to}, ID: {response.get('id')}")
        return {"status": "sent", "id": response.get("id"), "to": recipients}
    
    def _format_guidance_to_list(self, guidance: str) -> str:
        """
        Convert guidance text với bullet points thành HTML ul/li list.
        Hỗ trợ các format:
        - "• item1\n• item2"
        - "- item1\n- item2"
        - "1. item1\n2. item2"
        """
        if not guidance:
            return '<p style="color: #333; margin: 0;">Không có hướng dẫn.</p>'
        
        # Split by newlines
        lines = guidance.strip().split('\n')
        items = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Remove bullet markers
            if line.startswith('• '):
                line = line[2:]
            elif line.startswith('- '):
                line = line[2:]
            elif line[0].isdigit() and '. ' in line[:4]:
                line = line.split('. ', 1)[1] if '. ' in line else line
            items.append(line)
        
        if not items:
            return f'<p style="color: #333; margin: 0;">{guidance}</p>'
        
        # Build HTML list with inline styles for email compatibility
        list_html = '<ul style="margin: 0; padding-left: 20px; color: #333;">'
        for item in items:
            list_html += f'<li style="margin-bottom: 8px; line-height: 1.5;">{item}</li>'
        list_html += '</ul>'
        
        return list_html
    
    def send_report_notification(
        self,
        to: str,
        report_id: int,
        incident_type: str,
        severity: str,
        risk_type: str,
        content_preview: str,
        receiver_guidance: str,
        attachments: list[dict] = None,
        # New optional fields for enhanced template
        receiver_name: str = None,
        school_name: str = None,
        reporter_info: str = None,
        location: str = None,
        submitted_at: str = None,
    ) -> dict | None:
        """
        Gửi thông báo báo cáo mới với AI analysis và hình ảnh đính kèm.
        Template theo thiết kế mới với header đỏ và các section rõ ràng.
        """
        # Determine if emergency
        is_urgent = severity in ["HIGH", "EMERGENCY"]
        
        # Subject with urgency prefix
        urgency_prefix = "[KHẨN CẤP] " if is_urgent else ""
        subject = f"{urgency_prefix}BÁO CÁO BẠO LỰC HỌC ĐƯỜNG - Mã #{report_id}"
        
        # Severity display
        severity_display = "NGUY CẤP / CAO" if is_urgent else severity
        severity_color = "#C41E3A" if is_urgent else "#1a73e8"
        
        # Risk type Vietnamese
        risk_type_vn = {
            "SELF_HARM": "Tự gây thương tích",
            "BULLYING": "Bạo lực / Bắt nạt",
            "HARASSMENT": "Quấy rối",
            "PHYSICAL": "Bạo lực thể chất",
            "VERBAL": "Bạo lực lời nói",
            "CYBERBULLYING": "Bạo lực mạng",
            "EXCLUSION": "Cô lập xã hội",
            "OTHER": "Khác",
        }.get(risk_type, incident_type)
        
        # Receiver greeting
        receiver_greeting = receiver_name or "Cơ quan chức năng"
        
        # School name
        school_display = school_name or "Trường học"
        
        # Location display
        location_display = location or "(Chưa cung cấp)"
        
        # Time display
        time_display = submitted_at or "(Chưa xác định)"
        
        # Reporter info (anonymized)
        reporter_display = reporter_info or "(Ẩn danh)"
        
        # Convert receiver_guidance to HTML list
        guidance_html = self._format_guidance_to_list(receiver_guidance)
        
        # Attachments note
        attachments_note = ""
        if attachments and len(attachments) > 0:
            attachments_note = f'<p style="font-size: 12px; color: #666; margin-top: 16px;">* Các tệp bằng chứng (hình ảnh/video) đã được đính kèm theo email này.</p>'
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Arial, sans-serif; background-color: #f5f5f5;">
            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f5; padding: 20px 0;">
                <tr>
                    <td align="center">
                        <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                            
                            <!-- Header đỏ -->
                            <tr>
                                <td style="background-color: #C41E3A; padding: 24px; text-align: center;">
                                    <h1 style="color: #ffffff; margin: 0; font-size: 22px; font-weight: bold;">
                                        {urgency_prefix}BÁO CÁO BẠO LỰC HỌC ĐƯỜNG
                                    </h1>
                                    <p style="color: rgba(255,255,255,0.9); margin: 8px 0 0 0; font-size: 14px;">
                                        Mã vụ việc: #{report_id}
                                    </p>
                                </td>
                            </tr>
                            
                            <!-- Greeting -->
                            <tr>
                                <td style="padding: 24px 24px 16px 24px;">
                                    <p style="margin: 0 0 16px 0; color: #333; font-size: 14px; line-height: 1.6;">
                                        <strong>Kính gửi:</strong> {receiver_greeting},
                                    </p>
                                    <p style="margin: 0; color: #333; font-size: 14px; line-height: 1.6;">
                                        Chúng tôi là đội ngũ quản trị ứng dụng <strong>Calmi</strong> - Nền tảng hỗ trợ phòng chống bạo lực học đường. 
                                        Hệ thống vừa ghi nhận một báo cáo có mức độ rủi ro <span style="color: #C41E3A; font-weight: bold;">CAO</span> cần sự can thiệp kịp thời.
                                    </p>
                                </td>
                            </tr>
                            
                            <!-- 1. Thông tin báo cáo -->
                            <tr>
                                <td style="padding: 0 24px 16px 24px;">
                                    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #FEF2F2; border-left: 4px solid #C41E3A; border-radius: 4px;">
                                        <tr>
                                            <td style="padding: 12px 16px; border-bottom: 1px solid #FECACA;">
                                                <span style="color: #666;">Mã báo cáo:</span>
                                            </td>
                                            <td style="padding: 12px 16px; border-bottom: 1px solid #FECACA;">
                                                <span style="color: #C41E3A; font-weight: bold;">#{report_id}</span>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 12px 16px; border-bottom: 1px solid #FECACA;">
                                                <span style="color: #666;">Loại sự cố:</span>
                                            </td>
                                            <td style="padding: 12px 16px; border-bottom: 1px solid #FECACA;">
                                                {risk_type_vn}
                                            </td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 12px 16px; border-bottom: 1px solid #FECACA;">
                                                <span style="color: #666;">Mức độ:</span>
                                            </td>
                                            <td style="padding: 12px 16px; border-bottom: 1px solid #FECACA;">
                                                <span style="color: #C41E3A; font-weight: bold;">{severity_display}</span>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 12px 16px;">
                                                <span style="color: #666;">Thời gian:</span>
                                            </td>
                                            <td style="padding: 12px 16px;">
                                                {time_display}
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                            
                            <!-- 2. Nội dung chi tiết -->
                            <tr>
                                <td style="padding: 0 24px 16px 24px;">
                                    <p style="margin: 0 0 12px 0; font-size: 14px; font-weight: bold; color: #C41E3A; border-bottom: 2px solid #C41E3A; padding-bottom: 8px; display: inline-block;">
                                        2. Nội dung chi tiết
                                    </p>
                                    <div style="background-color: #fafafa; padding: 16px; border-radius: 8px; border-left: 4px solid #C41E3A;">
                                        <p style="margin: 0; color: #333; font-size: 14px; line-height: 1.6; font-style: italic;">
                                            "{content_preview}"
                                        </p>
                                    </div>
                                </td>
                            </tr>
                            
                            <!-- 3. Thông tin đối tượng -->
                            <tr>
                                <td style="padding: 0 24px 16px 24px;">
                                    <p style="margin: 0 0 12px 0; font-size: 14px; font-weight: bold; color: #C41E3A; border-bottom: 2px solid #C41E3A; padding-bottom: 8px; display: inline-block;">
                                        3. Thông tin đối tượng
                                    </p>
                                    <table width="100%" cellpadding="0" cellspacing="0">
                                        <tr>
                                            <td style="padding: 8px 0; color: #666; width: 40%;">Người báo cáo:</td>
                                            <td style="padding: 8px 0; color: #333;">{reporter_display}</td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 8px 0; color: #666;">Đối tượng bị phản ánh:</td>
                                            <td style="padding: 8px 0; color: #333;">(Thông tin trong nội dung)</td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 8px 0; color: #666;">Địa điểm xảy ra:</td>
                                            <td style="padding: 8px 0; color: #333;">{location_display}</td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                            
                            <!-- 4. Đề xuất phối hợp -->
                            <tr>
                                <td style="padding: 0 24px 16px 24px;">
                                    <p style="margin: 0 0 12px 0; font-size: 14px; font-weight: bold; color: #C41E3A; border-bottom: 2px solid #C41E3A; padding-bottom: 8px; display: inline-block;">
                                        4. Đề xuất phối hợp
                                    </p>
                                    <p style="margin: 0 0 12px 0; color: #333; font-size: 14px; line-height: 1.6;">
                                        Dựa trên đánh giá từ AI của hệ thống Calmi, chúng tôi kính đề nghị:
                                    </p>
                                    {guidance_html}
                                    {attachments_note}
                                </td>
                            </tr>
                            
                            <!-- Hotline -->
                            <tr>
                                <td style="padding: 16px 24px; text-align: center; border-top: 1px solid #e0e0e0;">
                                    <p style="margin: 0 0 12px 0; font-size: 14px; font-weight: bold; color: #333;">
                                        Cần trao đổi gấp, vui lòng liên hệ Hotline:
                                    </p>
                                    <a href="tel:0867104228" style="display: inline-block; background-color: #C41E3A; color: #ffffff; padding: 12px 32px; border-radius: 24px; text-decoration: none; font-size: 18px; font-weight: bold;">
                                        0867 104 228
                                    </a>
                                </td>
                            </tr>
                            
                            <!-- Footer -->
                            <tr>
                                <td style="padding: 20px 24px; background-color: #f5f5f5; text-align: center;">
                                    <p style="margin: 0 0 8px 0; font-size: 14px; font-weight: bold; color: #333;">
                                        Ban Quản trị Ứng dụng Calmi
                                    </p>
                                    <p style="margin: 0 0 8px 0; font-size: 12px; color: #666;">
                                        [Website/Link ứng dụng] | Email này được gửi tự động từ hệ thống.
                                    </p>
                                    <p style="margin: 0; font-size: 11px; color: #999;">
                                        Bảo mật thông tin: Nội dung email này chứa thông tin nhạy cảm về trẻ vị thành niên, vui lòng bảo mật theo quy định pháp luật.
                                    </p>
                                </td>
                            </tr>
                            
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        return self.send(to=to, subject=subject, html=html, attachments=attachments)


# Singleton
_email_service: EmailService | None = None


def get_email_service() -> EmailService:
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
