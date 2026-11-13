from fastapi.testclient import TestClient
from app.main import app


def test_acceptance_checklist_and_hybrid_rag():
    with TestClient(app) as client:
        # 1. Health & counts
        res_health = client.get("/api/health")
        assert res_health.status_code == 200
        hdata = res_health.json()
        assert hdata["counts"]["data_sources"] == 3
        assert hdata["counts"]["investigations"] == 8
        assert hdata["counts"]["experiment_runs"] >= 20
        assert hdata["counts"]["knowledge_chunks"] >= 7

        # 2. Sources registry
        res_sources = client.get("/api/sources")
        assert res_sources.status_code == 200
        pubs = {s["publisher"] for s in res_sources.json()}
        assert {"NASA PSI", "JAXA DARTS", "UL FSRI"} == pubs

        # 3. Every investigation has source_url, domain, gravity, and DOI where provided
        res_invs = client.get("/api/investigations")
        assert res_invs.status_code == 200
        invs = res_invs.json()
        ext_ids = {i["external_id"] for i in invs}
        assert {"PSI-25", "PSI-98", "PSI-101", "PSI-102", "PSI-107", "PSI-69", "JAXA-GC", "FSRI-MAP"} == ext_ids

        # 4. Every downloaded file has filename, version, SHA-256 checksum, and source-investigation link
        res_files = client.get("/api/investigations/PSI-25/files")
        assert res_files.status_code == 200
        files = res_files.json()
        assert len(files) >= 1
        assert len(files[0]["checksum_sha256"]) == 64

        # 5. Missing values remain missing (NULL) with explicit missing_reason (never converted to zero)
        res_b5 = client.get("/api/experiments/BASS2-T05/measurements")
        assert res_b5.status_code == 200
        b5_data = res_b5.json()
        missing_m = [m for m in b5_data["measurements"] if m["canonical_field"] == "flame_height"][0]
        assert missing_m["value_numeric"] is None
        assert missing_m["value_status"] == "missing"
        assert missing_m["missing_reason"] == "unavailable_in_source"

        # 6. Domain-gated comparison blocks incompatible domains by default and isolates Earth-based FSRI baseline
        res_cmp = client.post(
            "/api/compare",
            json={
                "target_domain": "solid",
                "target_gravity": "microgravity",
                "oxygen_fraction": 0.21,
                "pressure_kpa": 101.3,
                "flow_velocity_cm_s": 8.0,
                "include_terrestrial_baseline": True,
            },
        )
        assert res_cmp.status_code == 200
        cmp_data = res_cmp.json()
        assert len(cmp_data["compatible_microgravity_ranking"]) >= 7
        for r in cmp_data["compatible_microgravity_ranking"]:
            assert r["combustion_domain"] == "solid"
            assert r["gravity_regime"] == "microgravity"
            assert r["is_terrestrial_baseline"] is False

        assert len(cmp_data["terrestrial_baseline_track"]) == 3
        for tb in cmp_data["terrestrial_baseline_track"]:
            assert tb["is_terrestrial_baseline"] is True

        assert len(cmp_data["excluded_incompatible_domains"]) >= 10
        blocked_domains = {e["record_domain"] for e in cmp_data["excluded_incompatible_domains"]}
        assert {"gas", "liquid_droplet", "aerosol_smoke"}.issubset(blocked_domains)

        # 7. Provenance endpoint returns DOI, file checksum, field mappings, and derived audit trail
        res_prov = client.get("/api/provenance/BASS2-T01")
        assert res_prov.status_code == 200
        prov_data = res_prov.json()
        assert prov_data["investigation"]["doi"] == "10.60555/4qc4-de67"
        assert len(prov_data["derived_audit_trail"]) >= 1

        # 8. Hybrid Retrieval RAG Assistant answers microgravity flame spread question with separated evidence & interpretation
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
        assert len(rag_data["published_scientific_evidence"]) >= 1
        assert len(rag_data["structured_sql_experiments"]) >= 1
        assert "markdown_content" in rag_data["generated_interpretation"]
        assert len(rag_data["generated_interpretation"]["citations"]) >= 1
        print("ALL 8 ACCEPTANCE & HYBRID RAG CHECKS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    test_acceptance_checklist_and_hybrid_rag()

