"""
Email service for the XerpeX ERP System
"""
import logging
from typing import List, Optional
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.settings import GeneralSettings

# Configure logging
logger = logging.getLogger(__name__)

# Email configuration - only initialize if all required settings are present
fastmail = None
if all([settings.MAIL_USERNAME, settings.MAIL_PASSWORD, settings.MAIL_FROM, settings.MAIL_SERVER]):
    conf = ConnectionConfig(
        MAIL_USERNAME=settings.MAIL_USERNAME,
        MAIL_PASSWORD=settings.MAIL_PASSWORD,
        MAIL_FROM=settings.MAIL_FROM,
        MAIL_PORT=settings.MAIL_PORT,
        MAIL_SERVER=settings.MAIL_SERVER,
        MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
        MAIL_STARTTLS=settings.MAIL_STARTTLS,
        MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True
    )
    fastmail = FastMail(conf)


async def send_survey_notification_to_salesman(
    salesman_email: EmailStr,
    salesman_name: str,
    survey_data: dict
) -> bool:
    """
    Send survey assignment notification to salesman
    
    Args:
        salesman_email: Salesman's email address
        salesman_name: Salesman's full name
        survey_data: Survey information
        
    Returns:
        bool: True if email sent successfully
    """
    if not fastmail:
        logger.warning("Email service not configured. Skipping salesman notification.")
        return False
        
    try:
        html_content = f"""
        <html>
        <body>
            <h2>New Survey Assignment - XerpeX ERP System</h2>
            <p>Dear {salesman_name},</p>
            
            <p>A new survey has been assigned to you. Please find the details below:</p>
            
            <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3>Survey Details:</h3>
                <p><strong>Client Name:</strong> {survey_data.get('client_name', 'N/A')}</p>
                <p><strong>Email:</strong> {survey_data.get('email', 'N/A')}</p>
                <p><strong>Phone:</strong> {survey_data.get('phone_number', 'N/A')}</p>
                <p><strong>Estimated Paxes:</strong> {survey_data.get('estimated_paxes', 'N/A')}</p>
                <p><strong>Villa Types:</strong> {survey_data.get('villa_types', 'N/A')}</p>
                <p><strong>Priority:</strong> {survey_data.get('priority', 'medium').upper()}</p>
                <p><strong>Status:</strong> {survey_data.get('status', 'new').upper()}</p>
                {f"<p><strong>Follow-up Date:</strong> {survey_data.get('follow_up_date', 'Not set')}</p>" if survey_data.get('follow_up_date') else ""}
                {f"<p><strong>Visiting Date:</strong> {survey_data.get('visiting_date', 'Not set')}</p>" if survey_data.get('visiting_date') else ""}
                {f"<p><strong>Notes:</strong> {survey_data.get('notes', 'No notes')}</p>" if survey_data.get('notes') else ""}
            </div>
            
            <p>Please log into the system to view more details and take appropriate action.</p>
            
            <p>Best regards,<br>
            XerpeX ERP System</p>
        </body>
        </html>
        """
        
        message = MessageSchema(
            subject="New Survey Assignment - XerpeX ERP",
            recipients=[salesman_email],
            body=html_content,
            subtype=MessageType.html
        )
        
        await fastmail.send_message(message)
        logger.info(f"Survey notification sent to salesman: {salesman_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send survey notification to salesman {salesman_email}: {str(e)}")
        return False


