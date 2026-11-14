from fastapi.testclient import TestClient
from app.main import app


def test_real_handoff_and_flare_ranking():
    with TestClient(app) as client:
        # 1. Health & real FLARE_AI_Data_Handoff counts
        res_health = client.get("/api/health")
        assert res_health.status_code == 200
        hdata = res_health.json()
        assert hdata["counts"]["investigations"] == 6
        assert hdata["counts"]["experiment_runs"] == 1157
        assert hdata["counts"]["measurements"] == 10079
        assert hdata["counts"]["knowledge_chunks"] == 1312

        # 2. All 6 NASA PSI investigations present with DOIs and files
        res_invs = client.get("/api/investigations")
        assert res_invs.status_code == 200
        invs = res_invs.json()
        ext_ids = {i["external_id"] for i in invs}
        assert {"PSI-25", "PSI-98", "PSI-101", "PSI-102", "PSI-107", "PSI-69"} == ext_ids
        for inv in invs:
            assert inv["doi"] is not None
            assert inv["file_count"] >= 1

        # 3. Missing values remain NULL with explicit missing_reason (e.g., PSI-69:FLEX-001 flow_cm_s)
        res_flex = client.get("/api/experiments/PSI-69:FLEX-001/measurements")
        assert res_flex.status_code == 200
        flex_data = res_flex.json()
        assert flex_data["flow_velocity_normalized_cm_s"] is None
        assert flex_data["flow_velocity_missing_reason"] == "unavailable_in_source"

        # 4. Domain-gated comparison powered by flare_ranking (adapter.py + ranking.py)
        for dom in ("solid", "gas", "liquid_droplet", "aerosol_smoke"):
            res_cmp = client.post(
                "/api/compare",
                json={
                    "target_domain": dom,
                    "target_gravity": "microgravity",
                    "oxygen_fraction": 0.21,
                    "pressure_kpa": 101.3,
                    "flow_velocity_cm_s": 8.0,
                    "include_terrestrial_baseline": True,
                },
            )
            assert res_cmp.status_code == 200
            cmp_data = res_cmp.json()
            assert len(cmp_data["compatible_microgravity_ranking"]) >= 1
            for r in cmp_data["compatible_microgravity_ranking"]:
                assert r["combustion_domain"] == dom
                assert r["gravity_regime"] == "microgravity"
            assert len(cmp_data["excluded_incompatible_domains"]) >= 1

        # 5. Provenance endpoint returns real DOI & SHA-256 file checksums
        res_psi25 = client.get("/api/experiments?investigation_id=PSI-25")
        assert res_psi25.status_code == 200
        first_psi25_code = res_psi25.json()[0]["run_code"]
        res_prov = client.get(f"/api/provenance/{first_psi25_code}")
        assert res_prov.status_code == 200
        prov_data = res_prov.json()
        assert prov_data["investigation"]["doi"] == "10.60555/4qc4-de67"
        assert len(prov_data["source_files"]) >= 1

        # 6. Hybrid Retrieval RAG Assistant searches 1,312 real PDF chunks + 1,157 SQL runs
        res_rag = client.post(
            "/api/assistant/query",
            json={
                "question": "Why does flame spread behave differently in microgravity?",
                "top_k_chunks": 4,
                "top_k_experiments": 5,
            },
        )
        assert res_rag.status_code == 200
        rag_data = res_rag.json()
        assert len(rag_data["published_scientific_evidence"]) == 4
        assert len(rag_data["structured_sql_experiments"]) == 5
        assert "markdown_content" in rag_data["generated_interpretation"]
        print("ALL REAL HANDOFF & FLARE_RANKING TESTS PASSED!")


if __name__ == "__main__":
    test_real_handoff_and_flare_ranking()
