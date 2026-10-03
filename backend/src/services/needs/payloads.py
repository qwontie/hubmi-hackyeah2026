from typing import Any

from utils.db.models.need import Need, NeedCluster


def cluster_ref(cluster: NeedCluster | None) -> dict[str, Any] | None:
    if cluster is None:
        return None
    return {"id": str(cluster.id), "title": cluster.title, "size": cluster.size}


def cluster_payload(cluster: NeedCluster) -> dict[str, Any]:
    return {
        "id": str(cluster.id),
        "title": cluster.title,
        "summary": cluster.summary,
        "category_slug": cluster.category_slug,
        "size": cluster.size,
        "last_need_at": cluster.last_need_at,
        "created_at": cluster.created_at,
    }


def need_payload(
    need: Need, cluster: NeedCluster | None, matches: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "id": str(need.id),
        "number": need.number,
        "text": need.text,
        "title": need.title,
        "origin": need.origin.value,
        "powiat": need.powiat,
        "category_slug": need.category_slug,
        "status": need.status.value,
        "nothing_fits": need.nothing_fits,
        "has_contact": bool(need.contact_email),
        "cluster": cluster_ref(cluster),
        "matches": matches,
        "created_at": need.created_at,
    }
