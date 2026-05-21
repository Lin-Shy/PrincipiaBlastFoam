from __future__ import annotations

import os
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env", override=False)

from principia_ai.retrieval.case_content_knowledge_graph import (  # noqa: E402
    CaseContentKnowledgeGraphRetriever,
)
from principia_ai.tools.retrieval_llm_config import resolve_retrieval_llm_config  # noqa: E402
from principia_ai.retrieval.user_guide_knowledge_graph import (  # noqa: E402
    UserGuideKnowledgeGraphRetriever,
)


CASE_ALIASES = {
    "ddt": "blastXiFoam/deflagrationToDetonationTransition",
    "deflagration to detonation": "blastXiFoam/deflagrationToDetonationTransition",
    "deflagration-to-detonation": "blastXiFoam/deflagrationToDetonationTransition",
    "deflagrationtodetonationtransition": "blastXiFoam/deflagrationToDetonationTransition",
    "laminar flame speed": "blastXiFoam/deflagrationToDetonationTransition",
    "spalart allmaras": "blastXiFoam/deflagrationToDetonationTransition",
    "free field": "blastFoam/freeField",
    "free-field": "blastFoam/freeField",
    "building3d": "blastFoam/building3D",
    "mapped building": "blastFoam/mappedBuilding3D",
    "moving cone": "blastFoam/movingCone",
    "internal detonation": "blastFoam/internalDetonation/internalDetonation",
    "bursting window": "blastFoam/burstingWindow_workshop",
    "two charge": "blastFoam/twoChargeDetonation",
    "axisymmetric charge": "blastFoam/axisymmetricCharge",
}

FILE_INTENT_RULES = [
    (
        "constant/combustionProperties",
        (
            "su",
            "laminar flame speed",
            "flame speed",
            "combustion",
            "equivalence ratio",
            "arrhenius",
            "reaction",
        ),
        100.0,
    ),
    (
        "0/Su",
        (
            "su field",
            "initial su",
            "initial flame speed",
            "internalfield",
        ),
        70.0,
    ),
    (
        "constant/turbulenceProperties",
        (
            "turbulence",
            "rasmodel",
            "spalart",
            "allmaras",
            "komegasst",
            "k omega",
            "rans",
        ),
        95.0,
    ),
    (
        "system/controlDict",
        (
            "endtime",
            "delta t",
            "time step",
            "write interval",
            "courant",
            "functions",
            "时间",
            "步长",
            "输出",
            "控制",
        ),
        85.0,
    ),
    (
        "system/setFieldsDict",
        (
            "charge",
            "charge mass",
            "c4",
            "tnt",
            "explosive",
            "装药",
            "爆源",
            "炸药",
            "爆炸",
            "比例距离",
            "初始场",
            "location",
            "sphere",
            "box",
            "initial distribution",
        ),
        90.0,
    ),
    (
        "system/blockMeshDict",
        (
            "mesh",
            "domain",
            "cell",
            "resolution",
            "blockmesh",
            "geometry",
            "网格",
            "计算域",
            "领域",
            "尺度",
            "几何",
            "边界",
            "比例距离",
        ),
        80.0,
    ),
    (
        "system/fvSchemes",
        (
            "scheme",
            "flux",
            "hllc",
            "ausm",
            "gradient",
            "interpolation",
            "div",
        ),
        80.0,
    ),
    (
        "system/fvSolution",
        (
            "solver",
            "pimple",
            "piso",
            "corrector",
            "tolerance",
        ),
        80.0,
    ),
    (
        "constant/thermophysicalProperties",
        (
            "thermo",
            "thermophysical",
            "cv",
            "hf",
            "equation of state",
        ),
        75.0,
    ),
    (
        "constant/phaseProperties",
        (
            "phase",
            "phaseproperties",
            "c4",
            "jwl",
            "eos",
            "equation of state",
            "density",
            "rho",
            "tnt equivalence",
            "explosive properties",
            "物性",
            "状态方程",
            "密度",
            "炸药物性",
        ),
        90.0,
    ),
    (
        "0/rho.c4.orig",
        (
            "rho.c4",
            "c4 density",
            "density",
            "1601",
            "密度",
        ),
        95.0,
    ),
    (
        "0/alpha.c4.orig",
        (
            "alpha.c4",
            "volume fraction",
            "c4 region",
            "initial c4",
            "体积分数",
            "初始c4",
        ),
        90.0,
    ),
]


