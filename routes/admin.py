from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
import os
from datetime import datetime, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv

from database.database import get_db
from models.user import User
from models.document import Document
from models.quiz_attempt import QuizAttempt
from schemas.user import UserResponse
from utils.dependencies import get_current_user

load_dotenv()

router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])

# Ensure only admin can access these routes
def check_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized, admin only")
    return current_user

# --- User Management ---
@router.get("/users", response_model=List[UserResponse])
def get_all_users(current_user: User = Depends(check_admin), db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users

@router.put("/users/{user_id}/role")
def update_user_role(user_id: int, role: str, current_user: User = Depends(check_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if role not in ["admin", "user", "guru"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    user.role = role
    db.commit()
    db.refresh(user)
    return {"message": "Role updated successfully", "role": user.role}

@router.get("/users/{user_id}/activity")
def get_user_activity(user_id: int, current_user: User = Depends(check_admin)):
    activity_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "activity.log")
    activities = []
    if os.path.exists(activity_file):
        with open(activity_file, "r") as f:
            for line in f:
                if f"user_id={user_id} |" in line or f"user_id={user_id}" in line:
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 3:
                        time_str = parts[0]
                        action = ""
                        detail = ""
                        for part in parts:
                            if part.startswith("action="):
                                action = part.replace("action=", "")
                            elif part.startswith("detail="):
                                detail = part.replace("detail=", "")
                                
                        activities.append({
                            "time": time_str,
                            "action": action,
                            "detail": detail
                        })
    # Return last 50 activities descending
    return activities[::-1][:50]

# --- Application DB Analytics (PostgreSQL) ---
@router.get("/analytics/appdata")
def get_app_analytics(period: str = "all", current_user: User = Depends(check_admin), db: Session = Depends(get_db)):
    threshold_date = None
    date_format = 'YYYY-MM'
    
    if period == "7d":
        threshold_date = datetime.utcnow() - timedelta(days=7)
        date_format = 'YYYY-MM-DD'
    elif period == "30d":
        threshold_date = datetime.utcnow() - timedelta(days=30)
        date_format = 'YYYY-MM-DD'
    elif period == "90d":
        threshold_date = datetime.utcnow() - timedelta(days=90)
        date_format = 'YYYY-MM-DD'

    def apply_filter(query, date_column):
        if threshold_date:
            return query.filter(date_column >= threshold_date)
        return query

    total_users = apply_filter(db.query(User), User.created_at).count()
    total_documents = apply_filter(db.query(Document), Document.created_at).count()
    total_quiz_attempts = apply_filter(db.query(QuizAttempt), QuizAttempt.completed_at).count()
    
    # User roles breakdown
    role_query = apply_filter(db.query(User.role, func.count(User.id)), User.created_at).group_by(User.role)
    role_counts = role_query.all()
    role_breakdown = [{"name": r[0] if r[0] else "user", "value": r[1]} for r in role_counts]
    if not role_breakdown:
        role_breakdown = [{"name": "user", "value": 0}, {"name": "admin", "value": 0}]
    
    # 1. User Growth Over Time
    user_growth_query = db.query(
        func.to_char(User.created_at, date_format).label('date'),
        func.count(User.id)
    ).filter(User.created_at.isnot(None))
    user_growth_query = apply_filter(user_growth_query, User.created_at).group_by('date').order_by('date')
    user_growth = [{"date": r[0], "users": r[1]} for r in user_growth_query.all()]
    
    # 2. Quiz Attempts & Average Score Trend
    quiz_trend_query = db.query(
        func.to_char(QuizAttempt.completed_at, date_format).label('date'),
        func.count(QuizAttempt.id),
        func.avg(QuizAttempt.total_score)
    ).filter(QuizAttempt.completed_at.isnot(None))
    quiz_trend_query = apply_filter(quiz_trend_query, QuizAttempt.completed_at).group_by('date').order_by('date')
    quiz_trend = [{"date": r[0], "attempts": r[1], "avg_score": round(r[2] or 0, 2)} for r in quiz_trend_query.all()]
    
    # 3. Peak Activity Times
    peak_times_query = db.query(
        func.extract('hour', QuizAttempt.completed_at).label('hour'),
        func.count(QuizAttempt.id)
    ).filter(QuizAttempt.completed_at.isnot(None))
    peak_times_query = apply_filter(peak_times_query, QuizAttempt.completed_at).group_by('hour').order_by('hour')
    peak_times = [{"hour": f"{int(r[0]):02d}:00", "activity": r[1]} for r in peak_times_query.all()]

    return {
        "summary": {
            "total_users": total_users,
            "total_documents": total_documents,
            "total_quiz_attempts": total_quiz_attempts
        },
        "role_breakdown": role_breakdown,
        "user_growth": user_growth,
        "quiz_trend": quiz_trend,
        "peak_times": peak_times
    }

# --- Document Management ---
@router.get("/documents")
def get_all_documents(current_user: User = Depends(check_admin), db: Session = Depends(get_db)):
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    items = []
    for d in docs:
        owner = db.query(User).filter(User.id == d.user_id).first()
        items.append({
            "id": d.id,
            "title": d.title,
            "owner_name": owner.full_name if owner else "Unknown",
            "owner_email": owner.email if owner else "",
            "status": d.status.value if d.status else "processing",
            "created_at": d.created_at,
            "total_pages": d.total_pages,
            "chapters_count": len(d.chapters) if d.chapters else 0
        })
    return items

# --- Big Data Analytics (MongoDB) ---
@router.get("/analytics/bigdata")
def get_bigdata_analytics(current_user: User = Depends(check_admin)):
    mongo_url = os.environ.get("MONGODB_URL")
    if not mongo_url:
        raise HTTPException(status_code=500, detail="MongoDB URL not configured")
    
    try:
        client = MongoClient(mongo_url)
        db = client.latihanbigdata
        collection = db.sampledata
        
        # Example aggregation: Average literacy rate by year for global data (filtered for years 2000-2023)
        pipeline_yearly = [
            {"$match": {"year": {"$gte": "2000", "$lte": "2023"}, "value": {"$gte": 0}}},
            {"$group": {"_id": "$year", "avg_literacy": {"$avg": "$value"}}},
            {"$sort": {"_id": 1}}
        ]
        yearly_data = list(collection.aggregate(pipeline_yearly))
        
        # Example aggregation: Average literacy by top countries (filter out aggregates roughly)
        pipeline_countries = [
            {"$match": {"country_name": {"$not": {"$in": ["World", "High income", "Low income", "Europe", "Africa", "Asia"]}}, "value": {"$gte": 0}}},
            {"$group": {"_id": "$country_name", "avg_literacy": {"$avg": "$value"}}},
            {"$sort": {"avg_literacy": -1}},
            {"$limit": 10}
        ]
        country_data = list(collection.aggregate(pipeline_countries))
        
        import math
        def clean_val(val):
            if val is None: return 0
            if isinstance(val, float) and math.isnan(val): return 0
            return val
            
        return {
            "yearly_trend": [{"year": item["_id"], "rate": clean_val(item.get("avg_literacy"))} for item in yearly_data if item["_id"] is not None],
            "top_countries": [{"country": item["_id"], "rate": clean_val(item.get("avg_literacy"))} for item in country_data if item["_id"] is not None]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'client' in locals():
            client.close()