async def send_survey_notification_to_admin(
    admin_email: EmailStr,
    survey_data: dict,
    salesman_name: Optional[str] = None
) -> bool:
    """
    Send survey notification to admin
    
    Args:
        admin_email: Admin's email address
        survey_data: Survey information
        salesman_name: Assigned salesman's name
        
    Returns:
        bool: True if email sent successfully
    """
    if not fastmail or not settings.ADMIN_EMAIL:
        logger.warning("Email service not configured or admin email missing. Skipping admin notification.")
        return False
        
    try:
        html_content = f"""
        <html>
        <body>
            <h2>New Survey Submission - XerpeX ERP System</h2>
            <p>Dear Admin,</p>
            
            <p>A new survey has been submitted to the system. Please find the details below:</p>
            
            <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3>Survey Details:</h3>
                <p><strong>Client Name:</strong> {survey_data.get('client_name', 'N/A')}</p>
                <p><strong>Email:</strong> {survey_data.get('email', 'N/A')}</p>
                <p><strong>Phone:</strong> {survey_data.get('phone_number', 'N/A')}</p>
                <p><strong>Estimated Paxes:</strong> {survey_data.get('estimated_paxes', 'N/A')}</p>
                <p><strong>Villa Types:</strong> {survey_data.get('villa_types', 'N/A')}</p>
                <p><strong>Priority:</strong> {survey_data.get('priority', 'medium').upper()}</p>
                <p><strong>Status:</strong> {survey_data.get('status', 'new').upper()}</p>
                <p><strong>Assigned to:</strong> {salesman_name or 'Default Salesman'}</p>
                {f"<p><strong>Follow-up Date:</strong> {survey_data.get('follow_up_date', 'Not set')}</p>" if survey_data.get('follow_up_date') else ""}
                {f"<p><strong>Visiting Date:</strong> {survey_data.get('visiting_date', 'Not set')}</p>" if survey_data.get('visiting_date') else ""}
                {f"<p><strong>Notes:</strong> {survey_data.get('notes', 'No notes')}</p>" if survey_data.get('notes') else ""}
            </div>
            
            <p>Please log into the system to review and manage this survey.</p>
            
            <p>Best regards,<br>
            XerpeX ERP System</p>
        </body>
        </html>
        """
        
        message = MessageSchema(
            subject="New Survey Submission - XerpeX ERP",
            recipients=[admin_email],
            body=html_content,
            subtype=MessageType.html
        )
        
        await fastmail.send_message(message)
        logger.info(f"Survey notification sent to admin: {admin_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send survey notification to admin {admin_email}: {str(e)}")
        return False


async def send_survey_status_update_notification(
    recipient_email: EmailStr,
    recipient_name: str,
    survey_data: dict,
    old_status: str,
    new_status: str
) -> bool:
    """
    Send survey status update notification
    
    Args:
        recipient_email: Recipient's email address
        recipient_name: Recipient's name
        survey_data: Survey information
        old_status: Previous status
        new_status: New status
        
    Returns:
        bool: True if email sent successfully
    """
    if not fastmail:
        logger.warning("Email service not configured. Skipping status update notification.")
        return False
        
    try:
        html_content = f"""
        <html>
        <body>
            <h2>Survey Status Update - XerpeX ERP System</h2>
            <p>Dear {recipient_name},</p>
            
            <p>The status of a survey has been updated. Please find the details below:</p>
            
            <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3>Survey Details:</h3>
                <p><strong>Client Name:</strong> {survey_data.get('client_name', 'N/A')}</p>
                <p><strong>Email:</strong> {survey_data.get('email', 'N/A')}</p>
                <p><strong>Status Change:</strong> {old_status.upper()} → {new_status.upper()}</p>
                <p><strong>Priority:</strong> {survey_data.get('priority', 'medium').upper()}</p>
                {f"<p><strong>Follow-up Date:</strong> {survey_data.get('follow_up_date', 'Not set')}</p>" if survey_data.get('follow_up_date') else ""}
                {f"<p><strong>Visiting Date:</strong> {survey_data.get('visiting_date', 'Not set')}</p>" if survey_data.get('visiting_date') else ""}
            </div>
            
            <p>Please log into the system to view more details.</p>
            
            <p>Best regards,<br>
            XerpeX ERP System</p>
        </body>
        </html>
        """
        
        message = MessageSchema(
            subject="Survey Status Update - XerpeX ERP",
            recipients=[recipient_email],
            body=html_content,
            subtype=MessageType.html
        )
        
        await fastmail.send_message(message)
        logger.info(f"Survey status update notification sent to: {recipient_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send survey status update notification to {recipient_email}: {str(e)}")
        return False


