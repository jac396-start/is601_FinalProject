# app/main.py (patched excerpt with updated PUT route)
from datetime import datetime
from uuid import UUID
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user
from app.database import Base, get_db, engine
from app.models.calculation import Calculation
from app.schemas.calculation import CalculationBase, CalculationResponse, CalculationUpdate
from app.operations.calc_utils import compute_result

app = FastAPI(title="Calculations API", version="1.0.0")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/dashboard/edit/{calc_id}", response_class=HTMLResponse, tags=["web"])
def edit_calculation_page(request: Request, calc_id: str):
    return templates.TemplateResponse("edit_calculation.html", {"request": request, "calc_id": calc_id})

# Create
@app.post("/calculations", response_model=CalculationResponse, status_code=status.HTTP_201_CREATED, tags=["calculations"])
def create_calculation(
    calculation_data: CalculationBase,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    new_calc = Calculation.create(
        calculation_type=calculation_data.type,
        user_id=current_user.id,
        inputs=calculation_data.inputs,
    )
    new_calc.result = compute_result(new_calc.type, new_calc.inputs)
    db.add(new_calc)
    db.commit()
    db.refresh(new_calc)
    return new_calc

# List
@app.get("/calculations", response_model=List[CalculationResponse], tags=["calculations"])
def list_calculations(current_user = Depends(get_current_active_user), db: Session = Depends(get_db)):
    return db.query(Calculation).filter(Calculation.user_id == current_user.id).order_by(Calculation.created_at.desc()).all()

# Get
@app.get("/calculations/{calc_id}", response_model=CalculationResponse, tags=["calculations"])
def get_calculation(calc_id: str, current_user = Depends(get_current_active_user), db: Session = Depends(get_db)):
    try:
        calc_uuid = UUID(calc_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid calculation id format.")
    calc = db.query(Calculation).filter(Calculation.id == calc_uuid, Calculation.user_id == current_user.id).first()
    if not calc:
        raise HTTPException(status_code=404, detail="Calculation not found.")
    return calc

# UPDATED PUT ROUTE
@app.put("/calculations/{calc_id}", response_model=CalculationResponse, tags=["calculations"])
def update_calculation(
    calc_id: str,
    calculation_update: CalculationUpdate,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        calc_uuid = UUID(calc_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid calculation id format.")

    calc = db.query(Calculation).filter(Calculation.id == calc_uuid, Calculation.user_id == current_user.id).first()
    if not calc:
        raise HTTPException(status_code=404, detail="Calculation not found.")

    new_type = calculation_update.type or calc.type
    new_inputs = calculation_update.inputs or calc.inputs

    try:
        new_result = compute_result(new_type, new_inputs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    calc.type = new_type
    calc.inputs = new_inputs
    calc.result = new_result
    calc.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(calc)
    return calc

# Delete
@app.delete("/calculations/{calc_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["calculations"])
def delete_calculation(calc_id: str, current_user = Depends(get_current_active_user), db: Session = Depends(get_db)):
    try:
        calc_uuid = UUID(calc_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid calculation id format.")
    calc = db.query(Calculation).filter(Calculation.id == calc_uuid, Calculation.user_id == current_user.id).first()
    if not calc:
        raise HTTPException(status_code=404, detail="Calculation not found.")
    db.delete(calc)
    db.commit()
    return None