def _normalize(text: str) -> str:
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(text))
    text = text.lower().replace("-", " ").replace("_", " ")
    text = re.sub(r"[^a-z0-9./]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


class PrincipiaRetrievalService:
    """Long-lived retrieval service used by MCP tools."""

    def __init__(self) -> None:
        tutorials = os.getenv("BLASTFOAM_TUTORIALS")
        if tutorials:
            os.environ["BLASTFOAM_TUTORIALS"] = os.path.expanduser(tutorials)

        llm_config = resolve_retrieval_llm_config()
        self.case_retriever = CaseContentKnowledgeGraphRetriever(
            llm_api_key=llm_config["api_key"],
            llm_base_url=llm_config["base_url"],
            llm_model=llm_config["model"],
        )
        self.user_guide_retriever: Optional[UserGuideKnowledgeGraphRetriever] = None

    def get_status(self) -> Dict[str, Any]:
        return {
            "project_root": str(PROJECT_ROOT),
            "blastfoam_tutorials": os.getenv("BLASTFOAM_TUTORIALS"),
            "case_nodes": len(self.case_retriever.nodes),
            "case_relationships": len(self.case_retriever.relationships),
            "known_cases": sorted(self.case_retriever.case_path_to_node_id.keys()),
            "retrieval_llm": resolve_retrieval_llm_config()["model"],
        }

    def _resolve_case_path(self, query_or_case_path: str) -> Optional[str]:
        raw = str(query_or_case_path).strip().strip("/")
        if raw in self.case_retriever.case_path_to_node_id:
            return raw

        normalized_query = _normalize(raw)
        compact_query = normalized_query.replace(" ", "")

        for alias, case_path in CASE_ALIASES.items():
            normalized_alias = _normalize(alias)
            if normalized_alias in normalized_query or normalized_alias.replace(" ", "") in compact_query:
                return case_path

        scored = []
        for case_path in self.case_retriever.case_path_to_node_id:
            normalized_case = _normalize(case_path)
            compact_case = normalized_case.replace(" ", "")
            score = 0
            if normalized_case in normalized_query or compact_case in compact_query:
                score += 100
            for token in normalized_case.replace("/", " ").split():
                if len(token) > 3 and token in normalized_query:
                    score += 10
            if score:
                scored.append((score, case_path))

        if not scored:
            return None
        return sorted(scored, key=lambda item: (-item[0], item[1]))[0][1]

    def get_case_by_intent(self, query: str) -> Dict[str, Any]:
        case_path = self._resolve_case_path(query)
        if not case_path:
            return {"found": False, "case_path": None, "reason": "No matching case intent found."}

        node_id = self.case_retriever.case_path_to_node_id.get(case_path)
        node = self.case_retriever.id_to_node.get(node_id, {}) if node_id else {}
        return {
            "found": True,
            "case_path": case_path,
            "node_id": node_id,
            "properties": node.get("properties", {}),
        }

    def get_files_for_case(self, case_path: str) -> Dict[str, Any]:
        resolved_case = self._resolve_case_path(case_path)
        if not resolved_case:
            return {"found": False, "case_path": case_path, "files": []}

        files = []
        for file_id in self.case_retriever.case_to_file_ids.get(resolved_case, []):
            node = self.case_retriever.id_to_node.get(file_id)
            if not node:
                continue
            full_path = str(node.get("properties", {}).get("path") or "")
            rel_path = self.case_retriever._normalize_file_reference(full_path, resolved_case)
            files.append(
                {
                    "file_path": rel_path,
                    "node_id": file_id,
                    "name": node.get("properties", {}).get("name"),
                }
            )

        return {
            "found": True,
            "case_path": resolved_case,
            "files": sorted(files, key=lambda item: str(item["file_path"])),
        }

    def find_variable(self, case_path: str, variable_name: str) -> Dict[str, Any]:
        resolved_case = self._resolve_case_path(case_path)
        if not resolved_case:
            return {"found": False, "case_path": case_path, "matches": []}

        variable_norm = _normalize(variable_name)
        matches = []
        for file_id in self.case_retriever.case_to_file_ids.get(resolved_case, []):
            node = self.case_retriever.id_to_node.get(file_id)
            if not node:
                continue
            full_path = str(node.get("properties", {}).get("path") or "")
            rel_path = self.case_retriever._normalize_file_reference(full_path, resolved_case)
            for variable_id in self.case_retriever.file_to_variable_ids.get(file_id, []):
                variable_node = self.case_retriever.id_to_node.get(variable_id)
                if not variable_node:
                    continue
                props = variable_node.get("properties", {})
                name = str(props.get("name") or "")
                if _normalize(name) == variable_norm:
                    matches.append(
                        {
                            "case_path": resolved_case,
                            "file_path": rel_path,
                            "variable_name": name,
                            "variable_id": variable_id,
                            "properties": props,
                        }
                    )

        return {"found": bool(matches), "case_path": resolved_case, "matches": matches}

    def get_file_content(self, case_path: str, file_path: str, max_lines: int = 120) -> Dict[str, Any]:
        resolved_case = self._resolve_case_path(case_path)
        if not resolved_case:
            return {"found": False, "case_path": case_path, "file_path": file_path, "content": ""}

        rel_path = str(file_path).strip().lstrip("/")
        if rel_path.startswith(f"{resolved_case}/"):
            rel_path = rel_path[len(resolved_case) + 1 :]

        full_rel_path = f"{resolved_case}/{rel_path}"
        content = self.case_retriever._get_file_content(full_rel_path, max_lines=max_lines)
        found = not content.startswith("File not found:")
        return {
            "found": found,
            "case_path": resolved_case,
            "file_path": rel_path,
            "content": content,
        }

    def get_modification_targets(
        self,
        user_request: str,
        case_path: Optional[str] = None,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        if case_path:
            resolved_case = self._resolve_case_path(case_path)
            if not resolved_case:
                return {"found": False, "case_path": case_path, "targets": [], "reason": "No matching case found."}
        else:
            case_info = self.get_case_by_intent(user_request)
            if not case_info.get("found"):
                return {"found": False, "case_path": None, "targets": [], "reason": case_info.get("reason")}
            resolved_case = str(case_info["case_path"])

        case_path = resolved_case
        files_info = self.get_files_for_case(case_path)
        available = {str(item["file_path"]): item for item in files_info.get("files", [])}
        normalized_query = _normalize(user_request)

        scored_targets = []
        for file_path, item in available.items():
            score = 0.0
            path_norm = _normalize(file_path)
            if path_norm in normalized_query:
                score += 120.0
            for suffix, phrases, boost in FILE_INTENT_RULES:
                if file_path == suffix or file_path.endswith(f"/{suffix}"):
                    if any(_normalize(phrase) in normalized_query for phrase in phrases):
                        score += boost
            if score > 0:
                scored_targets.append((score, item))

        scored_targets.sort(key=lambda pair: (-pair[0], str(pair[1]["file_path"])))
        targets = []
        for rank, (score, item) in enumerate(scored_targets[: max(1, int(top_k))], start=1):
            targets.append(
                {
                    "rank": rank,
                    "score": score,
                    "case_path": case_path,
                    "file_path": item["file_path"],
                    "node_id": item["node_id"],
                }
            )

        return {"found": bool(targets), "case_path": case_path, "targets": targets}

    def _score_case_files(self, case_path: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        files_info = self.get_files_for_case(case_path)
        if not files_info.get("found"):
            return []

        normalized_query = _normalize(query)
        scored_targets = []
        for item in files_info.get("files", []):
            file_path = str(item.get("file_path") or "")
            path_norm = _normalize(file_path)
            score = 0.0

            if path_norm and path_norm in normalized_query:
                score += 120.0
            if file_path and file_path.lower() in str(query).lower():
                score += 120.0

            for suffix, phrases, boost in FILE_INTENT_RULES:
                if file_path == suffix or file_path.endswith(f"/{suffix}"):
                    if any(_normalize(phrase) in normalized_query for phrase in phrases):
                        score += boost

            if score > 0:
                scored_targets.append((score, item))

        scored_targets.sort(key=lambda pair: (-pair[0], str(pair[1]["file_path"])))
        results = []
        for rank, (score, item) in enumerate(scored_targets[: max(1, int(top_k))], start=1):
            results.append(
                {
                    "rank": rank,
                    "score": score,
                    "case_path": case_path,
                    "file_path": item["file_path"],
                    "node_id": item["node_id"],
                    "name": item.get("name"),
                }
            )
        return results

    def search_case_content(
        self,
        query: str,
        case_path: Optional[str] = None,
        file_path: Optional[str] = None,
        variable_name: Optional[str] = None,
        top_k: int = 5,
        include_file_content: bool = False,
        max_iterations: int = 1,
    ) -> Dict[str, Any]:
        resolved_case = self._resolve_case_path(case_path or "") if case_path else None

        if resolved_case and file_path:
            content = self.get_file_content(resolved_case, file_path, max_lines=120 if include_file_content else 40)
            return {
                "found": content.get("found", False),
                "strategy": "scoped_file_content",
                "case_path": resolved_case,
                "results": [content] if content.get("found") else [],
                "fallback_used": False,
            }

        if resolved_case and variable_name:
            variable_result = self.find_variable(resolved_case, variable_name)
            return {
                "found": variable_result.get("found", False),
                "strategy": "scoped_variable_lookup",
                "case_path": resolved_case,
                "results": variable_result.get("matches", []),
                "fallback_used": False,
            }

        if resolved_case:
            scoped_results = self._score_case_files(resolved_case, query, top_k=top_k)
            if scoped_results:
                if include_file_content:
                    for item in scoped_results:
                        content = self.get_file_content(resolved_case, item["file_path"], max_lines=80)
                        item["content"] = content.get("content", "")
                return {
                    "found": True,
                    "strategy": "scoped_case_file_rules",
                    "case_path": resolved_case,
                    "results": scoped_results,
                    "fallback_used": False,
                }

        result = self.case_retriever.search_detailed(
            query,
            top_k=top_k,
            include_file_content=include_file_content,
            max_iterations=max_iterations,
        )
        if resolved_case:
            result["scoped_case_path"] = resolved_case
            result["fallback_used"] = True
        return result

    def search_user_guide(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        if self.user_guide_retriever is None:
            llm_config = resolve_retrieval_llm_config()
            self.user_guide_retriever = UserGuideKnowledgeGraphRetriever(
                llm_api_key=llm_config["api_key"],
                llm_base_url=llm_config["base_url"],
                llm_model=llm_config["model"],
            )
        return self.user_guide_retriever.search_detailed(query, top_k=top_k)


@lru_cache(maxsize=1)
def get_service() -> PrincipiaRetrievalService:
    return PrincipiaRetrievalService()