async def send_survey_notification_to_sales_team(
    sales_admin_email: Optional[str],
    sales_director_email: Optional[str],
    survey_data: dict,
    salesman_name: Optional[str] = None
) -> bool:
    """
    Send survey notification to sales admin and director
    
    Args:
        sales_admin_email: Sales admin's email address
        sales_director_email: Sales director's email address
        survey_data: Survey information
        salesman_name: Assigned salesman's name
        
    Returns:
        bool: True if at least one email sent successfully
    """
    if not fastmail:
        logger.warning("Email service not configured. Skipping sales team notification.")
        return False
    
    success_count = 0
    recipients = []
    
    # Add recipients if emails are configured
    if sales_admin_email:
        recipients.append(sales_admin_email)
    if sales_director_email:
        recipients.append(sales_director_email)
    
    if not recipients:
        logger.warning("No sales team email addresses configured. Skipping sales team notification.")
        return False
        
    try:
        html_content = f"""
        <html>
        <body>
            <h2>New Survey Submission - Sales Team Notification</h2>
            <p>Dear Sales Team,</p>
            
            <p>A new survey has been submitted to the XerpeX ERP System. Please find the details below:</p>
            
            <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3>Survey Details:</h3>
                <p><strong>Client Name:</strong> {survey_data.get('client_name', 'N/A')}</p>
                <p><strong>Email:</strong> {survey_data.get('email', 'N/A')}</p>
                <p><strong>Phone:</strong> {survey_data.get('phone_number', 'N/A')}</p>
                <p><strong>Estimated Paxes:</strong> {survey_data.get('estimated_paxes', 'N/A')}</p>
                <p><strong>Villa Types:</strong> {survey_data.get('villa_types', 'N/A')}</p>
                <p><strong>Priority:</strong> {survey_data.get('priority', 'medium').upper()}</p>
                <p><strong>Status:</strong> {survey_data.get('status', 'new').upper()}</p>
                <p><strong>Assigned to:</strong> {salesman_name or 'Default Salesman'}</p>
                {f"<p><strong>Follow-up Date:</strong> {survey_data.get('follow_up_date', 'Not set')}</p>" if survey_data.get('follow_up_date') else ""}
                {f"<p><strong>Visiting Date:</strong> {survey_data.get('visiting_date', 'Not set')}</p>" if survey_data.get('visiting_date') else ""}
                {f"<p><strong>Notes:</strong> {survey_data.get('notes', 'No notes')}</p>" if survey_data.get('notes') else ""}
            </div>
            
            <p>This is an automated notification to keep the sales team informed of new survey submissions.</p>
            <p>Please log into the system to review and manage this survey as needed.</p>
            
            <p>Best regards,<br>
            XerpeX ERP System</p>
        </body>
        </html>
        """
        
        message = MessageSchema(
            subject="New Survey Submission - Sales Team Notification",
            recipients=recipients,
            body=html_content,
            subtype=MessageType.html
        )
        
        await fastmail.send_message(message)
        logger.info(f"Survey notification sent to sales team: {', '.join(recipients)}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send survey notification to sales team {recipients}: {str(e)}")
        return False


