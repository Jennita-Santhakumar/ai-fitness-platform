from datetime import date
import pytest


def test_workout_crud_and_pagination(client, auth_headers):
    headers = auth_headers("athlete1@example.com")

    # 1. Create Workouts
    for i in range(1, 4):
        resp = client.post(
            "/workouts",
            json={"title": f"Workout Plan {i}", "notes": f"Notes for {i}"},
            headers=headers,
        )
        assert resp.status_code == 201

    # 2. Test Pagination (limit=2, offset=0)
    list_resp = client.get("/workouts?limit=2&offset=0", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 2

    # 3. Test Pagination (limit=2, offset=2)
    offset_resp = client.get("/workouts?limit=2&offset=2", headers=headers)
    assert offset_resp.status_code == 200
    assert len(offset_resp.json()) == 1

    # 4. Update Workout
    w_id = list_resp.json()[0]["id"]
    patch_resp = client.patch(
        f"/workouts/{w_id}",
        json={"title": "Updated Power Routine"},
        headers=headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["title"] == "Updated Power Routine"

    # 5. Delete Workout
    del_resp = client.delete(f"/workouts/{w_id}", headers=headers)
    assert del_resp.status_code == 204

    # Verify deleted
    get_resp = client.get(f"/workouts/{w_id}", headers=headers)
    assert get_resp.status_code == 404


def test_exercises_sub_resource(client, auth_headers):
    headers = auth_headers("lifter@example.com")

    # Create parent workout
    w_resp = client.post("/workouts", json={"title": "Chest Day"}, headers=headers)
    workout_id = w_resp.json()["id"]

    # Add exercise
    ex_resp = client.post(
        f"/workouts/{workout_id}/exercises",
        json={"name": "Barbell Bench Press", "sets": 4, "reps": 8, "weight": 85.0},
        headers=headers,
    )
    assert ex_resp.status_code == 201
    exercise_id = ex_resp.json()["id"]

    # Get workout details with exercises
    detail_resp = client.get(f"/workouts/{workout_id}", headers=headers)
    assert detail_resp.status_code == 200
    assert len(detail_resp.json()["exercises"]) == 1
    assert detail_resp.json()["exercises"][0]["name"] == "Barbell Bench Press"

    # Delete exercise
    del_resp = client.delete(
        f"/workouts/{workout_id}/exercises/{exercise_id}", headers=headers
    )
    assert del_resp.status_code == 204


def test_session_crud(client, auth_headers):
    headers = auth_headers("runner@example.com")

    # Log session
    s_resp = client.post(
        "/sessions",
        json={
            "date": str(date(2026, 10, 11)),
            "duration_min": 60,
            "notes": "10km endurance run",
        },
        headers=headers,
    )
    assert s_resp.status_code == 201
    session_id = s_resp.json()["id"]

    # List sessions
    list_resp = client.get("/sessions", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # Update session
    patch_resp = client.patch(
        f"/sessions/{session_id}",
        json={"duration_min": 65},
        headers=headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["duration_min"] == 65

    # Delete session
    del_resp = client.delete(f"/sessions/{session_id}", headers=headers)
    assert del_resp.status_code == 204


def test_ownership_enforcement_between_two_users(client, auth_headers):
    headers_a = auth_headers("user_a@example.com")
    headers_b = auth_headers("user_b@example.com")

    # User A creates a workout
    resp_a = client.post(
        "/workouts",
        json={"title": "User A Private Workout", "notes": "Secret routine"},
        headers=headers_a,
    )
    workout_id = resp_a.json()["id"]

    # User B attempts to GET User A's workout -> 404
    resp_b_get = client.get(f"/workouts/{workout_id}", headers=headers_b)
    assert resp_b_get.status_code == 404

    # User B attempts to PATCH User A's workout -> 404
    resp_b_patch = client.patch(
        f"/workouts/{workout_id}",
        json={"title": "Hacked Title"},
        headers=headers_b)
    assert resp_b_patch.status_code == 404

    # User B attempts to ADD exercise to User A's workout -> 404
    resp_b_add_ex = client.post(
        f"/workouts/{workout_id}/exercises",
        json={"name": "Intruder Pushups", "sets": 1, "reps": 1, "weight": 0.0},
        headers=headers_b,
    )
    assert resp_b_add_ex.status_code == 404

    # User B attempts to DELETE User A's workout -> 404
    resp_b_del = client.delete(f"/workouts/{workout_id}", headers=headers_b)
    assert resp_b_del.status_code == 404

    # User A verifies their workout remains intact
    verify_resp = client.get(f"/workouts/{workout_id}", headers=headers_a)
    assert verify_resp.status_code == 200
    assert verify_resp.json()["title"] == "User A Private Workout"
