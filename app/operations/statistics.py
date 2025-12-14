"""
Statistics Operations Module

This module provides business logic for calculating and aggregating
calculation statistics and usage metrics compatible with UUID-based
Calculation models using type/inputs structure.

Author: [Your Name]
Date: December 2025
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy import func, desc, and_
from sqlalchemy.orm import Session
from uuid import UUID
from app.models.calculation import Calculation


def calculate_user_statistics(db: Session, user_id: UUID) -> Dict:
    """
    Calculate comprehensive statistics for a user's calculations.
    
    Args:
        db: Database session
        user_id: UUID of the user to calculate statistics for
        
    Returns:
        Dict: Comprehensive statistics object
    """
    # Get all calculations for the user
    calculations = db.query(Calculation).filter(
        Calculation.user_id == user_id
    ).all()
    
    total_calculations = len(calculations)
    
    # Initialize statistics with default values
    if total_calculations == 0:
        return {
            "total_calculations": 0,
            "operations_breakdown": {},
            "average_inputs_count": None,
            "average_result": None,
            "most_used_operation": None,
            "recent_calculations": [],
            "calculations_by_day": {}
        }
    
    # Calculate operations breakdown
    operations_breakdown = {}
    result_sum = 0.0
    inputs_count_sum = 0
    
    for calc in calculations:
        # Count operations (normalize type names)
        operation = calc.type.lower()
        operations_breakdown[operation] = operations_breakdown.get(operation, 0) + 1
        
        # Sum results and input counts
        result_sum += calc.result
        inputs_count_sum += len(calc.inputs)
    
    # Calculate averages
    average_inputs_count = round(inputs_count_sum / total_calculations, 2)
    average_result = round(result_sum / total_calculations, 2)
    
    # Find most used operation
    most_used_operation = max(
        operations_breakdown.items(),
        key=lambda x: x[1]
    )[0] if operations_breakdown else None
    
    # Get recent calculations (last 10)
    recent_calculations = db.query(Calculation).filter(
        Calculation.user_id == user_id
    ).order_by(desc(Calculation.created_at)).limit(10).all()
    
    # Calculate daily breakdown for last 30 days
    calculations_by_day = get_calculations_by_day(db, user_id, days=30)
    
    return {
        "total_calculations": total_calculations,
        "operations_breakdown": operations_breakdown,
        "average_inputs_count": average_inputs_count,
        "average_result": average_result,
        "most_used_operation": most_used_operation,
        "recent_calculations": [
            {
                "id": str(calc.id),
                "type": calc.type,
                "inputs": calc.inputs,
                "result": calc.result,
                "created_at": calc.created_at.isoformat(),
                "updated_at": calc.updated_at.isoformat()
            }
            for calc in recent_calculations
        ],
        "calculations_by_day": calculations_by_day
    }


def get_calculations_by_day(
    db: Session, 
    user_id: UUID, 
    days: int = 30
) -> Dict[str, int]:
    """
    Get calculation counts grouped by day for trend analysis.
    
    Args:
        db: Database session
        user_id: UUID of the user
        days: Number of days to look back (default: 30)
        
    Returns:
        Dict mapping date strings (YYYY-MM-DD) to calculation counts
    """
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Query calculations grouped by date
    results = db.query(
        func.date(Calculation.created_at).label('date'),
        func.count(Calculation.id).label('count')
    ).filter(
        and_(
            Calculation.user_id == user_id,
            Calculation.created_at >= start_date,
            Calculation.created_at <= end_date
        )
    ).group_by(
        func.date(Calculation.created_at)
    ).all()
    
    # Convert to dictionary with string keys
    calculations_by_day = {
        str(result.date): result.count 
        for result in results
    }
    
    return calculations_by_day


def get_paginated_history(
    db: Session,
    user_id: UUID,
    page: int = 1,
    page_size: int = 10,
    operation_filter: Optional[str] = None
) -> Dict:
    """
    Get paginated calculation history with optional filtering.
    
    Args:
        db: Database session
        user_id: UUID of the user
        page: Page number (1-indexed)
        page_size: Number of items per page
        operation_filter: Optional operation type to filter by
        
    Returns:
        Dict: Paginated history object with metadata
    """
    # Validate pagination parameters
    if page < 1:
        raise ValueError("Page number must be >= 1")
    if page_size < 1 or page_size > 100:
        raise ValueError("Page size must be between 1 and 100")
    
    # Build base query
    query = db.query(Calculation).filter(Calculation.user_id == user_id)
    
    # Apply operation filter if provided
    if operation_filter:
        query = query.filter(
            func.lower(Calculation.type) == operation_filter.lower()
        )
    
    # Get total count for pagination
    total = query.count()
    
    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    
    # Get paginated results
    calculations = query.order_by(
        desc(Calculation.created_at)
    ).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    
    return {
        "calculations": [
            {
                "id": str(calc.id),
                "type": calc.type,
                "inputs": calc.inputs,
                "result": calc.result,
                "user_id": str(calc.user_id),
                "created_at": calc.created_at.isoformat(),
                "updated_at": calc.updated_at.isoformat()
            }
            for calc in calculations
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }


def get_operation_statistics(
    db: Session,
    user_id: UUID,
    operation: str
) -> Dict:
    """
    Get detailed statistics for a specific operation type.
    
    Args:
        db: Database session
        user_id: UUID of the user
        operation: Operation type to analyze
        
    Returns:
        Dictionary containing operation-specific statistics
    """
    calculations = db.query(Calculation).filter(
        and_(
            Calculation.user_id == user_id,
            func.lower(Calculation.type) == operation.lower()
        )
    ).all()
    
    if not calculations:
        return {
            'count': 0,
            'average_inputs_count': None,
            'average_result': None,
            'min_result': None,
            'max_result': None
        }
    
    result_values = [c.result for c in calculations]
    inputs_counts = [len(c.inputs) for c in calculations]
    
    return {
        'count': len(calculations),
        'average_inputs_count': round(sum(inputs_counts) / len(calculations), 2),
        'average_result': round(sum(result_values) / len(calculations), 2),
        'min_result': round(min(result_values), 2),
        'max_result': round(max(result_values), 2)
    }
