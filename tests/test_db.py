from supabase_provisioner.db import ControlDB


def test_db_allocates_non_overlapping_port_blocks(tmp_path):
    db = ControlDB(tmp_path / "control.sqlite3")
    db.migrate()
    first = db.next_port_block(18000)
    db.create_project(
        {
            "slug": "alpha",
            "name": "Alpha",
            "status": "running",
            "compose_project": "sb_alpha",
            "base_dir": str(tmp_path / "alpha"),
            "api_url": "https://alpha.example.test",
            "studio_url": "https://alpha.example.test",
            "kong_http_port": first[0],
            "kong_https_port": first[1],
            "pooler_session_port": first[2],
            "pooler_transaction_port": first[3],
            "secrets": {"postgres_password": "x"},
            "proxy": {},
        }
    )
    assert db.next_port_block(18000) == (18010, 18011, 18012, 18013)
