from expense_record.app import create_app


def test_index_page_loads():
    app = create_app({"TESTING": True})
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"Expense Screenshot Tool" in response.data
