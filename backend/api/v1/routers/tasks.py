import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from core.database import get_db
from api.v1.routers.auth import get_current_user
from models.memory import Task

router = APIRouter(prefix="/tasks", tags=["tasks"])

PRIORITY_MAP = {"critique": 1, "haute": 2, "normale": 3, "basse": 4}
PRIORITY_LABELS = {v: k for k, v in PRIORITY_MAP.items()}
VALID_STATUSES = {"todo", "in_progress", "done"}


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = "normale"
    status: str = "todo"
    due_date: Optional[datetime] = None
    project_id: Optional[uuid.UUID] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[datetime] = None
    project_id: Optional[uuid.UUID] = None


class TaskResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str]
    priority: str
    status: str
    due_date: Optional[str]
    project_id: Optional[uuid.UUID]
    created_at: str


def _serialize(t: Task) -> TaskResponse:
    return TaskResponse(
        id=t.id,
        title=t.title,
        description=t.description,
        priority=PRIORITY_LABELS.get(t.priority, "normale"),
        status=t.status,
        due_date=t.due_date.isoformat() if t.due_date else None,
        project_id=t.project_id,
        created_at=t.created_at.isoformat(),
    )


@router.get("/", response_model=list[TaskResponse])
async def list_tasks(
    status: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Task).where(Task.user_id == current_user.id).order_by(Task.priority.asc(), Task.due_date.asc().nullslast())
    if status:
        q = q.where(Task.status == status)
    result = await db.execute(q)
    return [_serialize(t) for t in result.scalars().all()]


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    body: TaskCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.priority not in PRIORITY_MAP:
        raise HTTPException(status_code=422, detail=f"Priorité invalide. Valeurs : {list(PRIORITY_MAP)}")
    if body.status not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail=f"Statut invalide. Valeurs : {list(VALID_STATUSES)}")
    task = Task(
        id=uuid.uuid4(),
        user_id=current_user.id,
        title=body.title,
        description=body.description,
        priority=PRIORITY_MAP[body.priority],
        status=body.status,
        due_date=body.due_date,
        project_id=body.project_id,
    )
    db.add(task)
    await db.commit()
    return _serialize(task)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: uuid.UUID,
    body: TaskUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Task).where(Task.id == task_id, Task.user_id == current_user.id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Tâche introuvable")
    if body.title is not None:
        task.title = body.title
    if body.description is not None:
        task.description = body.description
    if body.priority is not None:
        if body.priority not in PRIORITY_MAP:
            raise HTTPException(status_code=422, detail="Priorité invalide")
        task.priority = PRIORITY_MAP[body.priority]
    if body.status is not None:
        if body.status not in VALID_STATUSES:
            raise HTTPException(status_code=422, detail="Statut invalide")
        task.status = body.status
    if body.due_date is not None:
        task.due_date = body.due_date
    if body.project_id is not None:
        task.project_id = body.project_id
    await db.commit()
    return _serialize(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Task).where(Task.id == task_id, Task.user_id == current_user.id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Tâche introuvable")
    await db.delete(task)
    await db.commit()
