"""
FastAPI Main Application Module

This module defines the main FastAPI application, including:
- Application initialization and configuration
- API endpoints for user authentication
- API endpoints for calculation management (BREAD operations)
- Web routes for HTML templates
- Database table creation on startup

The application follows a RESTful API design with proper separation of concerns:
- Routes handle HTTP requests and responses
- Models define database structure
- Schemas validate request/response data
- Dependencies handle authentication and database sessions
"""

from contextlib import asynccontextmanager  # Used for startup/shutdown events
from datetime import datetime, timezone, timedelta
from uuid import UUID  # For type validation of UUIDs in path parameters
from typing import List

# FastAPI imports
from fastapi import Body, FastAPI, Depends, HTTPException, status, Request, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles  # For serving static files (CSS, JS)
from fastapi.templating import Jinja2Templates  # For HTML templates

from sqlalchemy.orm import Session  # SQLAlchemy database session

import uvicorn  # ASGI server for running FastAPI apps

# Application imports
from app.auth.dependencies import get_current_active_user  # Authentication dependency
from app.models.calculation import Calculation  # Database model for calculations
from app.models.user import User  # Database model for users
from app.schemas.calculation import CalculationBase, CalculationResponse, CalculationUpdate  # API request/response schemas
from app.schemas.token import TokenResponse  # API token schema
from app.schemas.user import UserCreate, UserResponse, UserLogin  # User schemas
from app.database import Base, get_db, engine  # Database connection
from typing import List
from typing import List, Optional
from fastapi import Query, Path
from app.operations.statistics import (
    calculate_user_statistics,
    get_paginated_history,
    get_operation_statistics
)
# ------------------------------------------------------------------------------
# Create tables on startup using the lifespan event
# ------------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI.
    
    This runs when the application starts and creates all database tables
    defined in SQLAlchemy models. It's an alternative to using Alembic
    for simpler applications.
    
    Args:
        app: FastAPI application instance
    """
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!")
    yield  # This is where application runs
    # Cleanup code would go here (after yield), but we don't need any

# Initialize the FastAPI application with metadata and lifespan
app = FastAPI(
    title="Calculations API",
    description="API for managing calculations",
    version="1.0.0",
    lifespan=lifespan  # Pass our lifespan context manager
)

# ------------------------------------------------------------------------------
# Static Files and Templates Configuration
# ------------------------------------------------------------------------------
# Mount the static files directory for serving CSS, JS, and images
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up Jinja2 templates directory for HTML rendering
templates = Jinja2Templates(directory="templates")


# ------------------------------------------------------------------------------
# Web (HTML) Routes
# ------------------------------------------------------------------------------
# Our web routes use HTML responses with Jinja2 templates
# These provide a user-friendly web interface alongside the API

@app.get("/", response_class=HTMLResponse, tags=["web"])
def read_index(request: Request):
    """
    Landing page.
    
    Displays the welcome page with links to register and login.
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse, tags=["web"])
def login_page(request: Request):
    """
    Login page.
    
    Displays a form for users to enter credentials and log in.
    """
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse, tags=["web"])
def register_page(request: Request):
    """
    Registration page.
    
    Displays a form for new users to create an account.
    """
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse, tags=["web"])
def dashboard_page(request: Request):
    """
    Dashboard page, listing calculations & new calculation form.
    
    This is the main interface after login, where users can:
    - See all their calculations
    - Create a new calculation
    - Access links to view/edit/delete calculations
    
    JavaScript in this page calls the API endpoints to fetch and display data.
    """
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/dashboard/view/{calc_id}", response_class=HTMLResponse, tags=["web"])
def view_calculation_page(request: Request, calc_id: str):
    """
    Page for viewing a single calculation (Read).
    
    Part of the BREAD (Browse, Read, Edit, Add, Delete) pattern:
    - This is the Read page
    
    Args:
        request: The FastAPI request object (required by Jinja2)
        calc_id: UUID of the calculation to view
        
    Returns:
        HTMLResponse: Rendered template with calculation ID passed to frontend
    """
    return templates.TemplateResponse("view_calculation.html", {"request": request, "calc_id": calc_id})

@app.get("/dashboard/edit/{calc_id}", response_class=HTMLResponse, tags=["web"])
def edit_calculation_page(request: Request, calc_id: str):
    """
    Page for editing a calculation (Update).
    
    Part of the BREAD (Browse, Read, Edit, Add, Delete) pattern:
    - This is the Edit page
    
    Args:
        request: The FastAPI request object (required by Jinja2)
        calc_id: UUID of the calculation to edit
        
    Returns:
        HTMLResponse: Rendered template with calculation ID passed to frontend
    """
    return templates.TemplateResponse("edit_calculation.html", {"request": request, "calc_id": calc_id})

"""
Statistics and History API Routes

ADD these routes to your existing app/main.py file.

INTEGRATION STEPS:
1. Add these imports at the top of main.py (after your existing imports)
2. Add these route definitions after your existing calculation routes
3. Create app/operations/statistics.py with the statistics operations code

Author: [Your Name]
Date: December 2025
"""

