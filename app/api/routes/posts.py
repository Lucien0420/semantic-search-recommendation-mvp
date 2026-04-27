from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from sqlalchemy import select

from app.api.deps import CurrentUserDep, DbDep
from app.models.post import Post
from app.models.user_action import UserAction
from app.schemas.post import PostCreate, PostRead
from app.schemas.user_action import LikeRead
from app.tasks.indexing import index_post_background

router = APIRouter()


@router.post("/", response_model=PostRead, status_code=status.HTTP_201_CREATED)
async def create_post(
    request: Request,
    body: PostCreate,
    db: DbDep,
    current: CurrentUserDep,
    background_tasks: BackgroundTasks,
) -> PostRead:
    post = Post(
        content=body.content,
        author_id=current.id,
        tags=list(body.tags),
        content_type=body.content_type,
    )
    db.add(post)
    await db.flush()
    await db.refresh(post)
    out = PostRead.model_validate(post)
    background_tasks.add_task(index_post_background, request.app, post.id)
    await db.commit()
    return out


@router.post("/{post_id}/like", response_model=LikeRead)
async def like_post(post_id: int, db: DbDep, current: CurrentUserDep) -> LikeRead:
    post = await db.get(Post, post_id)
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    stmt = select(UserAction).where(
        UserAction.user_id == current.id,
        UserAction.post_id == post_id,
        UserAction.action_type == "like",
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        await db.commit()
        return LikeRead.model_validate(existing)

    action = UserAction(user_id=current.id, post_id=post_id, action_type="like")
    db.add(action)
    await db.flush()
    await db.refresh(action)
    await db.commit()
    return LikeRead.model_validate(action)
