from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from database.connection import get_db
from core.security import get_current_user
from models.user import User
from services.secure_messaging_service import secure_messaging_service
from services.audit_service import audit_service
from services.dot_service import DOTService

router = APIRouter(prefix="/api/secure-messaging", tags=["secure-messaging"])

# Request/Response Models

class SecureConversationCreateRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    participant_ids: List[int] = Field(..., min_items=1, max_items=50)
    conversation_type: str = Field("group", pattern="^(direct|group)$")
    metadata: Optional[Dict[str, Any]] = None

class SecureMessageSendRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)
    message_type: str = Field("text", pattern="^(text|file|image|document)$")
    metadata: Optional[Dict[str, Any]] = None
    reply_to_id: Optional[int] = None

class MessageEditRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)

class ConversationResponse(BaseModel):
    id: int
    name: Optional[str]
    conversation_type: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    participant_count: int
    created_by: int

class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender_id: int
    sender_username: str
    content: str
    message_type: str
    metadata: Dict[str, Any]
    is_edited: bool
    is_deleted: bool
    created_at: str
    updated_at: Optional[str]

# Conversation Endpoints

@router.post("/conversations", response_model=dict)
async def create_secure_conversation(
    request: SecureConversationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new secure conversation with DOT-based validation"""
    try:
        # Audit log the attempt
        audit_service.log_activity(
            db=db,
            user_id=current_user.id,
            action="conversation_create_attempt",
            resource_type="conversation",
            details=f"Attempting to create conversation with {len(request.participant_ids)} participants"
        )

        conversation = secure_messaging_service.create_secure_conversation(
            db=db,
            creator_id=current_user.id,
            participant_ids=request.participant_ids,
            name=request.name,
            conversation_type=request.conversation_type,
            metadata=request.metadata
        )

        if not conversation:
            raise HTTPException(
                status_code=400,
                detail="Failed to create conversation. Check participant permissions."
            )

        return {
            "success": True,
            "conversation_id": conversation.id,
            "name": conversation.name,
            "conversation_type": conversation.conversation_type,
            "created_at": conversation.created_at.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        audit_service.log_activity(
            db=db,
            user_id=current_user.id,
            action="conversation_create_failed",
            resource_type="conversation",
            details=f"Failed to create conversation: {str(e)}",
            severity="error"
        )
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/conversations", response_model=List[ConversationResponse])
async def get_accessible_conversations(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get conversations accessible to user with DOT filtering"""
    try:
        conversations = secure_messaging_service.get_user_accessible_conversations(
            db=db,
            user_id=current_user.id,
            limit=limit,
            offset=offset
        )

        # Format response
        formatted_conversations = []
        for conv in conversations:
            # Get participant count
            from models.conversation import ConversationParticipant
            participant_count = db.query(ConversationParticipant).filter(
                ConversationParticipant.conversation_id == conv.id
            ).count()

            formatted_conversations.append(ConversationResponse(
                id=conv.id,
                name=conv.name,
                conversation_type=conv.conversation_type,
                is_active=conv.is_active,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                participant_count=participant_count,
                created_by=conv.created_by
            ))

        audit_service.log_activity(
            db=db,
            user_id=current_user.id,
            action="conversations_accessed",
            resource_type="conversation",
            details=f"Accessed {len(formatted_conversations)} conversations"
        )

        return formatted_conversations

    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve conversations")

@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: int,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get messages from conversation with decryption"""
    try:
        messages = secure_messaging_service.get_conversation_messages(
            db=db,
            user_id=current_user.id,
            conversation_id=conversation_id,
            limit=limit,
            offset=offset
        )

        return [MessageResponse(**msg) for msg in messages]

    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve messages")

# Message Endpoints

@router.post("/conversations/{conversation_id}/messages", response_model=dict)
async def send_secure_message(
    conversation_id: int,
    request: SecureMessageSendRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send encrypted message to conversation"""
    try:
        message = secure_messaging_service.send_secure_message(
            db=db,
            sender_id=current_user.id,
            conversation_id=conversation_id,
            content=request.content,
            message_type=request.message_type,
            metadata=request.metadata,
            reply_to_id=request.reply_to_id
        )

        if not message:
            raise HTTPException(status_code=400, detail="Failed to send message")

        return {
            "success": True,
            "message_id": message.id,
            "conversation_id": conversation_id,
            "created_at": message.created_at.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to send message")

@router.put("/messages/{message_id}", response_model=dict)
async def edit_message(
    message_id: int,
    request: MessageEditRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Edit message content"""
    try:
        success = secure_messaging_service.edit_message(
            db=db,
            user_id=current_user.id,
            message_id=message_id,
            new_content=request.content
        )

        if not success:
            raise HTTPException(status_code=400, detail="Failed to edit message")

        return {
            "success": True,
            "message_id": message_id,
            "edited_at": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to edit message")

@router.delete("/messages/{message_id}", response_model=dict)
async def delete_message(
    message_id: int,
    hard_delete: bool = Query(False, description="Permanently delete message"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete message (soft or hard delete)"""
    try:
        success = secure_messaging_service.delete_message_securely(
            db=db,
            user_id=current_user.id,
            message_id=message_id,
            hard_delete=hard_delete
        )

        if not success:
            raise HTTPException(status_code=400, detail="Failed to delete message")

        return {
            "success": True,
            "message_id": message_id,
            "deleted_at": datetime.utcnow().isoformat(),
            "hard_delete": hard_delete
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to delete message")

# DOT-based endpoints

@router.get("/users/accessible", response_model=List[dict])
async def get_accessible_users(
    search: Optional[str] = Query(None, max_length=50),
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get users accessible for messaging based on DOT permissions"""
    try:
        # Get user's accessible DOTs
        accessible_dots = DOTService.get_user_accessible_dots(db, current_user.id)

        if not accessible_dots and not (current_user.is_superuser or current_user.is_staff):
            return []

        # Build query for accessible users
        query = db.query(User).filter(User.is_active == True, User.id != current_user.id)

        # Filter by DOT access for regular users
        if not (current_user.is_superuser or current_user.is_staff):
            query = query.filter(User.dot_id.in_(accessible_dots))

        # Apply search filter
        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                (User.username.ilike(search_filter)) |
                (User.first_name.ilike(search_filter)) |
                (User.last_name.ilike(search_filter))
            )

        users = query.limit(limit).all()

        # Format response
        accessible_users = []
        for user in users:
            dot_info = None
            if user.dot:
                dot_info = {
                    "id": user.dot.id,
                    "name": user.dot.name
                }

            accessible_users.append({
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "dot": dot_info
            })

        return accessible_users

    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve accessible users")

@router.get("/conversations/{conversation_id}/participants", response_model=List[dict])
async def get_conversation_participants(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get conversation participants"""
    try:
        # Check access to conversation
        if not secure_messaging_service.can_user_access_conversation(db, current_user.id, conversation_id):
            raise HTTPException(status_code=403, detail="Access denied to this conversation")

        # Get participants
        from models.conversation import ConversationParticipant
        participants = db.query(ConversationParticipant).filter(
            ConversationParticipant.conversation_id == conversation_id
        ).all()

        # Get user details for participants
        participant_users = db.query(User).filter(
            User.id.in_([p.user_id for p in participants])
        ).all()

        # Format response
        formatted_participants = []
        for user in participant_users:
            participant_record = next((p for p in participants if p.user_id == user.id), None)

            dot_info = None
            if user.dot:
                dot_info = {
                    "id": user.dot.id,
                    "name": user.dot.name
                }

            formatted_participants.append({
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_admin": participant_record.is_admin if participant_record else False,
                "joined_at": participant_record.joined_at.isoformat() if participant_record else None,
                "dot": dot_info
            })

        return formatted_participants

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve participants")

# Security endpoints

@router.get("/security/my-activity", response_model=List[dict])
async def get_my_messaging_activity(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    action_filter: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's messaging activity logs"""
    try:
        logs = audit_service.get_user_activity_logs(
            db=db,
            user_id=current_user.id,
            limit=limit,
            offset=offset,
            action_filter=action_filter
        )

        # Filter for messaging-related actions
        messaging_actions = [
            'conversation_created', 'conversation_accessed', 'message_sent',
            'message_edited', 'message_deleted', 'messages_accessed'
        ]

        filtered_logs = [log for log in logs if log.action in messaging_actions]

        formatted_logs = []
        for log in filtered_logs:
            formatted_logs.append({
                "id": log.id,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "details": log.details,
                "severity": log.severity,
                "created_at": log.created_at.isoformat()
            })

        return formatted_logs

    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve activity logs")