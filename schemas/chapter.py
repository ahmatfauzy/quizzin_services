from pydantic import BaseModel
from typing import Optional, List


class KnowledgeGraphModule(BaseModel):
    module_number: str
    title: str
    icon_type: str


class KnowledgeGraphRelation(BaseModel):
    from_field: str
    to: str
    label: str


class KnowledgeGraph(BaseModel):
    core_concept: Optional[dict] = None
    modules: List[KnowledgeGraphModule] = []
    entities: List[str] = []
    relations: List[dict] = []


class ChapterDetailResponse(BaseModel):
    id: int
    chapter_number: int
    title: Optional[str] = None
    document_id: int
    document_title: Optional[str] = None
    summary: Optional[str] = None
    mastery_percentage: float = 0.0
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    knowledge_graph: Optional[dict] = None

    class Config:
        from_attributes = True
