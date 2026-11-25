def test_dashboard_layout_has_one_main_content_flow(client):
    client.post(
        "/auth/login",
        data={"email": "admin@test.local", "password": "MotDePasse-Test-2026!"},
        follow_redirects=True,
    )
    response = client.get("/dashboard")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    topbar = html.index('class="topbar"')
    content_area = html.index('class="page-content dashboard-page"')
    dashboard = html.index('class="dashboard-v3"')
    assert topbar < content_area < dashboard
    assert html.count('class="dashboard-v3"') == 1
