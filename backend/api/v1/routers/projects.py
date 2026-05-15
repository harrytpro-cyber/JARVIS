import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from core.database import get_db
from api.v1.routers.auth import get_current_user
from models.memory import Project

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str
    summary: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    summary: Optional[str] = None
    status: Optional[str] = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    summary: Optional[str]
    status: str
    created_at: str
    updated_at: str


def _serialize(p: Project) -> ProjectResponse:
    return ProjectResponse(
        id=p.id, name=p.name, summary=p.summary, status=p.status,
        created_at=p.created_at.isoformat(), updated_at=p.updated_at.isoformat(),
    )


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(
    include_archived: bool = False,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Project).where(Project.user_id == current_user.id).order_by(Project.updated_at.desc())
    if not include_archived:
        q = q.where(Project.status != "archived")
    result = await db.execute(q)
    return [_serialize(p) for p in result.scalars().all()]


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = Project(id=uuid.uuid4(), user_id=current_user.id, name=body.name, summary=body.summary)
    db.add(project)
    await db.commit()
    return _serialize(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    body: ProjectUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.id == project_id, Project.user_id == current_user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Projet introuvable")
    if body.name is not None:
        project.name = body.name
    if body.summary is not None:
        project.summary = body.summary
    if body.status is not None:
        if body.status not in {"active", "archived", "completed"}:
            raise HTTPException(status_code=422, detail="Statut invalide")
        project.status = body.status
    await db.commit()
    return _serialize(project)


@router.post("/{project_id}/archive", response_model=ProjectResponse)
async def archive_project(
    project_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.id == project_id, Project.user_id == current_user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Projet introuvable")
    project.status = "archived"
    await db.commit()
    return _serialize(project)
