"""Smoke tests. Set TEST_DATABASE_URL to a disposable PostgreSQL database before running."""
import os
import unittest

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
@unittest.skipUnless(TEST_DATABASE_URL, "Set TEST_DATABASE_URL to run PostgreSQL API tests")
class ApiSmokeTests(unittest.TestCase):
    def setUp(self):
        os.environ["DATABASE_URL"] = TEST_DATABASE_URL
        os.environ["ENABLE_SCHEDULER"] = "0"
        from app import create_app
        self.app = create_app()
        self.app.config.update(TESTING=True, ENABLE_SCHEDULER=False)
        self.client = self.app.test_client()

    def test_health(self):
        self.assertEqual(self.client.get("/health").status_code, 200)

    def test_create_and_list_subscription(self):
        response = self.client.post("/api/subscriptions", json={
            "user_id": 1,
            "transaction_ref": "TEST-T-001",
            "merchant": "TestMerchant",
            "amount": 99,
            "renewal_date": "2027-01-01"
        })
        self.assertIn(response.status_code, (201, 409), response.get_json())
        listing = self.client.get("/api/subscriptions?user_id=1")
        self.assertEqual(listing.status_code, 200)

if __name__ == "__main__":
    unittest.main()
