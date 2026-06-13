import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Provide a TestClient for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities to initial state before each test"""
    # Store original state
    original_activities = {
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
        },
        "Art Club": {
            "description": "Explore drawing, painting, and mixed media techniques",
            "schedule": "Wednesdays, 3:30 PM - 5:00 PM",
            "max_participants": 16,
            "participants": ["ava@mergington.edu", "jack@mergington.edu"]
        },
    }
    
    # Clear and reset activities
    activities.clear()
    activities.update(original_activities)
    yield
    # Cleanup after test
    activities.clear()
    activities.update(original_activities)


class TestGetActivities:
    """Tests for GET /activities endpoint"""

    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns the activities list"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert data["Chess Club"]["max_participants"] == 12

    def test_get_activities_includes_participants(self, client):
        """Test that activities include current participant list"""
        response = client.get("/activities")
        data = response.json()
        assert len(data["Chess Club"]["participants"]) == 2
        assert "michael@mergington.edu" in data["Chess Club"]["participants"]

    def test_get_activities_includes_schedule(self, client):
        """Test that activities include schedule information"""
        response = client.get("/activities")
        data = response.json()
        assert data["Programming Class"]["schedule"] == "Tuesdays and Thursdays, 3:30 PM - 4:30 PM"


class TestSignup:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_successful_signup(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Signed up" in data["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "newstudent@mergington.edu" in activities_data["Chess Club"]["participants"]

    def test_signup_duplicate_email(self, client):
        """Test that duplicate signup is rejected"""
        response = client.post(
            "/activities/Chess Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]

    def test_signup_nonexistent_activity(self, client):
        """Test signup for non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Club/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_signup_email_normalization(self, client):
        """Test that emails are normalized (case-insensitive)"""
        # First signup
        response1 = client.post(
            "/activities/Programming Class/signup?email=Test@MERGINGTON.edu"
        )
        assert response1.status_code == 200
        
        # Second signup with different case should be rejected
        response2 = client.post(
            "/activities/Programming Class/signup?email=test@mergington.edu"
        )
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"]

    def test_signup_email_whitespace_handling(self, client):
        """Test that email whitespace is trimmed"""
        response = client.post(
            "/activities/Art Club/signup?email=%20student@mergington.edu%20"
        )
        assert response.status_code == 200
        
        # Check that whitespace was trimmed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "student@mergington.edu" in activities_data["Art Club"]["participants"]


class TestUnregister:
    """Tests for DELETE /activities/{activity_name}/signup endpoint"""

    def test_successful_unregister(self, client):
        """Test successful unregister from an activity"""
        # First add a participant
        client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        
        # Then remove them
        response = client.delete(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        assert "Unregistered" in response.json()["message"]
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "newstudent@mergington.edu" not in activities_data["Chess Club"]["participants"]

    def test_unregister_nonexistent_participant(self, client):
        """Test unregister of participant not in activity"""
        response = client.delete(
            "/activities/Chess Club/signup?email=nonexistent@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_unregister_nonexistent_activity(self, client):
        """Test unregister from non-existent activity"""
        response = client.delete(
            "/activities/Nonexistent Club/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_unregister_email_normalization(self, client):
        """Test that email normalization works in unregister"""
        # Remove with different case
        response = client.delete(
            "/activities/Chess Club/signup?email=MICHAEL@MERGINGTON.EDU"
        )
        assert response.status_code == 200
        
        # Verify they were removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "michael@mergington.edu" not in activities_data["Chess Club"]["participants"]


class TestIntegration:
    """Integration tests for multiple operations"""

    def test_signup_and_unregister_flow(self, client):
        """Test complete signup and unregister flow"""
        email = "integration@test.edu"
        activity = "Chess Club"
        
        # Signup
        signup_response = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        assert signup_response.status_code == 200
        
        # Verify signup
        activities_response = client.get("/activities")
        assert email in activities_response.json()[activity]["participants"]
        
        # Unregister
        unregister_response = client.delete(
            f"/activities/{activity}/signup?email={email}"
        )
        assert unregister_response.status_code == 200
        
        # Verify unregister
        activities_response = client.get("/activities")
        assert email not in activities_response.json()[activity]["participants"]

    def test_multiple_signups_different_activities(self, client):
        """Test that a student can sign up for multiple activities"""
        email = "multiactivity@test.edu"
        
        # Sign up for two activities
        response1 = client.post(
            f"/activities/Chess Club/signup?email={email}"
        )
        response2 = client.post(
            f"/activities/Programming Class/signup?email={email}"
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Verify both signups
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data["Chess Club"]["participants"]
        assert email in activities_data["Programming Class"]["participants"]

    def test_concurrent_signups_same_activity(self, client):
        """Test multiple students signing up for the same activity"""
        emails = ["student1@test.edu", "student2@test.edu", "student3@test.edu"]
        
        for email in emails:
            response = client.post(
                f"/activities/Art Club/signup?email={email}"
            )
            assert response.status_code == 200
        
        # Verify all signups
        activities_response = client.get("/activities")
        participants = activities_response.json()["Art Club"]["participants"]
        for email in emails:
            assert email in participants
