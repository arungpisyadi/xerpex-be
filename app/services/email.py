"""
Email service for the XerpeX ERP System
"""
import logging
from typing import List, Optional
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr

from app.config import settings

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