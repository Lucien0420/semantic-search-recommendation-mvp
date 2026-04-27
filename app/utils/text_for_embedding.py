"""Build embeddable text from a post (extensible to multimodal captions later)."""

from app.models.post import Post


def post_to_embed_text(post: Post) -> str:
    parts = [post.content.strip()]
    if post.tags:
        parts.append("tags: " + ", ".join(str(t) for t in post.tags))
    return "\n".join(parts)