# ========== ADD THESE IMPORTS AT TOP OF main.py ==========
from app.operations.statistics import (
    calculate_user_statistics,
    get_paginated_history,
    get_operation_statistics
)
from typing import Optional
from fastapi import Query, Path


# ========== ADD THESE ROUTES AFTER YOUR EXISTING CALCULATION ROUTES ==========

@app.get(
    "/api/statistics",
    tags=["statistics"],
    summary="Get User Statistics",
    description="Retrieve comprehensive calculation statistics for the authenticated user"
)
def get_statistics(
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive statistics for current user's calculations.
    
    Returns detailed metrics including totals, averages, breakdowns,
    and trends to support the Report/History dashboard feature.
    
    Returns:
        Dict: Comprehensive statistics object including:
            - total_calculations: Total count
            - operations_breakdown: Count by type
            - average_inputs_count: Average number of inputs
            - average_result: Average result value
            - most_used_operation: Most frequent operation
            - recent_calculations: Last 10 calculations
            - calculations_by_day: Daily trends for last 30 days
    """
    try:
        statistics = calculate_user_statistics(db, current_user.id)
        return JSONResponse(content=statistics)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating statistics: {str(e)}"
        )


@app.get(
    "/api/history",
    tags=["statistics"],
    summary="Get Calculation History",
    description="Retrieve paginated calculation history with optional filtering"
)
def get_history(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    operation: Optional[str] = Query(None, description="Filter by operation type"),
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get paginated calculation history for current user.
    
    Supports pagination and filtering to efficiently browse large
    calculation histories. Orders results by creation date (newest first).
    
    Args:
        page: Page number to retrieve (1-indexed)
        page_size: Number of items per page (1-100)
        operation: Optional filter for operation type
        
    Returns:
        Dict: Paginated history with metadata including:
            - calculations: List of calculation objects
            - total: Total count matching filters
            - page: Current page number
            - page_size: Items per page
            - total_pages: Total number of pages
    """
    try:
        history = get_paginated_history(
            db=db,
            user_id=current_user.id,
            page=page,
            page_size=page_size,
            operation_filter=operation
        )
        return JSONResponse(content=history)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving history: {str(e)}"
        )