async def send_invoice_email(
    customer_email: str,
    customer_name: str,
    invoice_data: dict,
    company_info: dict
) -> bool:
    """
    Send invoice email to customer in Indonesian with bank payment information
    
    Args:
        customer_email: Customer's email address
        customer_name: Customer's full name
        invoice_data: Invoice information
        company_info: Company information
        
    Returns:
        bool: True if email sent successfully
    """
    if not fastmail:
        logger.warning("Email service not configured. Skipping invoice email.")
        return False
        
    if not customer_email:
        logger.warning("Customer email not provided. Cannot send invoice email.")
        return False
        
    try:
        # Query bank information from general_settings table
        db = SessionLocal()
        try:
            general_settings = db.query(GeneralSettings).first()
            logger.info(f"Retrieved general_settings for invoice email: {general_settings is not None}")
            if general_settings:
                logger.info(f"Bank info - Name: {general_settings.bank_name}, Account: {general_settings.bank_account_number}")
        finally:
            db.close()
        
        # Format currency amounts in Rupiah
        total_amount = f"Rp{invoice_data.get('total', 0):,.2f}"
        amount_due = f"Rp{invoice_data.get('amount_due', 0):,.2f}"
        
        # Format dates
        issue_date = invoice_data.get('formatted_issue_date', invoice_data.get('issue_date', 'N/A'))
        due_date = invoice_data.get('formatted_due_date', invoice_data.get('due_date', 'N/A'))
        
        # Get invoice items for display (Indonesian)
        items_html = ""
        if invoice_data.get('items'):
            items_html = "<h4>Daftar Pesanan:</h4><ul>"
            for item in invoice_data['items']:
                package_name = item.get('package', {}).get('name', 'Layanan')
                unit_price = f"Rp{item.get('unit_price', 0):,.2f}"
                discount = f"Rp{item.get('discount', 0):,.2f}"
                line_total = f"Rp{item.get('line_total', 0):,.2f}"
                items_html += f"""
                <li style="margin-bottom: 8px;">
                    <strong>{package_name}</strong><br>
                    Harga: {unit_price}
                    {f' | Diskon: {discount}' if item.get('discount', 0) > 0 else ''}
                    | Total: {line_total}
                </li>
                """
            items_html += "</ul>"
        
        # Prepare bank information section
        bank_info_html = ""
        if general_settings:
            logger.info("Adding bank information to email template")
            bank_info_html = f"""
            <div class="bank-info">
                <p>Lakukan pembayaran melalui akun resmi {general_settings.company_name or 'perusahaan kami'}</p>
                <p><strong>Bank:</strong> {general_settings.bank_name or 'N/A'}</p>
                <p><strong>Nomor Rekening:</strong> {general_settings.bank_account_number or 'N/A'}</p>
                <p><strong>Atas Nama:</strong> {general_settings.bank_account_holder_name or 'N/A'}</p>
            </div>
            """
        else:
            logger.warning("No general_settings found - bank information will not be included in email")
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                }}
                .header {{
                    background-color: #2c3e50;
                    color: white;
                    padding: 20px;
                    text-align: center;
                }}
                .content {{
                    padding: 20px;
                }}
                .invoice-details {{
                    background-color: #f8f9fa;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                    border-left: 4px solid #3498db;
                }}
                .amount-highlight {{
                    background-color: #e8f5e8;
                    padding: 15px;
                    border-radius: 6px;
                    text-align: center;
                    margin: 20px 0;
                    border: 2px solid #27ae60;
                }}
                .payment-info {{
                    background-color: #fff3cd;
                    padding: 15px;
                    border-radius: 6px;
                    margin: 20px 0;
                    border-left: 4px solid #ffc107;
                }}
                .footer {{
                    background-color: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    font-size: 12px;
                    color: #6c757d;
                }}
                ul {{
                    padding-left: 20px;
                }}
                li {{
                    margin-bottom: 5px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Invoice dari {company_info.get('name', 'Your Company')}</h1>
                <p>Invoice #{invoice_data.get('invoice_number', 'N/A')}</p>
            </div>
            
            <div class="content">
                <p>Yth. {customer_name},</p>
                
                <p>Terima kasih atas kepercayaan anda kepada kami. Di bawah ini adalah tagihan aktif anda:</p>
                
                <div class="invoice-details">
                    <h3>Invoice Details:</h3>
                    <p><strong>Invoice Number:</strong> {invoice_data.get('invoice_number', 'N/A')}</p>
                    <p><strong>Issue Date:</strong> {issue_date}</p>
                    <p><strong>Due Date:</strong> {due_date}</p>
                    <p><strong>Status:</strong> {invoice_data.get('status', 'sent').title()}</p>
                    {f"<p><strong>Payment Terms:</strong> {invoice_data.get('payment_terms', 'N/A')}</p>" if invoice_data.get('payment_terms') else ""}
                </div>
                
                {items_html}
                
                <div class="amount-highlight">
                    <h3 style="margin: 0; color: #27ae60;">Total Tagihan: {total_amount}</h3>
                    <p style="margin: 5px 0 0 0; font-size: 16px;"><strong>Tagihan Jatuh Tempo: {amount_due}</strong></p>
                </div>
                
                <div class="payment-info">
                    <h4>Informasi Pembayaran:</h4>
                    {bank_info_html}
                    <p>Harap lakukan pembayaran sebelum <strong>{due_date}</strong> untuk menghindari denda keterlambatan.</p>
                    <p>Jika Anda memiliki pertanyaan tentang invoice ini atau perlu membahas pengaturan pembayaran, jangan ragu untuk menghubungi kami.</p>
                    {f"<p><strong>Catatan Tambahan:</strong> {invoice_data.get('notes')}</p>" if invoice_data.get('notes') else ""}
                </div>
                
                <p>Kami sangat menghargai kepercayaan anda terhadap produk dan layanan kami.</p>
                
                <p>Hormat kami,<br>
                <strong>{company_info.get('name', 'Your Company')}</strong><br>
                {f"Email: {company_info.get('email', '')}<br>" if company_info.get('email') else ""}
                </p>
            </div>
            
            <div class="footer">
                <p>This is an automated email.</p>
                <p>Please do not reply to this email directly.</p>
            </div>
        </body>
        </html>
        """
        
        message = MessageSchema(
            subject=f"Invoice #{invoice_data.get('invoice_number', 'N/A')} from {company_info.get('name', 'Your Company')}",
            recipients=[customer_email],
            body=html_content,
            subtype=MessageType.html
        )
        
        await fastmail.send_message(message)
        logger.info(f"Indonesian invoice email sent successfully to: {customer_email} for invoice #{invoice_data.get('invoice_number', 'N/A')}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send Indonesian invoice email to {customer_email}: {str(e)}")
        return False