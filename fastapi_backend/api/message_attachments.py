from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import os
import uuid

from database.connection import get_db
from core.security import get_current_user
from models.conversation import ConversationParticipant
from models.message import Message, MessageResponse
from models.user import User
from models.file_upload import FileUpload
from services.notification_service import NotificationService
import logging

logger = logging.getLogger(__name__)

message_attachments_router = APIRouter()


@message_attachments_router.post("/send-file", response_model=MessageResponse)
async def send_file_message(
    conversation_id: int = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a file as a message"""
    try:
        # Check if user is participant
        participant = db.query(ConversationParticipant).filter(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.user_id == current_user.id
        ).first()

        if not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to send files to this conversation"
            )

        # Save file
        upload_dir = f"uploads/messages/{conversation_id}"
        os.makedirs(upload_dir, exist_ok=True)

        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(upload_dir, unique_filename)

        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Create file upload record
        file_upload = FileUpload(
            filename=unique_filename,
            original_filename=file.filename,
            file_path=file_path,
            file_size=len(content),
            file_type="message_attachment",
            mime_type=file.content_type,
            uploaded_by=current_user.id
        )

        db.add(file_upload)
        db.commit()
        db.refresh(file_upload)

        # Create message with file attachment
        message = Message(
            conversation_id=conversation_id,
            sender_id=current_user.id,
            content=f"File attachment: {file.filename}",
            message_type="file",
            message_metadata={
                "file_id": file_upload.id,
                "filename": file.filename,
                "file_size": len(content),
                "mime_type": file.content_type
            },
            created_at=datetime.utcnow()
        )

        db.add(message)
        db.commit()
        db.refresh(message)

        # Notify other participants
        try:
            other_participants = db.query(ConversationParticipant).filter(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id != current_user.id
            ).all()

            for participant in other_participants:
                await NotificationService.notify_new_message(
                    db=db,
                    user_id=participant.user_id,
                    message_id=message.id,
                    sender_name=current_user.username
                )
        except Exception as e:
            logger.error(f"Error sending file message notifications: {e}")

        return MessageResponse.from_orm(message)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending file message: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error sending file message"
        )


@message_attachments_router.get("/messages/{message_id}/download-file")
async def download_message_file(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download file attachment from a message"""
    try:
        message = db.query(Message).filter(Message.id == message_id).first()
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )

        # Check if user is participant
        participant = db.query(ConversationParticipant).filter(
            ConversationParticipant.conversation_id == message.conversation_id,
            ConversationParticipant.user_id == current_user.id
        ).first()

        if not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to download this file"
            )

        # Check if message has file attachment
        if message.message_type != "file" or not message.message_metadata:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message does not contain a file attachment"
            )

        file_id = message.message_metadata.get("file_id")
        if not file_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File attachment not found"
            )

        file_upload = db.query(FileUpload).filter(FileUpload.id == file_id).first()
        if not file_upload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )

        # Check if file exists on disk
        if not os.path.exists(file_upload.file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Physical file not found"
            )

        from fastapi.responses import FileResponse
        return FileResponse(
            path=file_upload.file_path,
            filename=file_upload.original_filename,
            media_type=file_upload.mime_type
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error downloading file"
        )


@message_attachments_router.get("/messages/{message_id}/file-info")
async def get_message_file_info(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get file attachment information from a message"""
    try:
        message = db.query(Message).filter(Message.id == message_id).first()
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )

        # Check if user is participant
        participant = db.query(ConversationParticipant).filter(
            ConversationParticipant.conversation_id == message.conversation_id,
            ConversationParticipant.user_id == current_user.id
        ).first()

        if not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this file information"
            )

        if message.message_type != "file" or not message.message_metadata:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message does not contain a file attachment"
            )

        return {
            "message_id": message.id,
            "filename": message.message_metadata.get("filename"),
            "file_size": message.message_metadata.get("file_size"),
            "mime_type": message.message_metadata.get("mime_type"),
            "file_id": message.message_metadata.get("file_id")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving file information"
        )