@app.get(
    "/api/statistics/operation/{operation}",
    tags=["statistics"],
    summary="Get Operation-Specific Statistics",
    description="Get detailed statistics for a specific operation type"
)
def get_operation_stats(
    operation: str = Path(..., description="Operation type to analyze"),
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed statistics for a specific operation type.
    
    Provides operation-specific metrics including counts, averages,
    and ranges to support detailed analysis.
    
    Args:
        operation: Type of operation to analyze (addition, subtraction, etc.)
        
    Returns:
        Dict: Operation-specific statistics including:
            - count: Number of calculations of this type
            - average_inputs_count: Average number of inputs used
            - average_result: Average result value
            - min_result: Minimum result value
            - max_result: Maximum result value
    """
    try:
        stats = get_operation_statistics(db, current_user.id, operation)
        return JSONResponse(content=stats)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving operation statistics: {str(e)}"
        )


# ========== ADD THIS HTML ROUTE FOR REPORTS PAGE ==========

@app.get("/reports", response_class=HTMLResponse, tags=["web"])
def reports_page(request: Request):
    """
    Render the Reports/Statistics page.
    
    Displays comprehensive analytics dashboard with charts,
    statistics, and calculation history.
    
    Note: Authentication is handled client-side via JavaScript
    """
    return templates.TemplateResponse("reports.html", {"request": request})
# ------------------------------------------------------------------------------
# Health Endpoint
# ------------------------------------------------------------------------------
@app.get("/health", tags=["health"])
def read_health():
    """Health check."""
    return {"status": "ok"}


# ------------------------------------------------------------------------------
# User Registration Endpoint
# ------------------------------------------------------------------------------
@app.post(
    "/auth/register", 
    response_model=UserResponse, 
    status_code=status.HTTP_201_CREATED,
    tags=["auth"]
)
def register(user_create: UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user account.
    """
    user_data = user_create.dict(exclude={"confirm_password"})
    try:
        user = User.register(db, user_data)
        db.commit()
        db.refresh(user)
        return user
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ------------------------------------------------------------------------------
# User Login Endpoints
# ------------------------------------------------------------------------------

@app.post("/auth/login", response_model=TokenResponse, tags=["auth"])
def login_json(user_login: UserLogin, db: Session = Depends(get_db)):
    """
    Login with JSON payload (username & password).
    Returns an access token, refresh token, and user info.
    """
    auth_result = User.authenticate(db, user_login.username, user_login.password)
    if auth_result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = auth_result["user"]
    db.commit()  # commit the last_login update

    # Ensure expires_at is timezone-aware
    expires_at = auth_result.get("expires_at")
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    else:
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

    return TokenResponse(
        access_token=auth_result["access_token"],
        refresh_token=auth_result["refresh_token"],
        token_type="bearer",
        expires_at=expires_at,
        user_id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_active=user.is_active,
        is_verified=user.is_verified
    )

@app.post("/auth/token", tags=["auth"])
def login_form(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Login with form data (Swagger/UI).
    Returns an access token.
    """
    auth_result = User.authenticate(db, form_data.username, form_data.password)
    if auth_result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "access_token": auth_result["access_token"],
        "token_type": "bearer"
    }


# ------------------------------------------------------------------------------
# Calculations Endpoints (BREAD)
# ------------------------------------------------------------------------------
# Create (Add) Calculation
@app.post(
    "/calculations",
    response_model=CalculationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["calculations"],
)
def create_calculation(
    calculation_data: CalculationBase,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new calculation for the authenticated user.
    Automatically computes the 'result'.
    """
    try:
        new_calculation = Calculation.create(
            calculation_type=calculation_data.type,
            user_id=current_user.id,
            inputs=calculation_data.inputs,
        )
        new_calculation.result = new_calculation.get_result()

        db.add(new_calculation)
        db.commit()
        db.refresh(new_calculation)
        return new_calculation

    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# Browse / List Calculations
@app.get("/calculations", response_model=List[CalculationResponse], tags=["calculations"])
def list_calculations(
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List all calculations belonging to the current authenticated user.
    """
    calculations = db.query(Calculation).filter(Calculation.user_id == current_user.id).all()
    return calculations


# Read / Retrieve a Specific Calculation by ID
@app.get("/calculations/{calc_id}", response_model=CalculationResponse, tags=["calculations"])
def get_calculation(
    calc_id: str,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve a single calculation by its UUID, if it belongs to the current user.
    """
    try:
        calc_uuid = UUID(calc_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid calculation id format.")

    calculation = db.query(Calculation).filter(
        Calculation.id == calc_uuid,
        Calculation.user_id == current_user.id
    ).first()
    if not calculation:
        raise HTTPException(status_code=404, detail="Calculation not found.")

    return calculation


# Edit / Update a Calculation
@app.put("/calculations/{calc_id}", response_model=CalculationResponse, tags=["calculations"])
def update_calculation(
    calc_id: str,
    calculation_update: CalculationUpdate,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update the inputs (and thus the result) of a specific calculation.
    """
    try:
        calc_uuid = UUID(calc_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid calculation id format.")

    calculation = db.query(Calculation).filter(
        Calculation.id == calc_uuid,
        Calculation.user_id == current_user.id
    ).first()
    if not calculation:
        raise HTTPException(status_code=404, detail="Calculation not found.")

    if calculation_update.inputs is not None:
        calculation.inputs = calculation_update.inputs
        calculation.result = calculation.get_result()

    calculation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(calculation)
    return calculation


# Delete a Calculation
@app.delete("/calculations/{calc_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["calculations"])
def delete_calculation(
    calc_id: str,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a calculation by its UUID, if it belongs to the current user.
    """
    try:
        calc_uuid = UUID(calc_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid calculation id format.")

    calculation = db.query(Calculation).filter(
        Calculation.id == calc_uuid,
        Calculation.user_id == current_user.id
    ).first()
    if not calculation:
        raise HTTPException(status_code=404, detail="Calculation not found.")

    db.delete(calculation)
    db.commit()
    return None

# ------------------------------------------------------------------------------
# Statistics and History Endpoints (Reports Feature)
# ------------------------------------------------------------------------------
@app.get(
    "/api/statistics",
    tags=["statistics"],
    summary="Get User Statistics"
)
def get_statistics(
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive statistics for current user's calculations.

    Returns detailed metrics including totals, averages, breakdowns,
    and trends to support the Report/History dashboard feature.
    """
    try:
        statistics = calculate_user_statistics(db, current_user.id)
        return JSONResponse(content=statistics)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating statistics: {str(e)}"
        )


@app.get(
    "/api/history",
    tags=["statistics"],
    summary="Get Calculation History"
)
def get_history(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    operation: Optional[str] = Query(None, description="Filter by operation type"),
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get paginated calculation history for current user.

    Supports pagination and filtering to efficiently browse large
    calculation histories. Orders results by creation date (newest first).
    """
    try:
        history = get_paginated_history(
            db=db,
            user_id=current_user.id,
            page=page,
            page_size=page_size,
            operation_filter=operation
        )
        return JSONResponse(content=history)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving history: {str(e)}"
        )


@app.get(
    "/api/statistics/operation/{operation}",
    tags=["statistics"],
    summary="Get Operation-Specific Statistics"
)
def get_operation_stats(
    operation: str = Path(..., description="Operation type to analyze"),
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed statistics for a specific operation type.
    """
    try:
        stats = get_operation_statistics(db, current_user.id, operation)
        return JSONResponse(content=stats)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving operation statistics: {str(e)}"
        )


@app.get("/reports", response_class=HTMLResponse, tags=["web"])
def reports_page(request: Request):
    """
    Render the Reports/Statistics page.

    Displays comprehensive analytics dashboard with charts,
    statistics, and calculation history.
    """
    return templates.TemplateResponse("reports.html", {"request": request})

# ------------------------------------------------------------------------------
# Main Block to Run the Server
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, log_level="info")
